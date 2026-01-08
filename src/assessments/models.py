# src/assessments/models.py
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


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

    # Reading comprehension fields
    reading_debate = models.ForeignKey(
        "DebateTopic",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="assessments",
        help_text=("Debate topic shown to the student for the Reading Comprehension step."),
    )
    reading_answer_draft = models.TextField(
        blank=True,
        help_text="Student's draft answer for the reading comprehension task.",
    )
    reading_answer_final = models.TextField(
        blank=True,
        help_text="Student's final answer for the reading comprehension task.",
    )
    reading_answer_submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the reading final answer was submitted.",
    )

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

    # ─────────────────────────────────────────
    # Simple flags
    # ─────────────────────────────────────────
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

    @property
    def has_reading_answer(self) -> bool:
        """
        Convenience flag for the Reading Comprehension step.
        """
        return bool(self.reading_answer_final)

    # ─────────────────────────────────────────
    # Legacy completeness (pre-reading)
    # ─────────────────────────────────────────
    def is_complete(self) -> bool:
        """
        “Complete” = writing + both follow-up answers + listening submitted.

        This preserves the original semantics used elsewhere in the codebase.
        The Reading step is handled separately via `is_fully_complete`.
        """
        return (
            self.has_writing
            and self.has_llm_q1_answer
            and self.has_llm_q2_answer
            and self.has_listening_answer
        )

    # ─────────────────────────────────────────
    # completeness duration time
    # ─────────────────────────────────────────
    @property
    def completion_duration(self):
        """
        Wall-clock elapsed time for this assessment.

        Defined as the time difference between:
        - when the student submitted their final Writing answer
        - and when they submitted their final Reading answer.

        Returns:
            datetime.timedelta | None:
                A positive time delta if both timestamps are present,
                otherwise None (e.g. if the assessment is not yet fully complete).
        """
        if self.writing_submitted_at and self.reading_answer_submitted_at:
            return self.reading_answer_submitted_at - self.writing_submitted_at
        return None

    # ─────────────────────────────────────────
    # New: progress helpers for UI
    # ─────────────────────────────────────────
    @property
    def step_states(self):
        """
        Ordered list of main assessment steps and whether they are done.

        Used by the UI to render progress bars / steppers.
        """
        return [
            ("writing", "Writing", self.has_writing),
            ("followup1", "Follow-up Question 1", self.has_llm_q1_answer),
            ("followup2", "Follow-up Question 2", self.has_llm_q2_answer),
            ("listening", "Listening", self.has_listening_answer),
            ("reading", "Reading Comprehension", self.has_reading_answer),
        ]

    @property
    def steps_completed(self) -> int:
        return sum(1 for _key, _label, done in self.step_states if done)

    @property
    def steps_total(self) -> int:
        return len(self.step_states)

    @property
    def progress_pct(self) -> int:
        if self.steps_total == 0:
            return 0
        return int(self.steps_completed * 100 / self.steps_total)

    @property
    def is_fully_complete(self) -> bool:
        """
        Stricter definition: all five steps completed, including Reading.
        """
        return self.steps_completed == self.steps_total

    @property
    def status_label(self) -> str:
        """
        Human-friendly status string for the UI.
        """
        if self.steps_completed == 0:
            return "Not started"
        if self.is_fully_complete:
            return "Assessment completed"
        return "In progress"

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


class AssessmentEvaluation(models.Model):
    class Recommendation(models.TextChoices):
        MET_CONDITION = (
            "MET_CONDITION",
            "Meets condition – no language course required",
        )
        RECOMMENDED_IN_SESSIONAL = (
            "RECOMMENDED_IN_SESSIONAL",
            "Meets condition – in-sessional support recommended",
        )
        REQUIRED_IN_SESSIONAL_SPEAKING = (
            "REQUIRED_IN_SESSIONAL_SPEAKING",
            "In-sessional support required (speaking focus)",
        )
        REQUIRED_IN_SESSIONAL = (
            "REQUIRED_IN_SESSIONAL",
            "In-sessional support required",
        )
        RECOMMENDED_PRE_SESSIONAL = (
            "RECOMMENDED_PRE_SESSIONAL",
            "Pre-sessional course recommended",
        )
        REQUIRED_PRE_SESSIONAL = (
            "REQUIRED_PRE_SESSIONAL",
            "Pre-sessional course required",
        )
        REFUSED = (
            "REFUSED",
            "Not recommended / refused",
        )

    # One evaluation per assessment
    assessment = models.OneToOneField(
        Assessment,
        on_delete=models.CASCADE,
        related_name="evaluation",
        help_text="LLM + assessor evaluation for this assessment.",
    )

    # Denormalised identifiers (snapshot at evaluation time)
    student_email = models.EmailField(
        help_text="Student email at the time of evaluation.",
    )
    student_usn = models.CharField(
        max_length=64,
        help_text="Student USN at the time of evaluation.",
    )

    # Timing
    submitted_at = models.DateTimeField(
        help_text="When the assessment was fully submitted (reading final).",
    )
    completion_duration = models.DurationField(
        help_text=("Wall-clock time from writing submission to final reading submission."),
    )

    # LLM evaluation snapshot
    llm_evaluation_text = models.TextField(
        blank=True,
        help_text="Short analytic evaluation generated by the LLM.",
    )
    llm_model_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Name of the LLM model used for this evaluation.",
    )
    llm_generated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the LLM evaluation was generated.",
    )
    llm_error = models.TextField(
        blank=True,
        help_text="Error message if the LLM evaluation failed.",
    )

    # Assessor decision
    recommendation = models.CharField(
        max_length=40,
        choices=Recommendation.choices,
        blank=True,
        help_text="Assessor's final recommendation.",
    )
    assessor_comment = models.TextField(
        blank=True,
        help_text="Optional assessor comments on the evaluation / assessment.",
    )

    # Flags for admin workflow
    exam_marked = models.BooleanField(
        default=False,
        help_text="Has this assessment been fully marked?",
    )
    phone_follow_up = models.BooleanField(
        default=False,
        help_text="Does this case require a phone follow-up?",
    )
    exam_archived = models.BooleanField(
        default=False,
        help_text="Has this evaluation been archived?",
    )

    # Who marked it, and when
    assessor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assessments_marked",
        help_text="User who last updated the recommendation/comment.",
    )
    assessor_reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the assessor last saved changes.",
    )

    # Standard timestamps for the evaluation record itself
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def record_assessor_update(self, user):
        """
        Call this whenever a teacher/admin saves recommendation/comments/flags.
        """
        self.assessor = user
        self.assessor_reviewed_at = timezone.now()

    def __str__(self) -> str:
        return f"Evaluation for {self.assessment.user.email}"
