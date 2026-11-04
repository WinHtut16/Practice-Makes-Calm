"""Agreement between the scorer (LLM 3) and the blind human rater (paper: ICC >= .75, kappa >= .60)."""
import csv

from django.core.management.base import BaseCommand

from study.prompts import STRATEGIES

from ._stats import cohen_kappa, icc_2_1


class Command(BaseCommand):
    help = "Compare human_rating_sheet.csv (filled in) with scores_blind.csv."

    def add_arguments(self, parser):
        parser.add_argument("--human", default="scoring_out/human_rating_sheet.csv")
        parser.add_argument("--llm", default="scoring_out/scores_blind.csv")

    def handle(self, *args, **o):
        llm_rows = {(r["blind_id"], r["reply_no"]): r for r in csv.DictReader(open(o["llm"], encoding="utf-8"))}
        pairs = []
        for h in csv.DictReader(open(o["human"], encoding="utf-8")):
            key = (h["blind_id"], h["reply_no"])
            if key in llm_rows and all(h[c].strip() for c in "DESC"):
                pairs.append((h, llm_rows[key]))
        if not pairs:
            self.stderr.write("No completed human ratings found.")
            return
        totals = [[sum(float(h[c]) for c in "DESC"), float(l["desc_total"])] for h, l in pairs]
        self.stdout.write(f"Replies compared: {len(pairs)}")
        self.stdout.write(f"DESC total ICC(2,1): {icc_2_1(totals):.2f}  (target >= .75)")
        for s in STRATEGIES:
            a = [int(h[s] or 0) for h, _ in pairs]
            b = [int(l[s]) for _, l in pairs]
            self.stdout.write(f"  {s:<10} kappa {cohen_kappa(a, b):.2f}  (target >= .60)")
        self.stdout.write("If below target, the human rater scores all transcripts and human scores become primary (paper, 3.6).")
