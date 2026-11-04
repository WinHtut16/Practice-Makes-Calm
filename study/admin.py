from django.contrib import admin

from .models import Block, Event, Message, Participant, Response, Round, Tag


class BlockInline(admin.TabularInline):
    model = Block
    extra = 0


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ("pid", "sequence_no", "is_pilot", "step", "created", "finished", "needs_attention")
    list_filter = ("is_pilot",)
    inlines = [BlockInline]


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    fields = ("role", "text", "level", "probe_line", "latency_ms")
    readonly_fields = fields


@admin.register(Round)
class RoundAdmin(admin.ModelAdmin):
    list_display = ("participant", "kind", "block", "index", "level", "end_reason", "stress", "judge_total", "decision", "next_level")
    list_filter = ("kind", "participant")
    inlines = [MessageInline]


admin.site.register(Response, list_display=("participant", "kind", "block", "created"))
admin.site.register(Tag, list_display=("message", "tag", "reason"))
admin.site.register(Event, list_display=("participant", "kind", "detail", "created"))
