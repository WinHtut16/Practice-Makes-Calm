"""Session flow and the core study logic (chat turns, probe, judge, controller).

The flow is a fixed list of steps, identical for every participant except for
the design/scenario of each block (from the counterbalancing table).
"""
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from . import llm, mock, prompts
from .content import DESIGNS, SCENARIOS, WARMUP
from .controller import next_level
from .counterbalance import sequence, shuffled_assignment
from .models import Block, Event, Message, Participant, Round

S = settings.STUDY


def steps():
    out = [("consent", None, None), ("pre", None, None), ("warmup", None, None)]
    for b in range(3):
        out.append(("card", b, None))
        for r in range(S["PRACTICE_ROUNDS"]):
            out += [("round", b, r), ("stress", b, r)]
        out += [("probe", b, None), ("block_survey", b, None), ("tags", b, None)]
        if b < 2:
            out.append(("break", b, None))
    out += [("human", None, None), ("human_survey", None, None), ("final", None, None), ("done", None, None)]
    return out


STEPS = steps()


def current_step(p):
    return STEPS[min(p.step, len(STEPS) - 1)]


def log(p, kind, detail=""):
    Event.objects.create(participant=p, kind=kind, detail=str(detail)[:2000])


# ----------------------------------------------------------------- setup

def multi_station():
    """True when this laptop owns only part of the main sequences (two-laptop mode)."""
    return bool(S["STATION_SEQUENCES"])


def assignment_order(is_pilot=False):
    """Order in which arriving participants receive sequence numbers on THIS laptop.

    Main study: the balanced 3-sequence square first (random order within it), then the other two.
    In two-laptop mode only this station's sequences are used (STATION_SEQUENCES), in the same order.
    Pilot: the remaining 13 sequences, offset by 100 so pilot IDs never clash with the main study.
    In two-laptop mode, station A takes every other pilot sequence and station B the rest.
    """
    import random
    rng = random.Random(S["ASSIGNMENT_SEED"] + (1 if is_pilot else 0))
    main = list(S["MAIN_SEQUENCES"])
    if is_pilot:
        rest = [n for n in shuffled_assignment(S["ASSIGNMENT_SEED"]) if n not in main]
        if multi_station():
            rest = rest[1::2] if S["STATION"] == "B" else rest[0::2]
        return [n + 100 for n in rest]
    square, extra = main[:3], main[3:]
    rng.shuffle(square); rng.shuffle(extra)
    order = square + extra
    if multi_station():
        order = [n for n in order if n in S["STATION_SEQUENCES"]]
    return order


def free_sequences(is_pilot=False):
    used = set(Participant.objects.filter(is_pilot=is_pilot).values_list("sequence_no", flat=True))
    return [n for n in assignment_order(is_pilot) if n not in used]


def make_pid(n, is_pilot):
    return f"PILOT{S['STATION'] if multi_station() else ''}{n - 100:02d}" if is_pilot else f"P{n:02d}"


@transaction.atomic
def create_participant(is_pilot=False, sequence_no=None):
    """Give the next arriving participant the next free sequence number (or the one the researcher chose)."""
    free = free_sequences(is_pilot)
    if not free:
        raise ValueError("All sequences on this laptop are used. Replace a withdrawn participant via the admin.")
    if sequence_no is not None:
        if sequence_no not in free:
            raise ValueError(f"Sequence {sequence_no} is not free on this laptop.")
        n = sequence_no
    else:
        n = free[0]
    seq_n = n - 100 if is_pilot else n
    from .version import config_hash
    p = Participant.objects.create(pid=make_pid(n, is_pilot), sequence_no=n, is_pilot=is_pilot,
                                   station=S["STATION"], config_hash=config_hash())
    for pos, (design, scen) in enumerate(sequence(seq_n)):
        Block.objects.create(participant=p, position=pos, design=design, scenario=scen,
                             current_level=S["ADAPTIVE_START_LEVEL"])
    log(p, "created", f"station {p.station}, config {p.config_hash}, sequence {seq_n}: {sequence(seq_n)}")
    return p


def advance(p):
    p.step = min(p.step + 1, len(STEPS) - 1)
    if STEPS[p.step][0] == "done" and not p.finished:
        p.finished = timezone.now()
    p.save()


# ----------------------------------------------------------------- rounds

def block_at(p, b):
    return p.blocks.get(position=b)


def level_for(block):
    fixed = DESIGNS[block.design]["fixed_level"]
    return fixed if fixed else block.current_level


def get_or_create_round(p, kind, b=None, r=0):
    block = block_at(p, b) if b is not None else None
    rnd = Round.objects.filter(participant=p, kind=kind, block=block, index=r).first()
    if rnd:
        return rnd
    level = level_for(block) if kind == "practice" else None
    rnd = Round.objects.create(participant=p, kind=kind, block=block, index=r, level=level)
    log(p, "round_start", f"{kind} b{b} r{r} level {level}")
    return rnd


def history(rnd):
    """Conversation as (role, text) for the LLM: learner = user, Dr. Lee/Sam = model."""
    return [("user" if m.role == "learner" else "model", m.text) for m in rnd.messages.all()]


def _close(rnd, reason):
    if rnd.ended is None:
        rnd.ended = timezone.now()
        rnd.end_reason = reason
        rnd.save()


def learner_count(rnd):
    return rnd.messages.filter(role="learner").count()


def chat_turn(p, rnd, text):
    """Handle one learner message in a practice or warm-up round. Returns dict for the UI."""
    if not rnd.is_open:
        return {"done": True, "reply": None, "reason": rnd.end_reason}
    text = text.strip()[:1000]
    learner_msg = Message.objects.create(round=rnd, role="learner", text=text, level=rnd.level)

    if rnd.kind == "warmup":
        system, temp, mock_fn = WARMUP["system"], 0.7, mock.warmup
    else:
        scen = rnd.block.scenario
        system, temp, mock_fn = prompts.dr_lee_system(scen, rnd.level), S["TEMP_DR_LEE"], mock.dr_lee(scen, rnd.level)

    try:
        res = llm.generate(system, history(rnd), temperature=temp, mock_fn=mock_fn)
    except llm.LLMError as e:
        # Remove the unanswered message so the conversation keeps alternating; the UI puts the text back.
        learner_msg.delete()
        log(p, "llm_error", e)
        p.needs_attention, p.attention_note = True, "LLM error: please check"
        p.save()
        return {"done": False, "reply": None, "error": "Connection problem. Please send your message again.", "restore": text}

    clean, agreed = llm.strip_agreed(res.text)
    Message.objects.create(round=rnd, role="drlee", text=clean, raw_text=res.text, latency_ms=res.latency_ms,
                           model=res.model, level=rnd.level)
    reason = None
    if agreed:
        reason = "agreed"
    elif learner_count(rnd) >= S["ROUND_MAX_MESSAGES"]:
        reason = "max_messages"
    if reason:
        _close(rnd, reason)
    return {"done": bool(reason), "reply": clean, "reason": reason}


def timeout_round(p, rnd, reason="timeout"):
    """Close a round because time ran out, or because the participant or researcher chose to stop it."""
    _close(rnd, reason)
    log(p, f"round_{reason}", f"round {rnd.id}")


def researcher_skip(p):
    """Researcher moves the participant past the current step (they asked to skip it). Logged."""
    step, b, r = current_step(p)
    if step in ("warmup", "round", "probe"):
        kind = {"warmup": "warmup", "round": "practice", "probe": "probe"}[step]
        rnd = get_or_create_round(p, kind, b, r if step == "round" else 0)
        _close(rnd, "skipped")
    log(p, "researcher_skip", f"{step} b{b} r{r}")
    if step != "done":
        advance(p)


# ----------------------------------------------------------------- probe

PROBE_CLOSING = "Thank you. Let's stop here for now."


def probe_turn(p, rnd, text):
    """Fixed probe: learner opens, then Dr. Lee's three fixed lines, one after each reply."""
    if not rnd.is_open:
        return {"done": True, "reply": None}
    lines = SCENARIOS[rnd.block.scenario]["probe"]
    n_learner = learner_count(rnd)  # learner messages before this one
    # Reply to fixed line k is the learner's (k+1)-th message (the first message is the opening request).
    Message.objects.create(round=rnd, role="learner", text=text.strip()[:1000], probe_line=(n_learner or None))
    if n_learner < len(lines):
        reply = lines[n_learner]
        Message.objects.create(round=rnd, role="drlee", text=reply, model="fixed")
        return {"done": False, "reply": reply}
    Message.objects.create(round=rnd, role="drlee", text=PROBE_CLOSING, model="fixed")
    _close(rnd, "probe_done")
    return {"done": True, "reply": PROBE_CLOSING}


# ----------------------------------------------------------------- after a round

def record_stress(p, rnd, stress, reflection=""):
    """Save the stress tap (and optional reflection note); in the adaptive design run the judge and the controller."""
    rnd.stress = stress
    rnd.reflection = (reflection or "").strip()[:300]
    block = rnd.block
    if stress >= S["PAUSE_IF_STRESS_GE"]:
        p.needs_attention, p.attention_note = True, f"Stress {stress} after block {block.position + 1} round {rnd.index + 1}"
        p.save()
        log(p, "high_stress", stress)

    if block.design == "A":
        # The judge sees the whole round (Dr. Lee's lines give context) but scores only the student's messages.
        transcript = "\n".join(f"{'Student' if m.role == 'learner' else 'Dr. Lee'}: {m.text}" for m in rnd.messages.all())
        desc = None
        try:
            res = llm.generate(prompts.judge_system(block.scenario), [("user", "Conversation:\n" + (transcript or "(none)"))],
                               temperature=S["TEMP_JUDGE"], as_json=True, max_tokens=512, mock_fn=mock.judge,
                               schema=prompts.JUDGE_SCHEMA)
            rnd.judge_raw = res.text
            data = llm.parse_json(res.text)
            parts = [max(0, min(2, int(data.get(k, 0)))) for k in "DESC"]
            rnd.judge_d, rnd.judge_e, rnd.judge_s, rnd.judge_c = parts
            desc = sum(parts)
            rnd.judge_total = desc
        except Exception as e:  # judge failure: keep the level and flag it
            log(p, "judge_error", e)
        if rnd.index >= S["PRACTICE_ROUNDS"] - 1:
            # Last practice round: the judge score is kept as data, but no level change (there is no next round).
            new, decision = block.current_level, "none(last_round)"
        elif desc is None:
            new, decision = block.current_level, "keep(judge_failed)"
        else:
            new, decision = next_level(block.current_level, stress, desc)
        rnd.decision, rnd.next_level = decision, new
        block.current_level = new
        block.save()
        log(p, "controller", f"b{block.position} r{rnd.index}: level {rnd.level}, stress {stress}, desc {desc} -> {decision} -> {new}")
    rnd.save()
