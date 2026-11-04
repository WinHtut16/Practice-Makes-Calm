import json

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import flow
from .content import (BLOCK_ITEMS, CARD_HINT, COLOURS, DESC_GUIDE, DESIGNS, INTERVIEW_QUESTIONS, PROBE_INTRO, S4, SCENARIOS,
                      SELF_EFFICACY, STAI6, STAI_LABELS, TAGS, WARMUP, stai_score)
from .models import Message, Participant, Response, Round, Tag

S = settings.STUDY

# ------------------------------------------------------------------ form specs


def stai_fields(prefix="stai"):
    return [{"name": f"{prefix}{i + 1}", "label": item, "type": "radio",
             "options": [(str(v + 1), lab) for v, lab in enumerate(STAI_LABELS)]}
            for i, (item, _) in enumerate(STAI6)]


def se_fields():
    return [{"name": f"se{i + 1}", "label": q, "type": "likert", "min": 1, "max": 7,
             "low": "Not at all confident", "high": "Completely confident"} for i, q in enumerate(SELF_EFFICACY)]


PRE_FIELDS = [
    {"name": "age", "label": "Age", "type": "number", "min": 18, "max": 99},
    {"name": "gender", "label": "Gender", "type": "radio",
     "options": [("woman", "Woman"), ("man", "Man"), ("nonbinary", "Non-binary"), ("na", "Prefer not to say")]},
    {"name": "program", "label": "Program", "type": "radio", "options": [("masters", "Master's"), ("phd", "PhD")]},
    {"name": "year", "label": "Year in program", "type": "number", "min": 1, "max": 10},
    {"name": "first_language", "label": "First language", "type": "text"},
    {"name": "english_comfort", "label": "How comfortable are you speaking English with professors?", "type": "likert",
     "min": 1, "max": 7, "low": "Not at all comfortable", "high": "Very comfortable"},
    {"name": "prior_experience", "label": "How often have you had to ask an advisor or professor for something difficult?",
     "type": "likert", "min": 1, "max": 7, "low": "Never", "high": "Very often"},
    {"name": "llm_use", "label": "How often do you use AI chatbots (e.g., ChatGPT, Gemini)?", "type": "radio",
     "options": [("never", "Never"), ("monthly", "A few times a month"), ("weekly", "Weekly"), ("daily", "Daily")]},
]


def block_fields():
    items = [{"name": n, "label": q, "type": "likert", "min": 1, "max": 7, "low": lo, "high": hi} for n, q, lo, hi in BLOCK_ITEMS]
    return stai_fields() + se_fields() + items


HUMAN_FIELDS = stai_fields() + [
    {"name": "human_vs_ai", "label": "Compared with the AI, how stressful was talking to the real person?",
     "type": "likert", "min": 1, "max": 7, "low": "Much less stressful", "high": "Much more stressful"}]


def parse_fields(post, fields):
    data, errors = {}, []
    for f in fields:
        v = post.get(f["name"], "").strip()
        if not v and not f.get("optional"):
            errors.append(f["label"])
            continue
        if f["type"] in ("number", "likert") and v:
            try:
                iv = int(v)
                if not f["min"] <= iv <= f["max"]:
                    raise ValueError
                v = iv
            except ValueError:
                errors.append(f["label"])
                continue
        data[f["name"]] = v
    return data, errors


def add_scores(data):
    if all(f"stai{i}" in data for i in range(1, 7)):
        data["stai_score"] = stai_score([int(data[f"stai{i}"]) for i in range(1, 7)])
    n = len(SELF_EFFICACY)
    if all(f"se{i}" in data for i in range(1, n + 1)):
        data["self_efficacy"] = round(sum(int(data[f"se{i}"]) for i in range(1, n + 1)) / n, 2)
    return data


# ------------------------------------------------------------------ participant pages

def index(request):
    return render(request, "study/index.html")


def session(request, pid):
    p = get_object_or_404(Participant, pid=pid)
    step, b, r = flow.current_step(p)
    ctx = {"p": p, "step": step, "b": b, "r": r, "error": None, "cfg": S,
           "progress": int(100 * p.step / (len(flow.STEPS) - 1)), "pause": request.GET.get("pause") == "1",
           "posted": request.POST if request.method == "POST" else {}, "card_hint": CARD_HINT}
    block = flow.block_at(p, b) if b is not None else None
    if block:
        ctx.update(block=block, colour=block.colour, scenario=SCENARIOS[block.scenario])

    if request.method == "POST":
        # A double-click or browser resend arrives with an old step number: ignore it, show the current page.
        if request.POST.get("step_no") != str(p.step):
            flow.log(p, "stale_submit", f"posted step {request.POST.get('step_no')} while at {p.step} ({step})")
            return redirect("session", pid=pid)
        err = handle_post(request, p, step, b, r, block)
        if err is None:
            flow.advance(p)
            if step == "stress" and int(request.POST.get("stress", 0)) >= S["PAUSE_IF_STRESS_GE"]:
                return redirect(f"/s/{pid}/?pause=1")
            return redirect("session", pid=pid)
        ctx["error"] = err

    # Safety net: a stress page whose practice round was never shown goes back to that round.
    if step == "stress" and not Round.objects.filter(participant=p, kind="practice", block=block, index=r).exists():
        flow.log(p, "repair", f"round b{b} r{r} missing; returning to it")
        p.step -= 1
        p.save()
        return redirect("session", pid=pid)

    # GET (or re-render after error)
    if step == "pre":
        ctx["fields"] = PRE_FIELDS + stai_fields() + se_fields()
        ctx["title"] = "About you"
    elif step == "block_survey":
        ctx["fields"] = block_fields()
        ctx["title"] = f"About the {block.colour} Dr. Lee"
    elif step == "human_survey":
        ctx["fields"] = HUMAN_FIELDS
        ctx["title"] = "About the conversation with the real person"
    elif step == "warmup":
        ctx["rnd"] = flow.get_or_create_round(p, "warmup")
        ctx["card"], ctx["partner"] = WARMUP, "Sam"
    elif step == "round":
        ctx["rnd"] = flow.get_or_create_round(p, "practice", b, r)
        ctx["partner"] = "Dr. Lee"
    elif step == "probe":
        ctx["rnd"] = flow.get_or_create_round(p, "probe", b, 0)
        ctx["partner"] = "Dr. Lee"
        ctx["probe_intro"] = PROBE_INTRO
    elif step == "tags":
        idx = list(range(S["PRACTICE_ROUNDS"]))
        # Show the whole conversation (the participant's own turns give context); only Dr. Lee's turns get tags.
        msgs = Message.objects.filter(round__block=block, round__kind="practice", round__index__in=idx).select_related("round")
        ctx["tag_rounds"] = [(i + 1, [m for m in msgs if m.round.index == i]) for i in idx]
        ctx["tags"] = TAGS
    elif step == "human":
        ctx["s4"] = S4
    elif step == "final":
        ctx["colours"] = COLOURS
    elif step == "done":
        ctx["desc_guide"] = DESC_GUIDE
        ctx["probe_replies"] = [
            (bl.colour, SCENARIOS[bl.scenario]["title"],
             list(Message.objects.filter(round__block=bl, round__kind="probe", role="learner", probe_line__isnull=False)))
            for bl in p.blocks.all()]
    if "rnd" in ctx:
        ctx["messages_list"] = list(ctx["rnd"].messages.all())
        ctx["learner_count"] = flow.learner_count(ctx["rnd"])
    return render(request, f"study/step_{step if step not in ('pre', 'block_survey', 'human_survey') else 'form'}.html", ctx)


def handle_post(request, p, step, b, r, block):
    """Validate and save a step. Return an error string, or None to advance."""
    post = request.POST
    if step == "consent":
        return None if post.get("agree") == "yes" else "Please tick the box to give consent, or tell the researcher."
    if step in ("pre", "block_survey", "human_survey"):
        fields = {"pre": PRE_FIELDS + stai_fields() + se_fields(), "block_survey": block_fields(), "human_survey": HUMAN_FIELDS}[step]
        data, errors = parse_fields(post, fields)
        if errors:
            return "Please answer: " + "; ".join(errors[:4]) + (" ..." if len(errors) > 4 else "")
        kind = {"pre": "pre", "block_survey": "block", "human_survey": "human"}[step]
        Response.objects.create(participant=p, block=block, kind=kind, data=add_scores(data))
        return None
    if step in ("warmup", "round", "probe"):
        kind = {"warmup": "warmup", "round": "practice", "probe": "probe"}[step]
        rnd = Round.objects.filter(participant=p, kind=kind, block=block, index=(r if step == "round" else 0)).first()
        if rnd is None:
            return "Please complete this conversation first."
        if rnd.is_open:
            if step == "probe":
                return "Please reply to Dr. Lee until the conversation ends."
            flow.timeout_round(p, rnd)
        return None
    if step == "stress":
        try:
            v = int(post.get("stress", ""))
            assert 0 <= v <= 10
        except (ValueError, AssertionError):
            return "Please choose a number from 0 to 10."
        rnd = Round.objects.filter(participant=p, kind="practice", block=block, index=r).first()
        if rnd is None:
            return "This round was not completed. Please reload the page."
        flow.record_stress(p, rnd, v, post.get("reflection", ""))
        return None
    if step == "tags":
        msgs = Message.objects.filter(round__block=block, round__kind="practice",
                                      round__index__in=range(S["PRACTICE_ROUNDS"]), role="drlee")
        for m in msgs:
            reason = post.get(f"reason_{m.id}", "").strip()[:300]
            for t in TAGS:
                if post.get(f"tag_{m.id}_{t}"):
                    Tag.objects.create(message=m, tag=t, reason=reason)
        return None
    if step == "final":
        ranks = [post.get(f"rank{i}") for i in (1, 2, 3)]
        if sorted(r_ for r_ in ranks if r_) != sorted(COLOURS):
            return "Please give each colour a different rank."
        Response.objects.create(participant=p, kind="final", data={"rank1": ranks[0], "rank2": ranks[1], "rank3": ranks[2]})
        return None
    return None  # card, break, human: just continue


@require_POST
def api_chat(request, pid):
    p = get_object_or_404(Participant, pid=pid)
    step, b, r = flow.current_step(p)
    try:
        text = json.loads(request.body or b"{}").get("text", "")
    except json.JSONDecodeError:
        return HttpResponseBadRequest("bad json")
    if not text.strip():
        return JsonResponse({"error": "Please type a message."}, status=400)
    if step == "warmup":
        return JsonResponse(flow.chat_turn(p, flow.get_or_create_round(p, "warmup"), text))
    if step == "round":
        return JsonResponse(flow.chat_turn(p, flow.get_or_create_round(p, "practice", b, r), text))
    if step == "probe":
        return JsonResponse(flow.probe_turn(p, flow.get_or_create_round(p, "probe", b, 0), text))
    return JsonResponse({"error": "No conversation on this page."}, status=400)


@require_POST
def api_timeout(request, pid):
    p = get_object_or_404(Participant, pid=pid)
    step, b, r = flow.current_step(p)
    try:
        reason = json.loads(request.body or b"{}").get("reason", "timeout")
    except json.JSONDecodeError:
        reason = "timeout"
    reason = "skipped" if reason == "skipped" else "timeout"
    if step in ("warmup", "round"):
        rnd = flow.get_or_create_round(p, "warmup" if step == "warmup" else "practice", b, r if step == "round" else 0)
        if rnd.is_open:
            flow.timeout_round(p, rnd, reason)
    return JsonResponse({"done": True, "reason": reason})


# ------------------------------------------------------------------ researcher pages

@staff_member_required
def researcher(request):
    return render(request, "study/researcher.html", console_ctx())


def console_ctx(error=None):
    from .version import config_hash
    ps = Participant.objects.all()
    hashes = sorted({p.config_hash for p in ps if p.config_hash})
    return {"rows": [(p, flow.current_step(p)[0]) for p in ps], "real_used": ps.filter(is_pilot=False).count(),
            "cfg": S, "error": error, "config_hash": config_hash(), "station": S["STATION"],
            "multi": flow.multi_station(), "free_main": flow.free_sequences(False),
            "free_pilot": [n - 100 for n in flow.free_sequences(True)],
            "hash_changed": [h for h in hashes if h != config_hash()]}


@staff_member_required
@require_POST
def researcher_new(request):
    is_pilot = request.POST.get("pilot") == "1"
    choice = request.POST.get("pilot_seq" if is_pilot else "main_seq", "").strip()
    try:
        seq = (int(choice) + (100 if is_pilot else 0)) if choice else None
        p = flow.create_participant(is_pilot=is_pilot, sequence_no=seq)
    except ValueError as e:
        return render(request, "study/researcher.html", console_ctx(str(e)))
    return redirect("monitor", pid=p.pid)


@staff_member_required
def monitor(request, pid):
    p = get_object_or_404(Participant, pid=pid)
    if request.method == "POST":
        if "clear" in request.POST:
            p.needs_attention, p.attention_note = False, ""
        if "notes" in request.POST:
            p.notes = request.POST["notes"]
        p.save()
        if "skip" in request.POST:
            flow.researcher_skip(p)
        return redirect("monitor", pid=pid)
    step, b, r = flow.current_step(p)
    reveal = request.GET.get("reveal") == "1"
    rounds = p.rounds.prefetch_related("messages").select_related("block")
    latest = rounds.last()
    return render(request, "study/monitor.html", {
        "p": p, "step": step, "b": b, "r": r, "reveal": reveal, "blocks": p.blocks.all(), "designs": DESIGNS,
        "latest": latest, "rounds": rounds, "events": p.events.all()[:15], "s4": S4,
        "interview": INTERVIEW_QUESTIONS, "show_script": step in ("human", "human_survey"),
        "step_no": p.step + 1, "step_total": len(flow.STEPS),
    })
