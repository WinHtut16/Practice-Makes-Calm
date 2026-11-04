"""Config fingerprint: one short hash of everything that defines the experimental conditions.

Stored on every participant, so data from two laptops can only be merged if both ran the same
prompts, materials, model and thresholds. Line endings are normalised, so a Windows checkout
(CRLF) and a Linux checkout (LF) of the same files give the same hash.
"""
import hashlib
import json
from pathlib import Path

from django.conf import settings

HERE = Path(__file__).resolve().parent
FILES = ["content.py", "prompts.py", "controller.py", "counterbalance.py", "flow.py"]
KEYS = ["PROVIDER", "MODEL", "CLAUDE_EFFORT", "MOCK", "PRACTICE_ROUNDS", "ROUND_SECONDS", "ROUND_MAX_MESSAGES",
        "ADAPTIVE_START_LEVEL", "LOWER_IF_STRESS_GE", "LOWER_IF_DESC_LE", "RAISE_IF_STRESS_LE", "RAISE_IF_DESC_GE",
        "MAIN_SEQUENCES", "ASSIGNMENT_SEED", "REFLECTION_PROMPT"]


def config_hash():
    h = hashlib.sha256()
    for name in FILES:
        h.update(name.encode())
        h.update((HERE / name).read_bytes().replace(b"\r\n", b"\n"))
    h.update(json.dumps({k: settings.STUDY.get(k) for k in KEYS}, sort_keys=True, default=str).encode())
    return h.hexdigest()[:12]


def config_summary():
    return {k: settings.STUDY.get(k) for k in KEYS}
