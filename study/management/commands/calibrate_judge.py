"""Pilot stage P2: compare the judge (or scorer) with two human raters.

Input CSV columns: scenario, reply, human_a, human_b   (human_* = DESC total 0-8)
    python manage.py calibrate_judge replies.csv --sleep 5
"""
import csv
import time

from django.conf import settings
from django.core.management.base import BaseCommand

from study import llm, mock, prompts

from ._stats import icc_2_1


class Command(BaseCommand):
    help = "Pilot P2: agreement between the LLM judge and two human DESC raters (ICC and within +/-1)."

    def add_arguments(self, parser):
        parser.add_argument("csv_path")
        parser.add_argument("--sleep", type=float, default=0.0)
        parser.add_argument("--out", default="pilot_out/p2_results.csv")

    def handle(self, *args, **o):
        rows = list(csv.DictReader(open(o["csv_path"], newline="", encoding="utf-8")))
        results = []
        for r in rows:
            res = llm.generate(prompts.judge_system(r["scenario"]), [("user", "Student messages:\n- " + r["reply"])],
                               temperature=settings.STUDY["TEMP_JUDGE"], as_json=True, max_tokens=512, mock_fn=mock.judge,
                               schema=prompts.JUDGE_SCHEMA)
            d = llm.parse_json(res.text)
            judge = sum(max(0, min(2, int(d.get(k, 0)))) for k in "DESC")
            results.append({**r, "judge": judge, "rationale": d.get("rationale", "")})
            time.sleep(o["sleep"])
        a = [float(r["human_a"]) for r in results]
        b = [float(r["human_b"]) for r in results]
        j = [float(r["judge"]) for r in results]
        human_mean = [(x + y) / 2 for x, y in zip(a, b)]
        icc_humans = icc_2_1([[x, y] for x, y in zip(a, b)])
        icc_all = icc_2_1([[x, y, z] for x, y, z in zip(a, b, j)])
        within1 = sum(abs(z - m) <= 1 for z, m in zip(j, human_mean)) / len(j)
        with open(o["out"], "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
            w.writeheader(); w.writerows(results)
        self.stdout.write(f"Replies: {len(results)}")
        self.stdout.write(f"ICC(2,1) human A vs B:          {icc_humans:.2f}")
        self.stdout.write(f"ICC(2,1) humans + judge:        {icc_all:.2f}   (target >= .75)")
        self.stdout.write(f"Judge within +/-1 of human mean: {100 * within1:.0f}%   (target >= 80%)")
        worst = sorted(results, key=lambda r: -abs(float(r["judge"]) - (float(r["human_a"]) + float(r["human_b"])) / 2))[:5]
        self.stdout.write("\nBiggest disagreements (fix the rubric anchors for these):")
        for r in worst:
            self.stdout.write(f"  judge {r['judge']} vs humans {r['human_a']}/{r['human_b']}: {r['reply'][:90]}")
        self.stdout.write(f"\nSaved {o['out']}")
