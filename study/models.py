from django.db import models

from .content import COLOURS, DESIGNS


class Participant(models.Model):
    pid = models.CharField(max_length=10, unique=True)  # e.g. P07 (the sequence number, not arrival order)
    sequence_no = models.PositiveSmallIntegerField(unique=True)
    is_pilot = models.BooleanField(default=False)
    station = models.CharField(max_length=4, default="A")  # which laptop ran the session (STATION in .env)
    config_hash = models.CharField(max_length=16, blank=True)  # fingerprint of prompts, content and settings
    step = models.PositiveSmallIntegerField(default=0)  # index into flow.steps()
    created = models.DateTimeField(auto_now_add=True)
    finished = models.DateTimeField(null=True, blank=True)
    needs_attention = models.BooleanField(default=False)  # e.g. stress >= 9 or LLM failure
    attention_note = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)  # researcher's interview notes

    class Meta:
        ordering = ["created"]

    def __str__(self):
        return self.pid


class Block(models.Model):
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name="blocks")
    position = models.PositiveSmallIntegerField()  # 0, 1, 2
    design = models.CharField(max_length=1, choices=[(k, v["name"]) for k, v in DESIGNS.items()])
    scenario = models.CharField(max_length=3)
    current_level = models.PositiveSmallIntegerField(default=1)  # adaptive state

    class Meta:
        ordering = ["participant", "position"]
        unique_together = [("participant", "position")]

    @property
    def colour(self):
        return COLOURS[self.position]

    def __str__(self):
        return f"{self.participant.pid} block {self.position + 1} ({self.design}/{self.scenario})"


class Round(models.Model):
    """A practice round, the probe, or the warm-up."""
    KINDS = [("practice", "practice"), ("probe", "probe"), ("warmup", "warmup")]
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name="rounds")
    block = models.ForeignKey(Block, on_delete=models.CASCADE, null=True, blank=True, related_name="rounds")
    kind = models.CharField(max_length=10, choices=KINDS)
    index = models.PositiveSmallIntegerField(default=0)  # 0-2 for practice
    level = models.PositiveSmallIntegerField(null=True, blank=True)
    started = models.DateTimeField(auto_now_add=True)
    ended = models.DateTimeField(null=True, blank=True)
    end_reason = models.CharField(max_length=20, blank=True)  # agreed / max_messages / timeout / probe_done / skipped
    stress = models.PositiveSmallIntegerField(null=True, blank=True)
    judge_d = models.PositiveSmallIntegerField(null=True, blank=True)
    judge_e = models.PositiveSmallIntegerField(null=True, blank=True)
    judge_s = models.PositiveSmallIntegerField(null=True, blank=True)
    judge_c = models.PositiveSmallIntegerField(null=True, blank=True)
    judge_total = models.PositiveSmallIntegerField(null=True, blank=True)
    judge_raw = models.TextField(blank=True)
    decision = models.CharField(max_length=10, blank=True)  # raise / keep / lower
    next_level = models.PositiveSmallIntegerField(null=True, blank=True)
    reflection = models.CharField(max_length=300, blank=True)  # optional "what will you try next round?" note

    class Meta:
        ordering = ["participant", "started"]

    @property
    def is_open(self):
        return self.ended is None


class Message(models.Model):
    round = models.ForeignKey(Round, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=10)  # learner / drlee
    text = models.TextField()
    raw_text = models.TextField(blank=True)  # model output before removing [AGREED]
    created = models.DateTimeField(auto_now_add=True)
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    model = models.CharField(max_length=60, blank=True)
    level = models.PositiveSmallIntegerField(null=True, blank=True)
    probe_line = models.PositiveSmallIntegerField(null=True, blank=True)  # 1-3: the fixed line this reply answers

    class Meta:
        ordering = ["created", "id"]


class Response(models.Model):
    """Questionnaire answers (one row per form submission)."""
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name="responses")
    block = models.ForeignKey(Block, on_delete=models.CASCADE, null=True, blank=True)
    kind = models.CharField(max_length=20)  # pre / block / human / final
    data = models.JSONField()
    created = models.DateTimeField(auto_now_add=True)


class Tag(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="tags")
    tag = models.CharField(max_length=20)
    reason = models.CharField(max_length=300, blank=True)
    created = models.DateTimeField(auto_now_add=True)


class Event(models.Model):
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, null=True, blank=True, related_name="events")
    kind = models.CharField(max_length=30)
    detail = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]
