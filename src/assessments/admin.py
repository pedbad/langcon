# src/assessments/admin.py
from django.contrib import admin

from .models import Assessment


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    """
    Custom admin for Assessment:
    - Shows writing and both LLM follow-up question blocks.
    - Provides compact previews in list view for readability.
    """

    # Columns in the list view (ordered to match logical grouping)
    list_display = (
        "user",
        # Writing block
        "writing_q1_preview",
        "answer_draft_preview",
        "answer_final_preview",
        "writing_submitted_at",  # Writing submitted at (model field)
        # LLM Q1 block
        "llm_q1_preview",
        "llm_q1_answer_draft_preview",
        "llm_q1_answer_final_preview",
        "llm_q1_submitted_at",  # LLM Q1 submitted at (helper → model field)
        # LLM Q2 block
        "llm_q2_preview",
        "llm_q2_answer_draft_preview",
        "llm_q2_answer_final_preview",
        "llm_q2_submitted_at",  # LLM Q2 submitted at (helper → model field)
        # Metadata
        "created_at",
    )
    list_display_links = ("user", "writing_q1_preview")
    search_fields = ("user__email", "user__username")
    list_filter = ("writing_submitted_at", "created_at")

    # Read-only metadata / generated bits
    readonly_fields = (
        "writing_q1_prompt",
        "writing_submitted_at",
        "llm_question_1_answer_submitted_at",
        "llm_question_2_answer_submitted_at",
        "created_at",
        "updated_at",
        "llm_question_1",
        "llm_question_2",
    )

    # Fieldsets organize the edit form
    fieldsets = (
        (None, {"fields": ("user",)}),
        (
            "Writing Q1 (Initial Statement)",
            {
                "fields": (
                    "writing_q1_prompt",
                    "writing_answer_draft",
                    "writing_answer_final",
                    "writing_submitted_at",
                )
            },
        ),
        (
            "Follow-up Questions (LLM-generated)",
            {
                "fields": (
                    "llm_question_1",
                    "llm_question_2",
                ),
                "description": (
                    "These are generated automatically from the student's initial statement."
                ),
            },
        ),
        (
            "LLM Q1 – Student answer",
            {
                "fields": (
                    "llm_question_1_answer_draft",
                    "llm_question_1_answer_final",
                    "llm_question_1_answer_submitted_at",
                ),
                "description": ("Draft and final answer for the first LLM follow-up question."),
            },
        ),
        (
            "LLM Q2 – Student answer",
            {
                "fields": (
                    "llm_question_2_answer_draft",
                    "llm_question_2_answer_final",
                    "llm_question_2_answer_submitted_at",
                ),
                "description": ("Draft and final answer for the second LLM follow-up question."),
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    # --- Preview helpers for shorter admin list cells ---

    def writing_q1_preview(self, obj):
        text = obj.writing_q1_prompt or ""
        return (text[:80] + "…") if len(text) > 80 else text

    writing_q1_preview.short_description = "Writing Q1 – Prompt"
    writing_q1_preview.admin_order_field = "writing_q1_prompt"

    def answer_draft_preview(self, obj):
        text = obj.writing_answer_draft or ""
        return (text[:80] + "…") if len(text) > 80 else text

    answer_draft_preview.short_description = "Writing Q1 – Draft answer"
    answer_draft_preview.admin_order_field = "writing_answer_draft"

    def answer_final_preview(self, obj):
        text = obj.writing_answer_final or ""
        return (text[:80] + "…") if len(text) > 80 else text

    answer_final_preview.short_description = "Writing Q1 – Final answer"
    answer_final_preview.admin_order_field = "writing_answer_final"

    def llm_q1_preview(self, obj):
        text = obj.llm_question_1 or ""
        return (text[:80] + "…") if len(text) > 80 else text

    llm_q1_preview.short_description = "LLM Q1 – Question"
    llm_q1_preview.admin_order_field = "llm_question_1"

    def llm_q1_answer_draft_preview(self, obj):
        text = obj.llm_question_1_answer_draft or ""
        return (text[:80] + "…") if len(text) > 80 else text

    llm_q1_answer_draft_preview.short_description = "LLM Q1 – Draft answer"
    llm_q1_answer_draft_preview.admin_order_field = "llm_question_1_answer_draft"

    def llm_q1_answer_final_preview(self, obj):
        text = obj.llm_question_1_answer_final or ""
        return (text[:80] + "…") if len(text) > 80 else text

    llm_q1_answer_final_preview.short_description = "LLM Q1 – Final answer"
    llm_q1_answer_final_preview.admin_order_field = "llm_question_1_answer_final"

    def llm_q1_submitted_at(self, obj):
        return obj.llm_question_1_answer_submitted_at

    llm_q1_submitted_at.short_description = "LLM Q1 – Submitted at"
    llm_q1_submitted_at.admin_order_field = "llm_question_1_answer_submitted_at"

    def llm_q2_preview(self, obj):
        text = obj.llm_question_2 or ""
        return (text[:80] + "…") if len(text) > 80 else text

    llm_q2_preview.short_description = "LLM Q2 – Question"
    llm_q2_preview.admin_order_field = "llm_question_2"

    def llm_q2_answer_draft_preview(self, obj):
        text = obj.llm_question_2_answer_draft or ""
        return (text[:80] + "…") if len(text) > 80 else text

    llm_q2_answer_draft_preview.short_description = "LLM Q2 – Draft answer"
    llm_q2_answer_draft_preview.admin_order_field = "llm_question_2_answer_draft"

    def llm_q2_answer_final_preview(self, obj):
        text = obj.llm_question_2_answer_final or ""
        return (text[:80] + "…") if len(text) > 80 else text

    llm_q2_answer_final_preview.short_description = "LLM Q2 – Final answer"
    llm_q2_answer_final_preview.admin_order_field = "llm_question_2_answer_final"

    def llm_q2_submitted_at(self, obj):
        return obj.llm_question_2_answer_submitted_at

    llm_q2_submitted_at.short_description = "LLM Q2 – Submitted at"
    llm_q2_submitted_at.admin_order_field = "llm_question_2_answer_submitted_at"
