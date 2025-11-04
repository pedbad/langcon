# src/profiles/models.py
from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models


class Profile(models.Model):
    """
    Stores additional student-specific details that extend the CustomUser model.
    A profile is automatically created for each student upon registration
    (if PROFILES_AUTO_CREATE = True).
    """

    # ────────────────────────────────────────────────────────────────
    # User association
    # Each Profile belongs to exactly one CustomUser instance.
    # When the user is deleted, their Profile is also removed.
    # ────────────────────────────────────────────────────────────────
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        help_text="Linked user account for this profile.",
    )

    # ────────────────────────────────────────────────────────────────
    # Contact information
    # Required phone number used for admin or teacher communication.
    # Validation ensures only digits, spaces, '+' or '-' are accepted.
    # ────────────────────────────────────────────────────────────────
    phone = models.CharField(
        max_length=20,
        blank=False,  # 🔒 required at form and DB level
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
    # Used to group students by their academic domain.
    # This field appears as a dropdown in the student profile form.
    # ────────────────────────────────────────────────────────────────
    SUBJECT_AREA_CHOICES = [
        ("arts_humanities", "Art and Humanities"),
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
        default="other",  # Ensures existing profiles migrate cleanly
        help_text="Student's main subject area (required).",
    )

    # ────────────────────────────────────────────────────────────────
    # UK Student Visa Requirement
    # Indicates whether the student requires a visa to study in the UK.
    # This field appears as a Yes/No dropdown banner in the student profile form.
    # ────────────────────────────────────────────────────────────────
    requires_uk_student_visa = models.BooleanField(
        null=False,
        default=True,
        help_text="Whether the student requires a visa to study in the UK.",
    )

    # ────────────────────────────────────────────────────────────────
    # English Exam (past five years)
    # Records whether the student has taken an English language exam
    # in the past five years. Additional fields (exam type/scores) will
    # be collected only if this is True.
    # ────────────────────────────────────────────────────────────────
    has_recent_english_exam = models.BooleanField(
        null=False,
        default=False,
        help_text="Has the student taken an English language exam in the last five years?",
    )

    # ────────────────────────────────────────────────────────────────
    # 🔒 Locking and auditing
    # is_locked prevents further student edits once approved.
    # created_at / updated_at provide basic audit metadata.
    # ────────────────────────────────────────────────────────────────
    is_locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Profile"
        verbose_name_plural = "Profiles"

    def __str__(self) -> str:
        """Readable string representation for admin/debug."""
        user_ident = getattr(self.user, "email", str(self.user))
        return f"Profile<{user_ident}>"

    # ────────────────────────────────────────────────────────────────
    # Completion logic
    # A profile is considered complete only when all required fields
    # are filled and the profile is not locked.
    # This will expand as new required fields are added.
    # ────────────────────────────────────────────────────────────────
    def is_complete(self) -> bool:
        return bool(self.phone and self.subject_area and not self.is_locked)
