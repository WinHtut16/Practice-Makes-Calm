"""Export all study data to CSV files for analysis (one folder per export)."""
import csv
from collections import Counter
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand

from study.content import DESIGNS
from study.models import Block, Message, Participant, Response, Round, Tag


def write(path, rows):
    if not rows:
        path.write_text("")
        return
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader(); w.writerows(rows)


class Command(BaseCommand):
    help = "Export participants, blocks (with surveys and tag counts), rounds, messages, tags and rankings to CSV."

    def add_arguments(self, parser):
        parser.add_argument("--out", default="exports")
        parser.add_argument("--include-pilot", action="store_true")

    def handle(self, *args, **o):
        out = Path(o["out"]) / datetime.now().strftime("%Y%m%d_%H%M%S")
        out.mkdir(parents=True)
        ps = Participant.objects.all() if o["include_pilot"] else Participant.objects.filter(is_pilot=False)

        prow, frow = [], []
        for p in ps:
            pre = Response.objects.filter(participant=p, kind="pre").last()
            human = Response.objects.filter(participant=p, kind="human").last()
            final = Response.objects.filter(participant=p, kind="final").last()
            row = {"pid": p.pid, "station": p.station, "config_hash": p.config_hash, "sequence_no": p.sequence_no,
                   "pilot": p.is_pilot, "created": p.created, "finished": p.finished,
                   "minutes": round((p.finished - p.created).total_seconds() / 60, 1) if p.finished else ""}
            row.update({f"pre_{k}": v for k, v in (pre.data if pre else {}).items()})
            row.update({f"human_{k}": v for k, v in (human.data if human else {}).items()})
            row["interview_notes"] = p.notes
            prow.append(row)
            if final:
                colour_to_design = {b.colour: b.design for b in p.blocks.all()}
                for rank in (1, 2, 3):
                    c = final.data[f"rank{rank}"]
                    frow.append({"pid": p.pid, "rank": rank, "colour": c, "design": colour_to_design.get(c, "")})
        write(out / "rankings.csv", frow)

        brow = []
        for b in Block.objects.filter(participant__in=ps).select_related("participant"):
            row = {"pid": b.participant.pid, "block": b.position + 1, "colour": b.colour, "design": b.design,
                   "design_name": DESIGNS[b.design]["name"], "scenario": b.scenario}
            s = Response.objects.filter(block=b, kind="block").last()
            row.update(s.data if s else {})
            # Practice exposure differs by design (a cooperative Dr. Lee agrees sooner), so report it next to outcomes.
            prs = list(b.rounds.filter(kind="practice"))
            row["practice_learner_messages"] = sum(r.messages.filter(role="learner").count() for r in prs)
            row["practice_seconds"] = sum(round((r.ended - r.started).total_seconds()) for r in prs if r.ended)
            row["practice_rounds_agreed"] = sum(r.end_reason == "agreed" for r in prs)
            row["practice_rounds_skipped"] = sum(r.end_reason == "skipped" for r in prs)
            row["adaptive_levels"] = "-".join(str(r.level) for r in sorted(prs, key=lambda r: r.index))
            tags = Counter(Tag.objects.filter(message__round__block=b).values_list("tag", flat=True))
            for t in ("unrealistic", "too harsh", "too easy", "helpful"):
                row[f"tags_{t.replace(' ', '_')}"] = tags.get(t, 0)
            brow.append(row)
        write(out / "blocks.csv", brow)

        rrow = []
        for r in Round.objects.filter(participant__in=ps).select_related("block", "participant"):
            n_l = r.messages.filter(role="learner").count()
            rrow.append({"pid": r.participant.pid, "kind": r.kind, "block": r.block.position + 1 if r.block else "",
                         "design": r.block.design if r.block else "", "scenario": r.block.scenario if r.block else "",
                         "round": r.index + 1, "level": r.level, "started": r.started, "ended": r.ended,
                         "seconds": round((r.ended - r.started).total_seconds()) if r.ended else "", "end_reason": r.end_reason,
                         "learner_messages": n_l, "stress": r.stress, "judge_D": r.judge_d, "judge_E": r.judge_e,
                         "judge_S": r.judge_s, "judge_C": r.judge_c, "judge_total": r.judge_total,
                         "decision": r.decision, "next_level": r.next_level, "reflection": r.reflection})
        write(out / "rounds.csv", rrow)

        # Typing speed proxy: characters per minute, from the moment the previous message appeared (or the round
        # started) to the moment the learner sent theirs. Includes reading time, so it underestimates true speed.
        mrow, last_time, cpm_by_pid = [], {}, {}
        msgs = (Message.objects.filter(round__participant__in=ps).select_related("round__block", "round__participant")
                .order_by("round_id", "created", "id"))
        for m in msgs:
            r = m.round
            prev = last_time.get(r.id, r.started)
            compose_s, cpm = "", ""
            if m.role == "learner":
                compose_s = round((m.created - prev).total_seconds(), 1)
                if compose_s and compose_s > 0 and r.kind in ("practice", "probe", "warmup"):
                    cpm = round(len(m.text) / compose_s * 60, 1)
                    cpm_by_pid.setdefault(r.participant.pid, []).append(cpm)
            last_time[r.id] = m.created
            mrow.append({"pid": r.participant.pid, "kind": r.kind, "block": r.block.position + 1 if r.block else "",
                         "design": r.block.design if r.block else "", "round": r.index + 1, "level": m.level,
                         "role": m.role, "probe_line": m.probe_line, "text": m.text, "words": len(m.text.split()),
                         "chars": len(m.text), "compose_seconds": compose_s, "chars_per_min": cpm,
                         "latency_ms": m.latency_ms, "model": m.model, "created": m.created})
        for row in prow:
            vals = sorted(cpm_by_pid.get(row["pid"], []))
            row["typing_cpm_median"] = vals[len(vals) // 2] if vals else ""
        write(out / "participants.csv", prow)
        write(out / "messages.csv", mrow)

        trow = [{"pid": t.message.round.participant.pid, "block": t.message.round.block.position + 1,
                 "design": t.message.round.block.design, "round": t.message.round.index + 1, "level": t.message.level,
                 "message": t.message.text, "tag": t.tag, "reason": t.reason}
                for t in Tag.objects.filter(message__round__participant__in=ps).select_related("message__round__block", "message__round__participant")]
        write(out / "tags.csv", trow)
        self.stdout.write(f"Exported to {out}")
