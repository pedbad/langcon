# src/assessments/admin.py
from django.contrib import admin

from .models import Assessment


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "writing_q1_preview",
        "answer_draft_preview",
        "answer_final_preview",
        "writing_submitted_at",
        "created_at",
    )
    list_display_links = ("user", "writing_q1_preview")
    search_fields = ("user__email", "user__username")
    list_filter = ("writing_submitted_at", "created_at")

    # detail page shows the full prompt (read-only)
    readonly_fields = ("writing_q1_prompt", "writing_submitted_at", "created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("user",)}),
        (
            "Writing",
            {
                "fields": (
                    "writing_q1_prompt",  # full text visible here
                    "writing_answer_draft",
                    "writing_answer_final",
                    "writing_submitted_at",
                )
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    # --- helpers for trimmed previews in the list view ---
    def writing_q1_preview(self, obj):
        text = obj.writing_q1_prompt or ""
        return (text[:80] + "…") if len(text) > 80 else text

    writing_q1_preview.short_description = "Writing Q1 prompt"
    writing_q1_preview.admin_order_field = "writing_q1_prompt"

    def answer_draft_preview(self, obj):
        text = obj.writing_answer_draft or ""
        return (text[:80] + "…") if len(text) > 80 else text

    answer_draft_preview.short_description = "Draft answer"

    def answer_final_preview(self, obj):
        text = obj.writing_answer_final or ""
        return (text[:80] + "…") if len(text) > 80 else text

    answer_final_preview.short_description = "Final answer"
