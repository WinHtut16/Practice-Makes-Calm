"""Load JSON bundles from several laptops into ONE fresh analysis database.

Use a separate database file so the laptops' own data is never touched (PowerShell):

    $env:DB_NAME = "analysis.sqlite3"
    python manage.py migrate
    python manage.py merge_bundles bundles\\bundle_A_....json bundles\\bundle_B_....json
    python manage.py export_csv          # then score_transcripts, as usual, on the merged data

Checks: a participant ID or sequence that already exists is refused (the two laptops must own different
sequences); participants run under different config hashes are refused unless --allow-config-mismatch.
"""
import json
from collections import Counter

from django.core.management.base import BaseCommand, CommandError

from study import bundle
from study.models import Participant


class Command(BaseCommand):
    help = "Merge export_bundle files from several laptops into the current (analysis) database."

    def add_arguments(self, parser):
        parser.add_argument("files", nargs="+")
        parser.add_argument("--allow-config-mismatch", action="store_true",
                            help="merge even if participants ran under different prompts or settings (pilots only)")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **o):
        items = []
        for f in o["files"]:
            data = json.loads(open(f, encoding="utf-8").read())
            if data.get("format") != bundle.FORMAT:
                raise CommandError(f"{f}: not a Dr. Lee bundle")
            for d in data["participants"]:
                items.append((f, data.get("station", "?"), d))

        # 1. Same experimental conditions everywhere?
        hashes = Counter(d["participant"].get("config_hash", "") for _, _, d in items if not d["participant"]["is_pilot"])
        if len(hashes) > 1:
            msg = "Main-study participants ran under different configurations: " + \
                  ", ".join(f"{h or '(none)'} x{n}" for h, n in hashes.items())
            if not o["allow_config_mismatch"]:
                raise CommandError(msg + "\nCheck that both laptops used the same code, .env model and thresholds. "
                                         "Use --allow-config-mismatch only if you understand why.")
            self.stdout.write(self.style.WARNING(msg))

        # 2. No clashing IDs or sequences, inside the bundles or with the database.
        pids = Counter(d["participant"]["pid"] for _, _, d in items)
        seqs = Counter((d["participant"]["is_pilot"], d["participant"]["sequence_no"]) for _, _, d in items)
        dup_p = [k for k, n in pids.items() if n > 1]
        dup_s = [k[1] for k, n in seqs.items() if n > 1]
        if dup_p or dup_s:
            raise CommandError(f"Duplicate participant IDs {dup_p} or sequences {dup_s} across bundles. "
                               "Both laptops handed out the same sequence: set STATION and STATION_SEQUENCES "
                               "differently on each laptop. Rename or drop the duplicate before merging.")
        loaded = 0
        for f, station, d in items:
            pd = d["participant"]
            if Participant.objects.filter(pid=pd["pid"]).exists() or \
                    Participant.objects.filter(sequence_no=pd["sequence_no"]).exists():
                self.stdout.write(self.style.WARNING(f"skip {pd['pid']} from {f}: already in this database"))
                continue
            n_msg = sum(len(r["messages"]) for r in d["rounds"])
            self.stdout.write(f"{'would load' if o['dry_run'] else 'load'} {pd['pid']:<9} station {station} "
                              f"config {pd.get('config_hash') or '-'}  rounds {len(d['rounds'])}  messages {n_msg}")
            if not o["dry_run"]:
                bundle.load_participant(d)
                loaded += 1
        self.stdout.write(self.style.SUCCESS(f"Done. {loaded} participants loaded."))
