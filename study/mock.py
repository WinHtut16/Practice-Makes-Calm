"""Deterministic stand-ins for the LLM, used when no API key is set (LLM_MOCK=1).

They let you click through the whole session and run the tests offline. They are
NOT a substitute for the real model in pilots.
"""
import json
import re

from .content import SCENARIOS


def _learner_turns(history):
    return sum(1 for r, _ in history if r == "user")


def dr_lee(scenario_id, level):
    pushbacks = {1: 1, 2: 2, 3: 3}[level]

    def fn(system, history):
        n = _learner_turns(history)
        ex = SCENARIOS[scenario_id]["examples"][level]
        if n > pushbacks - (1 if level == 1 else 0):
            return "All right, that works for me. Let's do that. [AGREED]"
        return ex[(n - 1) % len(ex)]
    return fn


def warmup(system, history):
    return "Sure, why do you need Thursday?" if _learner_turns(history) < 2 else "No problem, let's swap. [AGREED]"


def _heuristic_desc(text):
    t = text.lower()
    d = 2 if re.search(r"\b(because|corrupt|deadline|imbalanc|lost|broke|sick)\b", t) else (1 if len(t) > 20 else 0)
    e = 2 if re.search(r"\b(i need|i want|i believe|i think|i feel)\b", t) else (1 if " i " in f" {t} " else 0)
    s = 2 if re.search(r"\b(monday|tuesday|wednesday|thursday|friday|next week|instead|propose|could i|can i)\b", t) else (1 if "?" in t else 0)
    c = 2 if re.search(r"\b(so that|will be|which means|otherwise|valid|better results)\b", t) else 0
    return d, e, s, c


def judge(system, history):
    lines = history[-1][1].splitlines()
    text = " ".join(l.split(":", 1)[1] for l in lines if l.startswith("Student:")) or history[-1][1]
    d, e, s, c = _heuristic_desc(text)
    return json.dumps({"D": d, "E": e, "S": s, "C": c, "rationale": "mock heuristic"})


def scorer(system, history):
    text = history[-1][1].lower()
    d, e, s, c = _heuristic_desc(text)
    strategies = []
    if "sorry" in text:
        strategies.append("apologize")
    if "because" in text:
        strategies.append("justify")
    if re.search(r"\b(will|plan|by|next)\b", text):
        strategies.append("plan")
    if "okay" in text or "fine" in text:
        strategies.append("concede")
    return json.dumps({"D": d, "E": e, "S": s, "C": c, "strategies": strategies, "rationale": "mock heuristic"})


def learner(persona):
    lines = {
        "weak": ["Sorry, my experiment didn't work.", "Sorry, I don't know, I just need some time.", "Okay, sorry."],
        "medium": ["My sensor data was corrupted on Monday, so I need more time.", "I can rerun it next week.", "I think next Friday."],
        "strong": ["The sensor data from Monday was corrupted, so I lost three days. Could I submit next Friday instead? "
                   "I will send partial results on Wednesday, so the report will be valid."],
    }[persona]

    def fn(system, history):
        n = sum(1 for r, _ in history if r == "user") - 1  # first "user" turn is the opener prompt
        return lines[min(n, len(lines) - 1)]
    return fn
