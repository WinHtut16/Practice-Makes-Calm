"""Pilot stage P1: run simulated learners against Dr. Lee at every level and scenario.

Example (free tier, small run first):
    python manage.py pilot_system --runs 1 --sleep 5
"""
import csv
import re
import statistics
import time
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from study import llm, mock, prompts
from study.content import SCENARIOS

VIOLATION_RE = re.compile(
    r"\b(grammar|spelling|your english|accent|scholarship|grade[sd]?|funding|stupid|lazy|ridiculous|pathetic|incompetent)\b", re.I)


class Command(BaseCommand):
    help = "Pilot P1: check that Dr. Lee's levels behave differently and never break the shared rules."

    def add_arguments(self, parser):
        parser.add_argument("--runs", type=int, default=1, help="conversations per level x scenario x learner")
        parser.add_argument("--levels", default="1,2,3")
        parser.add_argument("--scenarios", default="S1,S2,S3")
        parser.add_argument("--learners", default="weak,medium,strong")
        parser.add_argument("--max-turns", type=int, default=settings.STUDY["ROUND_MAX_MESSAGES"])
        parser.add_argument("--sleep", type=float, default=0.0, help="seconds between API calls (use ~4-6 on the free tier)")
        parser.add_argument("--out", default="pilot_out")

    def handle(self, *args, **o):
        levels = [int(x) for x in o["levels"].split(",")]
        scenarios, learners = o["scenarios"].split(","), o["learners"].split(",")
        total = o["runs"] * len(levels) * len(scenarios) * len(learners)
        self.stdout.write(f"Running {total} conversations (up to {total * o['max_turns'] * 2} API calls). "
                          f"Mode: {'MOCK' if settings.STUDY['MOCK'] else settings.STUDY['MODEL']}")
        out = Path(o["out"]); out.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        rows, transcripts = [], []
        for lv in levels:
            for sc in scenarios:
                for ln in learners:
                    for run in range(o["runs"]):
                        row, tr = self.one(lv, sc, ln, o["max_turns"], o["sleep"])
                        row["run"] = run + 1
                        rows.append(row)
                        transcripts.append(f"=== L{lv} {sc} {ln} run {run + 1} ===\n{tr}\n")
                        self.stdout.write(f"L{lv} {sc} {ln:<6} pushbacks={row['pushbacks']} agreed={row['agreed']} "
                                          f"violations={row['violations']} max_words={row['max_words']}")
        csv_path = out / f"p1_{stamp}.csv"
        with open(csv_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
        (out / f"p1_{stamp}_transcripts.txt").write_text("\n".join(transcripts))
        self.summary(rows)
        self.stdout.write(f"\nSaved {csv_path} and transcripts. Read the transcripts too: check that [AGREED] came at the right time.")

    def one(self, level, sc, learner_type, max_turns, sleep):
        sys_lee = prompts.dr_lee_system(sc, level)
        sys_learner = prompts.learner_system(sc, learner_type)
        conv = []  # (speaker, text)
        latencies, violations, agreed, max_words = [], 0, False, 0
        for _ in range(max_turns):
            # Learner's view: Dr. Lee's messages are "user", own messages are "model". Seed with an opener.
            lh = [("user", "(Your advisor Dr. Lee looks up.) Please start the conversation.")]
            for spk, t in conv:
                lh.append(("model" if spk == "learner" else "user", t))
            l_res = llm.generate(sys_learner, lh, temperature=0.7, mock_fn=mock.learner(learner_type))
            conv.append(("learner", l_res.text)); time.sleep(sleep)
            dh = [("user" if spk == "learner" else "model", t) for spk, t in conv]
            d_res = llm.generate(sys_lee, dh, temperature=settings.STUDY["TEMP_DR_LEE"], mock_fn=mock.dr_lee(sc, level))
            latencies.append(d_res.latency_ms); time.sleep(sleep)
            clean, ag = llm.strip_agreed(d_res.text)
            conv.append(("drlee", clean))
            violations += len(VIOLATION_RE.findall(clean))
            max_words = max(max_words, len(clean.split()))
            if ag:
                agreed = True
                break
        drlee_turns = sum(1 for s, _ in conv if s == "drlee")
        pushbacks = drlee_turns - (1 if agreed else 0)
        tr = "\n".join(f"{'STUDENT' if s == 'learner' else 'DR LEE '}: {t}" for s, t in conv)
        return {"level": level, "scenario": sc, "learner": learner_type, "pushbacks": pushbacks, "agreed": agreed,
                "violations": violations, "max_words": max_words,
                "median_latency_ms": int(statistics.median(latencies)) if latencies else 0}, tr

    def summary(self, rows):
        # Pass rule since the 4 Nov prompt change: push-backs depend on how good the student's case is, so the check
        # is the ORDER of levels for the same student, not a fixed count per level.
        self.stdout.write("\nSUMMARY")
        for lv in sorted({r["level"] for r in rows}):
            rs = [r for r in rows if r["level"] == lv]
            med = statistics.median(r["pushbacks"] for r in rs)
            self.stdout.write(f"  L{lv}: median push-backs {med}, agreed {sum(r['agreed'] for r in rs)}/{len(rs)}, "
                              f"violations {sum(r['violations'] for r in rs)}, max words {max(r['max_words'] for r in rs)}")
        self.stdout.write("\n  Push-backs per student type and scenario (mean over runs), L1 / L2 / L3:")
        ok = True
        for sc in sorted({r["scenario"] for r in rows}):
            for ln in ["weak", "medium", "strong"]:
                pb = {}
                for lv in (1, 2, 3):
                    v = [r["pushbacks"] for r in rows if r["scenario"] == sc and r["learner"] == ln and r["level"] == lv]
                    if v:
                        pb[lv] = statistics.mean(v)
                if len(pb) < 3:
                    continue
                good = pb[1] <= pb[2] <= pb[3] and pb[1] <= 1 and pb[3] >= 1
                ok &= good
                self.stdout.write(f"    {sc} {ln:<6} {pb[1]:.1f} / {pb[2]:.1f} / {pb[3]:.1f}  {'ok' if good else 'CHECK'}")
        self.stdout.write(f"  Rule: L1 <= L2 <= L3 for each student type, L1 at most 1, L3 at least 1.  "
                          f"{'PASS' if ok else 'CHECK the rows marked CHECK'}")
        lat = statistics.median(r["median_latency_ms"] for r in rows)
        self.stdout.write(f"  Median latency: {lat} ms (target <= 4000)")
        self.stdout.write("  Note: violations are keyword matches; review flagged transcripts by hand.")
