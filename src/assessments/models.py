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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # LLM follow-up questions (populated right after the student submits)
    llm_question_1 = models.TextField(blank=True)
    llm_question_2 = models.TextField(blank=True)

    def __str__(self):
        return f"Assessment for {self.user.email}"
