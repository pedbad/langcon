# src/profiles/models.py
from datetime import date

# ────────────────────────────────────────────────────────────────
# Score helpers (keep math consistent server-side)
# ────────────────────────────────────────────────────────────────
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import CheckConstraint, Q
from django.utils.translation import gettext_lazy as _


def _to_dec(x):
    """Coerce to Decimal or return None."""
    if x is None:
        return None
    if isinstance(x, Decimal):
        return x
    try:
        return Decimal(str(x))
    except Exception:
        return None


def _clamp(x: Decimal, lo: Decimal, hi: Decimal) -> Decimal:
    return max(lo, min(hi, x))


def _nearest_half(x: Decimal) -> Decimal:
    """Round to nearest 0.5 (e.g., 6.24→6.0, 6.26→6.5, 6.75→7.0)."""
    return (x * 2).to_integral_value(rounding=ROUND_HALF_UP) / Decimal("2")


def _is_step(x: Decimal, step: Decimal) -> bool:
    """True if x is a multiple of step (within Decimal arithmetic)."""
    # Avoid modulo on Decimals with fractional steps by scaling
    q = (x / step).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return (q * step) == x


# Rules for each exam type
EXAM_RULES = {
    "ielts": {
        "sub_min": Decimal("0.0"),
        "sub_max": Decimal("9.0"),
        "sub_step": Decimal("0.5"),
        "overall_min": Decimal("0.0"),
        "overall_max": Decimal("9.0"),
        "overall_kind": "avg_half",  # average of subs, rounded to nearest 0.5
    },
    "toefl": {
        "sub_min": Decimal("0"),
        "sub_max": Decimal("30"),
        "sub_step": Decimal("1"),
        "overall_min": Decimal("0"),
        "overall_max": Decimal("120"),
        "overall_kind": "sum_int",  # sum of subs
    },
    "c1": {
        "sub_min": Decimal("160"),
        "sub_max": Decimal("210"),
        "sub_step": Decimal("1"),
        "overall_min": Decimal("160"),
        "overall_max": Decimal("210"),
        "overall_kind": "avg_int",  # average of subs, rounded to nearest int
    },
    "c2": {
        "sub_min": Decimal("200"),
        "sub_max": Decimal("230"),
        "sub_step": Decimal("1"),
        "overall_min": Decimal("200"),
        "overall_max": Decimal("230"),
        "overall_kind": "avg_int",
    },
}


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

    exam_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of the most recent English exam (required if an exam was taken).",
    )

    # ────────────────────────────────────────────────────────────────
    # NEW: Generic exam scores (conditionally validated by exam_type)
    # We use Decimal so IELTS 0.5 steps are representable and others (int ranges)
    # still fit.  max_digits=5, decimal_places=1 comfortably stores e.g. 230.0.
    # ────────────────────────────────────────────────────────────────
    reading_score = models.DecimalField(
        max_digits=5, decimal_places=1, null=True, blank=True, help_text="Reading score."
    )
    listening_score = models.DecimalField(
        max_digits=5, decimal_places=1, null=True, blank=True, help_text="Listening score."
    )
    writing_score = models.DecimalField(
        max_digits=5, decimal_places=1, null=True, blank=True, help_text="Writing score."
    )
    speaking_score = models.DecimalField(
        max_digits=5, decimal_places=1, null=True, blank=True, help_text="Speaking score."
    )
    overall_score = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="Overall score (auto-calculated by default).",
    )

    # Track whether the student explicitly edited the overall score.
    # Later we will compute overall when this is False; otherwise we only range-check.
    overall_manual_override = models.BooleanField(default=False)

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
                condition=(
                    Q(has_recent_english_exam=False)
                    | (~Q(exam_type="") & Q(exam_date__isnull=False))
                ),
            ),
        ]

    def __str__(self) -> str:
        user_ident = getattr(self.user, "email", str(self.user))
        return f"Profile<{user_ident}>"

    # ────────────────────────────────────────────────────────────────
    # Helpers
    # ────────────────────────────────────────────────────────────────
    def _clear_exam_scores(self):
        """Reset all score fields and the manual override flag."""
        self.reading_score = None
        self.listening_score = None
        self.writing_score = None
        self.speaking_score = None
        self.overall_score = None
        self.overall_manual_override = False

    def _compute_overall_from_subs(self, rules: dict) -> Decimal:
        """
        Compute overall from sub-scores using the selected exam rules.
        - IELTS: average → nearest 0.5 (clamped to 0–9)
        - TOEFL: sum (clamped to 0–120)
        - C1/C2: average → nearest int (clamped to band range)
        """
        subs = [
            _to_dec(self.reading_score),
            _to_dec(self.listening_score),
            _to_dec(self.writing_score),
            _to_dec(self.speaking_score),
        ]
        # All subs are assumed present/validated before calling
        if rules["overall_kind"] == "sum_int":
            total = sum(subs, Decimal("0"))
            return _clamp(total, rules["overall_min"], rules["overall_max"])
        elif rules["overall_kind"] == "avg_half":
            avg = sum(subs, Decimal("0")) / Decimal("4")
            rounded = _nearest_half(avg)
            return _clamp(rounded, rules["overall_min"], rules["overall_max"])
        elif rules["overall_kind"] == "avg_int":
            avg = sum(subs, Decimal("0")) / Decimal("4")
            # round to nearest integer
            rounded = avg.to_integral_value(rounding=ROUND_HALF_UP)
            return _clamp(rounded, rules["overall_min"], rules["overall_max"])
        # Fallback (should not happen)
        return _to_dec(self.overall_score)

    # ────────────────────────────────────────────────────────────────
    # Validation + normalization
    # ────────────────────────────────────────────────────────────────
    def clean(self):
        super().clean()

        if self.has_recent_english_exam:
            errors = {}

            # ── Basic requirements (type + date window) ─────────────────
            if not self.exam_type:
                errors["exam_type"] = _("Please select the exam taken.")

            date_ok = False
            if self.exam_date is None:
                errors["exam_date"] = _("Please provide the exam date.")
            else:
                today = date.today()
                min_date = date(today.year - 5, today.month, today.day)
                if not (min_date <= self.exam_date <= today):
                    errors["exam_date"] = _("Exam date must be within the last five years.")
                else:
                    date_ok = True  # ← only true when date is present and within window

            # ── Only proceed to score validation when type & date are OK ─
            et = (self.exam_type or "").lower()
            if et not in EXAM_RULES:
                # Unknown/empty type → don’t try to validate scores yet
                if self.exam_type:  # user supplied a non-empty bad value
                    errors["exam_type"] = _("Unknown exam type. Please choose one from the list.")
            elif date_ok:
                # Subscore presence & range/step checks
                rules = EXAM_RULES[et]
                sub_fields = ["reading_score", "listening_score", "writing_score", "speaking_score"]
                for f in sub_fields:
                    v = _to_dec(getattr(self, f))
                    if v is None:
                        errors[f] = _("Please enter a value.")
                        continue
                    if not (rules["sub_min"] <= v <= rules["sub_max"]):
                        errors[f] = _(
                            f"Value must be between {rules['sub_min']} and {rules['sub_max']}."
                        )
                        continue
                    if not _is_step(v, rules["sub_step"]):
                        step_msg = (
                            "in 0.5 steps (e.g., 6.5)"
                            if rules["sub_step"] == Decimal("0.5")
                            else "in whole numbers"
                        )
                        errors[f] = _("Please enter a valid value ") + step_msg + "."

                # Only compute/check overall if all subs are valid
                if not any(k in errors for k in sub_fields):
                    if self.overall_manual_override:
                        ov = _to_dec(self.overall_score)
                        if ov is None:
                            errors["overall_score"] = _(
                                "Please enter the overall score or turn off manual override."
                            )
                        else:
                            if not (rules["overall_min"] <= ov <= rules["overall_max"]):
                                errors["overall_score"] = _(
                                    "Overall must be between %(lo)s and %(hi)s."
                                ) % {
                                    "lo": rules["overall_min"],
                                    "hi": rules["overall_max"],
                                }
                            if et == "ielts" and not _is_step(ov, Decimal("0.5")):
                                errors["overall_score"] = _(
                                    "Overall must be in 0.5 steps (e.g., 6.5)."
                                )
                    else:
                        self.overall_score = self._compute_overall_from_subs(rules)

            if errors:
                raise ValidationError(errors)

    def save(self, *args, **kwargs):
        # Normalize dependent fields when the switch is False
        if not self.has_recent_english_exam:
            self.exam_type = ""
            self.exam_date = None
            self._clear_exam_scores()
        else:
            # If exam type is changed to an unknown or empty, wipe scores
            et = (self.exam_type or "").lower()
            if et not in EXAM_RULES:
                self._clear_exam_scores()
        super().save(*args, **kwargs)

    # ────────────────────────────────────────────────────────────────
    # Completion logic
    # ────────────────────────────────────────────────────────────────
    def is_complete(self) -> bool:
        """
        Profile is complete when:
          - phone, subject_area present
          - not locked
          - if no recent exam → complete
          - if recent exam → exam_type & date + 4 subscores + overall present
        """
        base_ok = bool(self.phone and self.subject_area and not self.is_locked)
        if not base_ok:
            return False
        if not self.has_recent_english_exam:
            return True

        all_scores_present = all(
            getattr(self, f) is not None
            for f in (
                "reading_score",
                "listening_score",
                "writing_score",
                "speaking_score",
                "overall_score",
            )
        )
        return bool(self.exam_type and self.exam_date and all_scores_present)
