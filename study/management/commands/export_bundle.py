"""Write all of this laptop's study data to one JSON file, for merging with the other laptop.

    python manage.py export_bundle                 # main-study participants only
    python manage.py export_bundle --include-pilot # also pilot participants
"""
import json
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from study import bundle
from study.models import Participant
from study.version import config_hash, config_summary


class Command(BaseCommand):
    help = "Export this laptop's participants (with all rounds, messages, tags, surveys, events) to a JSON bundle."

    def add_arguments(self, parser):
        parser.add_argument("--out", default="bundles")
        parser.add_argument("--include-pilot", action="store_true")

    def handle(self, *args, **o):
        ps = Participant.objects.all() if o["include_pilot"] else Participant.objects.filter(is_pilot=False)
        station = settings.STUDY["STATION"]
        data = bundle.dump(ps, station, config_hash(), config_summary())
        out = Path(o["out"]); out.mkdir(exist_ok=True)
        path = out / f"bundle_{station}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        hashes = sorted({p.config_hash for p in ps})
        self.stdout.write(f"Wrote {path} ({len(data['participants'])} participants, station {station}).")
        self.stdout.write(f"Config hashes in this bundle: {', '.join(h or '(none)' for h in hashes) or '-'}")
        self.stdout.write("Send this file to the person who merges the data. It contains chat text: share it privately.")
