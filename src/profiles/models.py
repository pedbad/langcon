# src/profiles/models.py
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import CheckConstraint, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


# ────────────────────────────────────────────────────────────────
# Decimal helpers (keep math consistent server-side)
# ────────────────────────────────────────────────────────────────
def _to_dec(x):
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
    """True if x is a multiple of step (robust with Decimals)."""
    q = (x / step).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return (q * step) == x


# ────────────────────────────────────────────────────────────────
# Rules for each exam type
# ────────────────────────────────────────────────────────────────
EXAM_RULES = {
    "ielts": {
        "sub_min": Decimal("0.0"),
        "sub_max": Decimal("9.0"),
        "sub_step": Decimal("0.5"),
        "overall_min": Decimal("0.0"),
        "overall_max": Decimal("9.0"),
        "overall_kind": "avg_half",  # average of subs → nearest 0.5
    },
    "toefl_120": {
        # Old TOEFL scheme: 0–120 total (4 × 0–30)
        "sub_min": Decimal("0"),
        "sub_max": Decimal("30"),
        "sub_step": Decimal("1"),
        "overall_min": Decimal("0"),
        "overall_max": Decimal("120"),
        "overall_kind": "sum_int",  # sum of subs
    },
    "toefl_6": {
        # New TOEFL scheme: 0–6 per skill in 0.5 steps
        "sub_min": Decimal("0.0"),
        "sub_max": Decimal("6.0"),
        "sub_step": Decimal("0.5"),
        "overall_min": Decimal("0.0"),
        "overall_max": Decimal("6.0"),
        "overall_kind": "avg_half",  # like IELTS: average → nearest 0.5
    },
    "c1": {
        "sub_min": Decimal("160"),
        "sub_max": Decimal("210"),
        "sub_step": Decimal("1"),
        "overall_min": Decimal("160"),
        "overall_max": Decimal("210"),
        "overall_kind": "avg_int",  # average of subs → nearest int
    },
    "c2": {
        "sub_min": Decimal("180"),
        "sub_max": Decimal("230"),
        "sub_step": Decimal("1"),
        "overall_min": Decimal("180"),
        "overall_max": Decimal("230"),
        "overall_kind": "avg_int",
    },
}

# Backwards-compatibility: support old "toefl" rows transparently
EXAM_RULES["toefl"] = EXAM_RULES["toefl_120"]


class Profile(models.Model):
    """
    Student profile extending the CustomUser model.
    """

    # ── User association ───────────────────────────────────────────
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        help_text="Linked user account for this profile.",
    )

    # ── Student number (USN / CRSid) ───────────────────────────────
    student_number = models.CharField(
        max_length=20,
        unique=True,
        help_text="Unique Student Number (USN)",
    )

    # ── Contact ───────────────────────────────────────────────────
    phone = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r"^\+?[0-9\s\-]{7,20}$",
                message="Enter a valid phone number (digits, spaces, +, -).",
            )
        ],
        help_text="Student contact number (required).",
    )

    # ── Subject area ───────────────────────────────────────────────
    SUBJECT_AREA_CHOICES = [
        ("arts_humanities", "Arts and Humanities"),
        ("business_management", "Business and Management"),
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
        default="",
        help_text="Student's main subject area (required).",
    )

    # ── Visa ───────────────────────────────────────────────────────
    requires_uk_student_visa = models.BooleanField(
        default=True,
        help_text="Whether the student requires a visa to study in the UK.",
    )

    # ── English Exam (past five years) ─────────────────────────────
    has_recent_english_exam = models.BooleanField(
        default=False,
        help_text="Has the student taken an English language exam in the last five years?",
    )

    TEST_CHOICES = (
        ("", "Select your exam…"),  # placeholder
        ("ielts", "IELTS (0–9, half points)"),
        ("toefl_120", "TOEFL (0–120)"),
        ("toefl_6", "TOEFL (0–6, half points)"),
        ("c1", "Cambridge C1 Advanced (160–210)"),
        ("c2", "Cambridge C2 Proficiency (180–230)"),
    )

    exam_type = models.CharField(
        max_length=20,
        choices=TEST_CHOICES,
        blank=True,  # conditional-required via clean()
        help_text="The type of English language exam taken.",
    )

    exam_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of the most recent English exam (required if an exam was taken).",
    )

    # ── Cambridge grade (for C1/C2) ────────────────────────────────
    CAMBRIDGE_GRADES = (("a", "A"), ("b", "B"), ("c", "C"))
    cambridge_grade = models.CharField(
        max_length=1,
        choices=CAMBRIDGE_GRADES,
        blank=True,
        null=True,
        help_text="Grade for Cambridge exams (A/B/C). Only for C1/C2.",
    )

    # Cambridge “Use of English” score (only for C1/C2)
    cambridge_use_of_english = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        blank=True,
        null=True,
        help_text="Cambridge Use of English score (only for C1/C2).",
    )

    # ── Scores ─────────────────────────────────────────────────────
    reading_score = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    listening_score = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    writing_score = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    speaking_score = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    overall_score = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    overall_manual_override = models.BooleanField(default=False)

    # ── Locking + timestamps ───────────────────────────────────────
    is_locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ── Honour code / academic integrity confirmation ──────────────
    academic_integrity_confirmed = models.BooleanField(
        default=False,
        help_text=(
            "Student has confirmed the work will be their own unaided effort, "
            "completed without the use of AI or large language models (LLMs)."
        ),
    )
    academic_integrity_confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
        help_text="Timestamp when the student confirmed the honour code.",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Profile"
        verbose_name_plural = "Profiles"
        constraints = [
            CheckConstraint(
                name="exam_requires_type_and_date",
                condition=Q(has_recent_english_exam=False)
                | (~Q(exam_type="") & Q(exam_date__isnull=False)),
            ),
        ]

    def __str__(self) -> str:
        user_ident = getattr(self.user, "email", str(self.user))
        return f"Profile<{user_ident}>"

    # ── Helpers ────────────────────────────────────────────────────
    def _clear_exam_scores(self):
        self.reading_score = None
        self.listening_score = None
        self.writing_score = None
        self.speaking_score = None
        self.overall_score = None
        self.overall_manual_override = False
        self.cambridge_grade = None
        self.cambridge_use_of_english = None

    def _compute_overall_from_subs(self, rules: dict) -> Decimal:
        subs = [
            _to_dec(self.reading_score),
            _to_dec(self.listening_score),
            _to_dec(self.writing_score),
            _to_dec(self.speaking_score),
        ]
        if rules["overall_kind"] == "sum_int":
            total = sum(subs, Decimal("0"))
            return _clamp(total, rules["overall_min"], rules["overall_max"])
        if rules["overall_kind"] == "avg_half":
            avg = sum(subs, Decimal("0")) / Decimal("4")
            return _clamp(_nearest_half(avg), rules["overall_min"], rules["overall_max"])
        if rules["overall_kind"] == "avg_int":
            avg = sum(subs, Decimal("0")) / Decimal("4")
            rounded = avg.to_integral_value(rounding=ROUND_HALF_UP)
            return _clamp(rounded, rules["overall_min"], rules["overall_max"])
        return _to_dec(self.overall_score)

    # ── Validation + normalization ─────────────────────────────────
    def clean(self):
        """
        Validation rules when has_recent_english_exam is True:
        - exam_type required, must be one of EXAM_RULES keys
        - exam_date required, within last 5 years (inclusive)
        - if C1/C2 → cambridge_grade required
        - validate 4 subscores (presence, range, step)
        - overall: compute unless manual override is on; then range/step-check
        """
        super().clean()

        if not self.has_recent_english_exam:
            return

        errors: dict[str, list | str] = {}

        # 1) exam_type + exam_date
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
                date_ok = True

        et = (self.exam_type or "").lower()
        if et not in EXAM_RULES:
            if self.exam_type:
                errors["exam_type"] = _("Unknown exam type. Please choose one from the list.")

        # 2) Cambridge grade only for C1/C2 (+ optional UoE score)
        if et in {"c1", "c2"} and date_ok:
            if not self.cambridge_grade:
                errors["cambridge_grade"] = _("Please select your Cambridge grade (A, B, or C).")
            uoe = _to_dec(self.cambridge_use_of_english)
            if uoe is not None and not _is_step(uoe, EXAM_RULES[et]["sub_step"]):
                errors["cambridge_use_of_english"] = _("Please enter a whole number.")

        # 3) Sub-scores (only if exam type and date are ok)
        rules = None
        sub_fields = ("reading_score", "listening_score", "writing_score", "speaking_score")
        if et in EXAM_RULES and date_ok:
            rules = EXAM_RULES[et]
            for f in sub_fields:
                v = _to_dec(getattr(self, f))
                if v is None:
                    errors[f] = _("Please enter a value.")
                    continue
                if not (rules["sub_min"] <= v <= rules["sub_max"]):
                    errors[f] = _("Value must be between %(lo)s and %(hi)s.") % {
                        "lo": rules["sub_min"],
                        "hi": rules["sub_max"],
                    }
                    continue
                if not _is_step(v, rules["sub_step"]):
                    step_msg = (
                        _("in 0.5 steps (e.g., 6.5)")
                        if str(rules["sub_step"]) == "0.5"
                        else _("in whole numbers")
                    )
                    errors[f] = _("Please enter a valid value ") + step_msg + "."

        # 4) Overall (compute or validate)
        if rules is not None and not any(k in errors for k in sub_fields):
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
                        ) % {"lo": rules["overall_min"], "hi": rules["overall_max"]}
                    if et == "ielts" and not _is_step(ov, Decimal("0.5")):
                        errors["overall_score"] = _("Overall must be in 0.5 steps (e.g., 6.5).")
            else:
                self.overall_score = self._compute_overall_from_subs(rules)

        if errors:
            raise ValidationError(errors)

    # 🔧 make sure this is at CLASS LEVEL (not nested inside clean)
    def save(self, *args, **kwargs):
        # Track confirmation timestamp transition (False -> True)
        if self.pk is not None:
            try:
                previous = (
                    type(self)
                    .objects.only("academic_integrity_confirmed", "academic_integrity_confirmed_at")
                    .get(pk=self.pk)
                )
                previously_confirmed = bool(previous.academic_integrity_confirmed)
            except type(self).DoesNotExist:
                previously_confirmed = False
        else:
            previously_confirmed = False

        # Normalize dependent fields when the switch is False
        if not self.has_recent_english_exam:
            self.exam_type = ""
            self.exam_date = None
            self.cambridge_grade = None
            self.cambridge_use_of_english = None
            self._clear_exam_scores()
        else:
            et = (self.exam_type or "").lower()
            if et not in EXAM_RULES:
                self._clear_exam_scores()
                self.cambridge_grade = None
                self.cambridge_use_of_english = None
            elif et not in {"c1", "c2"}:
                # Not a Cambridge exam → clear Cambridge-only fields
                self.cambridge_grade = None
                self.cambridge_use_of_english = None

        # Set confirmation timestamp when the box is (newly) checked
        if self.academic_integrity_confirmed and not previously_confirmed:
            self.academic_integrity_confirmed_at = timezone.now()

        super().save(*args, **kwargs)

    # ── Completion logic used by gating nav, etc. ──────────────────
    def is_complete(self) -> bool:
        # Base requirements + honour code
        base_ok = bool(
            self.phone and self.student_number and self.subject_area and not self.is_locked
        )
        if not base_ok:
            return False
        if not self.academic_integrity_confirmed:
            return False

        # If no exam → complete after base + confirmation
        if not self.has_recent_english_exam:
            return True

        # With exam → require exam_type + exam_date + subs + overall
        # (plus Cambridge grade when applicable)
        subs_ok = all(
            getattr(self, f) is not None
            for f in (
                "reading_score",
                "listening_score",
                "writing_score",
                "speaking_score",
                "overall_score",
            )
        )
        et = (self.exam_type or "").lower()
        cambridge_ok = True if et not in {"c1", "c2"} else bool(self.cambridge_grade)

        return bool(self.exam_type and self.exam_date and subs_ok and cambridge_ok)
