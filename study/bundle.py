"""Move study data between laptops without database key clashes.

Each laptop writes one JSON bundle (export_bundle). The bundles are loaded into one fresh
analysis database (merge_bundles). The bundle is nested by participant, so no database
IDs are copied: every row gets a new ID on import, and links are rebuilt from the nesting.
"""
from django.db import transaction
from django.utils.dateparse import parse_datetime

from .models import Block, Event, Message, Participant, Response, Round, Tag

FORMAT = "drlee-bundle-1"


def _fields(obj, skip=()):
    out = {}
    for f in obj._meta.concrete_fields:
        if f.primary_key or f.is_relation or f.name in skip:
            continue
        v = getattr(obj, f.name)
        out[f.name] = v.isoformat() if hasattr(v, "isoformat") else v
    return out


def dump_participant(p):
    blocks = {b.id: b.position for b in p.blocks.all()}
    return {
        "participant": _fields(p),
        "blocks": [_fields(b) for b in p.blocks.all()],
        "rounds": [{**_fields(r), "block_position": blocks.get(r.block_id),
                    "messages": [{**_fields(m), "tags": [_fields(t) for t in m.tags.all()]} for m in r.messages.all()]}
                   for r in p.rounds.all().prefetch_related("messages__tags")],
        "responses": [{**_fields(x), "block_position": blocks.get(x.block_id)} for x in p.responses.all()],
        "events": [_fields(e) for e in p.events.all()],
    }


def dump(participants, station, config_hash, config):
    return {"format": FORMAT, "station": station, "config_hash": config_hash, "config": config,
            "participants": [dump_participant(p) for p in participants]}


# Fields Django fills in automatically on create; restored afterwards with update().
AUTO_TIME = {Participant: "created", Round: "started", Message: "created", Response: "created", Tag: "created",
             Event: "created"}


def _make(model, data, **links):
    data = dict(data)
    stamp = data.pop(AUTO_TIME.get(model, "_none"), None)
    for f in model._meta.concrete_fields:
        if f.get_internal_type() == "DateTimeField" and isinstance(data.get(f.name), str):
            data[f.name] = parse_datetime(data[f.name])
    obj = model.objects.create(**data, **links)
    if stamp:
        model.objects.filter(pk=obj.pk).update(**{AUTO_TIME[model]: parse_datetime(stamp)})
    return obj


@transaction.atomic
def load_participant(d):
    p = _make(Participant, d["participant"])
    blocks = {b["position"]: _make(Block, b, participant=p) for b in d["blocks"]}
    for r in d["rounds"]:
        r = dict(r)
        msgs, pos = r.pop("messages"), r.pop("block_position")
        rnd = _make(Round, r, participant=p, block=blocks.get(pos))
        for m in msgs:
            m = dict(m)
            tags = m.pop("tags")
            msg = _make(Message, m, round=rnd)
            for t in tags:
                _make(Tag, t, message=msg)
    for x in d["responses"]:
        x = dict(x)
        pos = x.pop("block_position")
        _make(Response, x, participant=p, block=blocks.get(pos))
    for e in d["events"]:
        _make(Event, e, participant=p)
    return p
