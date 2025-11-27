# src/assessments/models.py
import uuid

from django.conf import settings
from django.db import models


class Assessment(models.Model):
    """
    One assessment per student — created once their profile is complete.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assessment",
    )

    # Writing section fields
    writing_q1_prompt = models.TextField(
        default=(
            "Explain as if writing for an educated but non-expert audience the nature of your "
            "postgraduate research if applying for a PhD or the reasons for your choice of "
            "taught postgraduate or (undergraduate) programme."
        ),
        editable=False,
    )
    writing_answer_draft = models.TextField(blank=True)
    writing_answer_final = models.TextField(blank=True)
    writing_submitted_at = models.DateTimeField(null=True, blank=True)

    # Listening comprehension fields
    listening_q1_prompt = models.TextField(
        default=(
            "You are going to listen to a lecture related to your subject area. "
            "The lecture is approximately ten minutes long. Write a short summary of the lecture."
        ),
        editable=False,
    )
    listening_answer_draft = models.TextField(blank=True)
    listening_answer_final = models.TextField(blank=True)
    listening_answer_submitted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # LLM follow-up questions (populated right after the student submits)
    llm_question_1 = models.TextField(blank=True)
    llm_question_2 = models.TextField(blank=True)

    # Follow-up Question 1 answers
    llm_question_1_answer_draft = models.TextField(blank=True)
    llm_question_1_answer_final = models.TextField(blank=True)
    llm_question_1_answer_submitted_at = models.DateTimeField(null=True, blank=True)

    # Follow-up Question 2 answers
    llm_question_2_answer_draft = models.TextField(blank=True)
    llm_question_2_answer_final = models.TextField(blank=True)
    llm_question_2_answer_submitted_at = models.DateTimeField(null=True, blank=True)

    @property
    def has_writing(self) -> bool:
        return bool(self.writing_answer_final)

    @property
    def has_llm_q1(self) -> bool:
        return bool(self.llm_question_1)

    @property
    def has_llm_q1_answer(self) -> bool:
        return bool(self.llm_question_1_answer_final)

    @property
    def has_llm_q2(self) -> bool:
        return bool(self.llm_question_2)

    @property
    def has_llm_q2_answer(self) -> bool:
        return bool(self.llm_question_2_answer_final)

    @property
    def has_listening_prompt(self) -> bool:
        return bool(self.listening_q1_prompt)

    @property
    def has_listening_answer(self) -> bool:
        return bool(self.listening_answer_final)

    def is_complete(self) -> bool:
        """
        “Complete” = writing + both follow-up answers + listening submitted.
        """
        return (
            self.has_writing
            and self.has_llm_q1_answer
            and self.has_llm_q2_answer
            and self.has_listening_answer
        )

    def __str__(self):
        return f"Assessment for {self.user.email}"


class DebateTopic(models.Model):
    """Reading comprehension debate topic (Position A / Position B)."""

    topic_number = models.PositiveSmallIntegerField(
        unique=True,
        help_text="Short numeric identifier, e.g. 1–10.",
    )
    slug = models.SlugField(
        max_length=50,
        unique=True,
        help_text="Short label, e.g. 'ubi', 'ai-decisions'.",
    )

    # Main question shown as the topic heading
    question = models.TextField(
        help_text="Full debate question shown to students.",
    )

    # Position A
    position_a_title = models.CharField(
        max_length=255,
        help_text="Short heading for Position A.",
    )
    position_a_body = models.TextField(
        help_text="Full text for Position A.",
    )

    # Position B
    position_b_title = models.CharField(
        max_length=255,
        help_text="Short heading for Position B.",
    )
    position_b_body = models.TextField(
        help_text="Full text for Position B.",
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Only active topics are used for new assessments.",
    )

    class Meta:
        ordering = ("topic_number",)
        verbose_name = "Debate topic"
        verbose_name_plural = "Debate topics"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"Topic {self.topic_number}: {self.question[:80]}"
