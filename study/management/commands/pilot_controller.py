"""Pilot stage P3: replay stress/DESC traces through the adaptive rule."""
import random

from django.conf import settings
from django.core.management.base import BaseCommand

from study.controller import next_level

EXAMPLES = [
    ("Confident learner", [(3, 7), (4, 7)]),
    ("Distressed but skilled", [(9, 7), (9, 7)]),  # high stress must beat a good score
    ("Struggling", [(5, 1), (5, 2)]),
    ("Middle", [(5, 4), (6, 5)]),
]


class Command(BaseCommand):
    help = "Pilot P3: check the adaptive controller (reachability, 'lower' beats 'raise', oscillation)."

    def add_arguments(self, parser):
        parser.add_argument("--random", type=int, default=2000, help="number of random 3-round blocks to simulate")

    def handle(self, *args, **o):
        start = settings.STUDY["ADAPTIVE_START_LEVEL"]
        n_dec = settings.STUDY["PRACTICE_ROUNDS"] - 1
        self.stdout.write(f"Start level L{start}. {n_dec} decision(s) per block.\n")
        for name, trace in EXAMPLES:
            lv, path = start, [f"L{start}"]
            for s, d in trace[:n_dec]:
                lv, dec = next_level(lv, s, d)
                path.append(f"--(stress {s}, DESC {d}: {dec})--> L{lv}")
            self.stdout.write(f"{name:<24} " + " ".join(path))

        rng = random.Random(1)
        reached, flips = {1: 0, 2: 0, 3: 0}, 0
        for _ in range(o["random"]):
            lv, levels, decs = start, [start], []
            for _ in range(n_dec):
                lv, dec = next_level(lv, rng.randint(0, 10), rng.randint(0, 8))
                levels.append(lv); decs.append(dec)
            for l_ in set(levels):
                reached[l_] += 1
            if decs == ["raise", "lower"] or decs == ["lower", "raise"]:
                flips += 1
        n = o["random"]
        self.stdout.write("\nRandom traces (uniform stress 0-10, DESC 0-8; real data will differ):")
        for l_ in (1, 2, 3):
            self.stdout.write(f"  L{l_} used in {100 * reached[l_] / n:.0f}% of blocks")
        self.stdout.write(f"  Up-then-down or down-then-up in {100 * flips / n:.0f}% of blocks")
        self.stdout.write("\nAfter pilot P4, rerun the examples with the real stress/DESC values from the database (see export_csv rounds.csv).")
