"""Offline scoring with LLM 3 (the scorer), blind to condition.

Scores every probe reply (and optional role-play transcripts) three times and keeps the median.
Writes a blind score file, a separate key file, and a 25% sample sheet for the human rater.

    python manage.py score_transcripts --sleep 5
    python manage.py score_transcripts --roleplay-dir roleplay_txt/   # files P01.txt ... with "Dr. Lee:" / "Student:" lines
"""
import csv
import random
import statistics
import time
from collections import Counter
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from study import llm, mock, prompts
from study.models import Message

STRATS = prompts.STRATEGIES


class Command(BaseCommand):
    help = "Score probe (and role-play) replies blind with the scorer model; 3 runs, median."

    def add_arguments(self, parser):
        parser.add_argument("--runs", type=int, default=3)
        parser.add_argument("--seed", type=int, default=7)
        parser.add_argument("--sleep", type=float, default=0.0)
        parser.add_argument("--include-pilot", action="store_true")
        parser.add_argument("--practice", action="store_true", help="also code strategies in practice rounds (H2a)")
        parser.add_argument("--roleplay-dir", default="")
        parser.add_argument("--human-share", type=float, default=0.25)
        parser.add_argument("--out", default="scoring_out")

    def handle(self, *args, **o):
        units = self.collect(o)  # one unit = one transcript (a probe, a role-play, or a practice round)
        rng = random.Random(o["seed"])
        rng.shuffle(units)
        for i, u in enumerate(units):
            u["blind_id"] = f"T{i + 1:03d}"
        out = Path(o["out"]); out.mkdir(exist_ok=True)
        score_rows = []
        for u in units:
            for k, (line, reply) in enumerate(u["pairs"], start=1):
                runs = []
                for _ in range(o["runs"]):
                    res = llm.generate(prompts.scorer_system(u["scenario"]),
                                       [("user", f'Advisor: "{line}"\nStudent reply: "{reply}"')],
                                       temperature=0.0, as_json=True, max_tokens=512, mock_fn=mock.scorer,
                                       schema=prompts.SCORER_SCHEMA)
                    runs.append(llm.parse_json(res.text))
                    time.sleep(o["sleep"])
                row = {"blind_id": u["blind_id"], "reply_no": k, "reply": reply}
                for c in "DESC":
                    row[c] = statistics.median(max(0, min(2, int(r.get(c, 0)))) for r in runs)
                row["desc_total"] = sum(row[c] for c in "DESC")
                counts = Counter(s for r in runs for s in set(r.get("strategies", [])))
                for s in STRATS:
                    row[s] = int(counts[s] * 2 > o["runs"])  # majority of runs
                score_rows.append(row)
            self.stdout.write(f"scored {u['blind_id']}")
        self.write(out / "scores_blind.csv", score_rows)
        # Transcript level. One reply rarely covers all four DESC parts, so the per-reply mean squeezes scores low.
        # desc_best uses the best score per component across the transcript, the same unit the live judge uses.
        by_t = {}
        for row in score_rows:
            by_t.setdefault(row["blind_id"], []).append(row)
        t_rows = []
        for bid, rows in by_t.items():
            best = {c: max(r[c] for r in rows) for c in "DESC"}
            t_rows.append({"blind_id": bid, "replies": len(rows),
                           "desc_mean_per_reply": round(statistics.mean(r["desc_total"] for r in rows), 2),
                           **{f"best_{c}": best[c] for c in "DESC"}, "desc_best": sum(best.values())})
        self.write(out / "scores_by_transcript.csv", t_rows)
        self.write(out / "key_DO_NOT_SHARE_WITH_RATER.csv",
                   [{k: u[k] for k in ("blind_id", "pid", "kind", "block", "design", "scenario", "round", "level")} for u in units])
        outcome = [u for u in units if u["kind"] in ("probe", "roleplay")]
        n_h = max(1, round(len(outcome) * o["human_share"])) if outcome else 0
        sample = rng.sample(outcome, n_h) if outcome else []
        sheet = [{"blind_id": u["blind_id"], "reply_no": k, "advisor_line": line, "reply": reply,
                  "D": "", "E": "", "S": "", "C": "", **{s: "" for s in STRATS}}
                 for u in sorted(sample, key=lambda x: x["blind_id"]) for k, (line, reply) in enumerate(u["pairs"], start=1)]
        self.write(out / "human_rating_sheet.csv", sheet)
        self.stdout.write(f"\n{len(units)} transcripts scored. Human sheet: {n_h} of {len(outcome)} outcome transcripts.")
        self.stdout.write("Give ONLY human_rating_sheet.csv to the human rater. Then run compare_human_scores.")

    def collect(self, o):
        units = []
        msgs = Message.objects.select_related("round__block", "round__participant").order_by("round_id", "created", "id")
        if not o["include_pilot"]:
            msgs = msgs.filter(round__participant__is_pilot=False)
        by_round = {}
        for m in msgs:
            by_round.setdefault(m.round, []).append(m)
        for rnd, ms in by_round.items():
            if rnd.kind == "probe":
                pairs, last_line = [], None
                for m in ms:
                    if m.role == "drlee":
                        last_line = m.text
                    elif m.probe_line and last_line:
                        pairs.append((last_line, m.text))
                kind = "probe"
            elif rnd.kind == "practice" and o["practice"]:
                pairs, prev = [], "(opening)"
                for m in ms:
                    if m.role == "learner":
                        pairs.append((prev, m.text))
                    else:
                        prev = m.text
                kind = "practice"
            else:
                continue
            if pairs:
                b = rnd.block
                units.append({"pid": rnd.participant.pid, "kind": kind, "block": b.position + 1, "design": b.design,
                              "scenario": b.scenario, "round": rnd.index + 1, "level": rnd.level or "", "pairs": pairs})
        if o["roleplay_dir"]:
            for f in sorted(Path(o["roleplay_dir"]).glob("*.txt")):
                pairs, last = [], None
                for line in f.read_text(encoding="utf-8").splitlines():
                    if line.lower().startswith("dr. lee:"):
                        last = line.split(":", 1)[1].strip()
                    elif line.lower().startswith("student:") and last:
                        pairs.append((last, line.split(":", 1)[1].strip()))
                units.append({"pid": f.stem, "kind": "roleplay", "block": "", "design": "", "scenario": "S4",
                              "round": "", "level": "", "pairs": pairs})
        return units

    @staticmethod
    def write(path, rows):
        if not rows:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
