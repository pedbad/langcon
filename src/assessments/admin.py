from django.contrib import admin

from .models import Assessment


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    """
    Custom admin for Assessment:
    - Shows both writing and LLM follow-up question data.
    - Provides compact previews in list view for readability.
    """

    # Columns in the list view
    list_display = (
        "user",
        "writing_q1_preview",
        "answer_draft_preview",
        "answer_final_preview",
        "llm_q1_preview",
        "llm_q2_preview",
        "writing_submitted_at",
        "created_at",
    )
    list_display_links = ("user", "writing_q1_preview")
    search_fields = ("user__email", "user__username")
    list_filter = ("writing_submitted_at", "created_at")

    # Read-only metadata
    readonly_fields = (
        "writing_q1_prompt",
        "writing_submitted_at",
        "created_at",
        "updated_at",
        "llm_question_1",
        "llm_question_2",
    )

    # Fieldsets organize the edit form
    fieldsets = (
        (None, {"fields": ("user",)}),
        (
            "Writing Section",
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
            "LLM Follow-Up Questions",
            {
                "fields": (
                    "llm_question_1",
                    "llm_question_2",
                ),
                "description": (
                    "These are auto-generated after submission using the student's final answer."
                ),
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    # --- Preview helpers for shorter admin list cells ---
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

    def llm_q1_preview(self, obj):
        text = obj.llm_question_1 or ""
        return (text[:80] + "…") if len(text) > 80 else text

    llm_q1_preview.short_description = "LLM Q1"

    def llm_q2_preview(self, obj):
        text = obj.llm_question_2 or ""
        return (text[:80] + "…") if len(text) > 80 else text

    llm_q2_preview.short_description = "LLM Q2"
