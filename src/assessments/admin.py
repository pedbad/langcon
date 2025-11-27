# src/assessments/admin.py
from django import forms
from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.widgets import UnfoldAdminTextareaWidget

from .models import Assessment, DebateTopic


class AssessmentAdminForm(forms.ModelForm):
    """
    Custom form to make long text answer fields taller,
    while keeping Unfold's styling (borders, focus ring, etc.).
    """

    class Meta:
        model = Assessment
        fields = "__all__"
        widgets = {
            # Writing Q1 answers
            "writing_answer_draft": UnfoldAdminTextareaWidget(attrs={"rows": 10}),
            "writing_answer_final": UnfoldAdminTextareaWidget(attrs={"rows": 10}),
            # LLM Q1 answers
            "llm_question_1_answer_draft": UnfoldAdminTextareaWidget(attrs={"rows": 10}),
            "llm_question_1_answer_final": UnfoldAdminTextareaWidget(attrs={"rows": 10}),
            # LLM Q2 answers
            "llm_question_2_answer_draft": UnfoldAdminTextareaWidget(attrs={"rows": 10}),
            "llm_question_2_answer_final": UnfoldAdminTextareaWidget(attrs={"rows": 10}),
            # Listening answers
            "listening_answer_draft": UnfoldAdminTextareaWidget(attrs={"rows": 10}),
            "listening_answer_final": UnfoldAdminTextareaWidget(attrs={"rows": 10}),
        }


@admin.register(Assessment)
class AssessmentAdmin(ModelAdmin):
    """
    Custom admin for Assessment:
    - Shows writing, both LLM follow-up question blocks, and listening.
    - Provides compact previews in list view for readability.
    - Uses a custom form so long-text fields are taller, but still styled by Unfold.
    """

    form = AssessmentAdminForm

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
        # Listening block
        "listening_q1_preview",
        "listening_answer_draft_preview",
        "listening_answer_final_preview",
        "listening_submitted_at",  # Listening submitted at (helper → model field)
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
        "listening_q1_prompt",
        "listening_answer_submitted_at",
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
                "classes": ("wide",),
                "fields": (
                    "writing_q1_prompt",
                    "writing_answer_draft",
                    "writing_answer_final",
                    "writing_submitted_at",
                ),
            },
        ),
        (
            "LLM Q1 – Question & answer",
            {
                "classes": ("wide",),
                "fields": (
                    "llm_question_1",
                    "llm_question_1_answer_draft",
                    "llm_question_1_answer_final",
                    "llm_question_1_answer_submitted_at",
                ),
                "description": (
                    "First follow-up question generated from the student's initial statement, "
                    "with their draft and final answer."
                ),
            },
        ),
        (
            "LLM Q2 – Question & answer",
            {
                "classes": ("wide",),
                "fields": (
                    "llm_question_2",
                    "llm_question_2_answer_draft",
                    "llm_question_2_answer_final",
                    "llm_question_2_answer_submitted_at",
                ),
                "description": (
                    "Second follow-up question generated from the student's initial statement, "
                    "with their draft and final answer."
                ),
            },
        ),
        (
            "Listening comprehension",
            {
                "classes": ("wide",),
                "fields": (
                    "listening_q1_prompt",
                    "listening_answer_draft",
                    "listening_answer_final",
                    "listening_answer_submitted_at",
                ),
                "description": (
                    "Listening comprehension task: default prompt and the student's "
                    "draft/final summary."
                ),
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

    # --- Listening previews ---

    def listening_q1_preview(self, obj):
        text = obj.listening_q1_prompt or ""
        return (text[:80] + "…") if len(text) > 80 else text

    listening_q1_preview.short_description = "Listening – Prompt"
    listening_q1_preview.admin_order_field = "listening_q1_prompt"

    def listening_answer_draft_preview(self, obj):
        text = obj.listening_answer_draft or ""
        return (text[:80] + "…") if len(text) > 80 else text

    listening_answer_draft_preview.short_description = "Listening – Draft summary"
    listening_answer_draft_preview.admin_order_field = "listening_answer_draft"

    def listening_answer_final_preview(self, obj):
        text = obj.listening_answer_final or ""
        return (text[:80] + "…") if len(text) > 80 else text

    listening_answer_final_preview.short_description = "Listening – Final summary"
    listening_answer_final_preview.admin_order_field = "listening_answer_final"

    def listening_submitted_at(self, obj):
        return obj.listening_answer_submitted_at

    listening_submitted_at.short_description = "Listening – Submitted at"
    listening_submitted_at.admin_order_field = "listening_answer_submitted_at"


class DebateTopicAdminForm(forms.ModelForm):
    """
    Custom form for DebateTopic:
    - Uses Unfold's textarea widget so borders / focus / width look consistent.
    - Only tweaks textarea height via `rows`.
    """

    class Meta:
        model = DebateTopic
        fields = "__all__"
        widgets = {
            "question": UnfoldAdminTextareaWidget(attrs={"rows": 3}),
            "position_a_body": UnfoldAdminTextareaWidget(attrs={"rows": 10}),
            "position_b_body": UnfoldAdminTextareaWidget(attrs={"rows": 10}),
            # Titles use the default Unfold text input widget,
            # so we don't override them here.
        }


@admin.register(DebateTopic)
class DebateTopicAdmin(ModelAdmin):
    form = DebateTopicAdminForm

    list_display = (
        "topic_number",
        "question_short",
        "is_active",
    )
    list_display_links = ("question_short",)
    list_filter = ("is_active",)
    search_fields = (
        "question",
        "position_a_title",
        "position_b_title",
        "slug",
    )
    prepopulated_fields = {
        "slug": ("question",),
    }
    fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "topic_number",
                    "slug",
                    "question",
                    "position_a_title",
                    "position_a_body",
                    "position_b_title",
                    "position_b_body",
                    "is_active",
                ),
            },
        ),
    )

    def question_short(self, obj):
        return obj.question[:80]

    question_short.short_description = "Question"
