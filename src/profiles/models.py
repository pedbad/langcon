# src/profiles/models.py
from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import CheckConstraint, Q
from django.utils.translation import gettext_lazy as _


class Profile(models.Model):
    """
    Stores additional student-specific details that extend the CustomUser model.
    A profile is automatically created for each student upon registration
    (if PROFILES_AUTO_CREATE = True).
    """

    # ────────────────────────────────────────────────────────────────
    # User association
    # ────────────────────────────────────────────────────────────────
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        help_text="Linked user account for this profile.",
    )

    # ────────────────────────────────────────────────────────────────
    # Contact information
    # ────────────────────────────────────────────────────────────────
    phone = models.CharField(
        max_length=20,
        blank=False,
        validators=[
            RegexValidator(
                regex=r"^\+?[0-9\s\-]{7,20}$",
                message="Enter a valid phone number (digits, spaces, +, -).",
            )
        ],
        help_text="Student contact number (required).",
    )

    # ────────────────────────────────────────────────────────────────
    # Subject Area
    # ────────────────────────────────────────────────────────────────
    SUBJECT_AREA_CHOICES = [
        ("arts_humanities", "Arts and Humanities"),
        ("computing", "Computing"),
        ("education", "Education"),
        ("engineering", "Engineering"),
        ("environment", "Environment"),
        ("medicine", "Medicine"),
        ("physical_sciences", "Physical Sciences"),
        ("social_sciences", "Social Sciences"),
        ("other", "Other"),
    ]

    subject_area = models.CharField(
        max_length=50,
        choices=SUBJECT_AREA_CHOICES,
        default="other",
        help_text="Student's main subject area (required).",
    )

    # ────────────────────────────────────────────────────────────────
    # UK Student Visa Requirement
    # ────────────────────────────────────────────────────────────────
    requires_uk_student_visa = models.BooleanField(
        null=False,
        default=True,
        help_text="Whether the student requires a visa to study in the UK.",
    )

    # ────────────────────────────────────────────────────────────────
    # English Exam (past five years)
    # ────────────────────────────────────────────────────────────────
    has_recent_english_exam = models.BooleanField(
        null=False,
        default=False,
        help_text="Has the student taken an English language exam in the last five years?",
    )

    # Dropdown appears when student selects "Yes".
    TEST_CHOICES = (
        ("", "Select exam..."),  # placeholder for form
        ("ielts", "IELTS"),
        ("toefl", "TOEFL"),
        ("c1", "Cambridge C1 Advanced"),
        ("c2", "Cambridge C2 Proficiency"),
    )
    exam_type = models.CharField(
        max_length=20,
        choices=TEST_CHOICES,
        blank=True,  # optional in DB; conditional in validation
        help_text="The type of English language exam taken.",
    )

    # stored date for the taken exam (optional in DB; conditional in validation)
    exam_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of the most recent English exam (required if an exam was taken).",
    )

    # ────────────────────────────────────────────────────────────────
    # 🔒 Locking and auditing
    # ────────────────────────────────────────────────────────────────
    is_locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Profile"
        verbose_name_plural = "Profiles"
        # Optional DB guardrail (MySQL 8+ enforces CHECK):
        constraints = [
            CheckConstraint(
                name="exam_requires_type_and_date",
                condition=(  # ← Changed from 'check' to 'condition'
                    Q(has_recent_english_exam=False)
                    | (~Q(exam_type="") & Q(exam_date__isnull=False))
                ),
            ),
        ]

    def __str__(self) -> str:
        user_ident = getattr(self.user, "email", str(self.user))
        return f"Profile<{user_ident}>"

    # ────────────────────────────────────────────────────────────────
    # Validation + normalization (conditional-required)
    # ────────────────────────────────────────────────────────────────
    def clean(self):
        super().clean()
        if self.has_recent_english_exam:
            errors = {}
            if not self.exam_type:
                errors["exam_type"] = _("Please select the exam taken.")
            if self.exam_date is None:
                errors["exam_date"] = _("Please provide the exam date.")
            else:
                # Optional server-side window check
                today = date.today()
                min_date = date(today.year - 5, today.month, today.day)
                if not (min_date <= self.exam_date <= today):
                    errors["exam_date"] = _("Exam date must be within the last five years.")
            if errors:
                raise ValidationError(errors)

    def save(self, *args, **kwargs):
        # Normalize dependent fields when the switch is False
        if not self.has_recent_english_exam:
            self.exam_type = ""
            self.exam_date = None
        super().save(*args, **kwargs)

    # ────────────────────────────────────────────────────────────────
    # Completion logic
    # ────────────────────────────────────────────────────────────────
    def is_complete(self) -> bool:
        base_ok = bool(self.phone and self.subject_area and not self.is_locked)
        if not base_ok:
            return False
        if not self.has_recent_english_exam:
            return True
        return bool(self.exam_type and self.exam_date)
