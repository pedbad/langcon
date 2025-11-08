# src/profiles/forms.py
from datetime import date

from django import forms

from .models import Profile


# ────────────────────────────────────────────────────────────────
# Tiny helpers to keep the form tidy
# ────────────────────────────────────────────────────────────────
def _select_widget(*, element_id: str | None = None) -> forms.Select:
    cls = (
        "w-full rounded-md border border-input bg-background px-3 py-2 text-sm "
        "shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring "
        "appearance-none pr-10"
    )
    attrs = {"class": cls}
    if element_id:
        attrs["id"] = element_id
    return forms.Select(attrs=attrs)


def _score_input_widget(step: str = "0.5") -> forms.NumberInput:
    # Default step=0.5 (IELTS); we can override per-field (e.g., Use of English → "1")
    return forms.NumberInput(
        attrs={
            "step": step,
            "placeholder": "—",
            "class": (
                "score-input w-full rounded-md border border-input bg-background px-3 py-2 text-sm "
                "shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            ),
        }
    )


def _day_choices():
    return [(i, f"{i:02d}") for i in range(1, 32)]


def _month_choices():
    return [
        (1, "Jan"),
        (2, "Feb"),
        (3, "Mar"),
        (4, "Apr"),
        (5, "May"),
        (6, "Jun"),
        (7, "Jul"),
        (8, "Aug"),
        (9, "Sep"),
        (10, "Oct"),
        (11, "Nov"),
        (12, "Dec"),
    ]


def _year_choices(span=5):
    y = date.today().year
    return [(y - i, str(y - i)) for i in range(span + 1)]  # inclusive


class ProfileForm(forms.ModelForm):
    # ─────────────────────────────
    # Visa + Exam “switch” fields
    # ─────────────────────────────
    requires_uk_student_visa = forms.TypedChoiceField(
        label="Do you require a student visa to study in the UK?",
        choices=(("True", "Yes"), ("False", "No")),
        coerce=lambda v: v == "True",
        required=True,
        initial="True",
        widget=_select_widget(element_id="id_requires_uk_student_visa"),
    )

    has_recent_english_exam = forms.TypedChoiceField(
        label="Have you taken an English language exam in the past five years?",
        choices=(("False", "No"), ("True", "Yes")),
        coerce=lambda v: v == "True",
        required=True,
        initial="False",
        widget=_select_widget(element_id="id_has_recent_english_exam"),
    )

    # ─────────────────────────────
    # Exam date (split D/M/Y)
    # ─────────────────────────────
    exam_day = forms.ChoiceField(
        label="Day",
        choices=_day_choices(),
        required=False,
        widget=_select_widget(element_id="id_exam_day"),
    )
    exam_month = forms.ChoiceField(
        label="Month",
        choices=_month_choices(),
        required=False,
        widget=_select_widget(element_id="id_exam_month"),
    )
    exam_year = forms.ChoiceField(
        label="Year",
        choices=_year_choices(span=5),
        required=False,
        widget=_select_widget(element_id="id_exam_year"),
    )

    # Hidden relay so model.clean can attach errors to “exam_date”
    exam_date = forms.DateField(required=False, widget=forms.HiddenInput())

    # ─────────────────────────────
    # Exam scores
    # ─────────────────────────────
    reading_score = forms.DecimalField(
        label="Reading",
        required=False,
        min_value=0,
        widget=_score_input_widget(step="0.5"),
        help_text="Your reading score.",
    )
    listening_score = forms.DecimalField(
        label="Listening",
        required=False,
        min_value=0,
        widget=_score_input_widget(step="0.5"),
    )
    writing_score = forms.DecimalField(
        label="Writing",
        required=False,
        min_value=0,
        widget=_score_input_widget(step="0.5"),
    )
    speaking_score = forms.DecimalField(
        label="Speaking",
        required=False,
        min_value=0,
        widget=_score_input_widget(step="0.5"),
    )
    overall_score = forms.DecimalField(
        label="Overall",
        required=False,
        min_value=0,
        widget=_score_input_widget(step="0.5"),
    )

    # ─────────────────────────────
    # Cambridge only (C1/C2)
    # ─────────────────────────────
    cambridge_grade = forms.ChoiceField(
        label="Cambridge grade",
        required=False,  # enforced in model.clean only for C1/C2
        widget=_select_widget(element_id="id_cambridge_grade"),
        help_text="Select A, B, or C (only for Cambridge C1/C2).",
    )

    cambridge_use_of_english = forms.DecimalField(
        label="Use of English (score)",
        required=False,  # optional; if present, model.clean validates
        min_value=0,
        widget=_score_input_widget(step="1"),  # integers for C1/C2 bands
        help_text="Whole number score (only for Cambridge C1/C2).",
    )

    class Meta:
        model = Profile
        fields = [
            "phone",
            "subject_area",
            "requires_uk_student_visa",
            "has_recent_english_exam",
            "exam_type",
            # (exam_date assembled from the split fields)
            "reading_score",
            "listening_score",
            "writing_score",
            "speaking_score",
            "overall_score",
            "overall_manual_override",
            "cambridge_grade",
            "cambridge_use_of_english",
        ]
        widgets = {
            "phone": forms.TextInput(
                attrs={
                    "id": "id_phone",
                    "placeholder": "Phone",
                    "required": True,
                    "class": (
                        "w-full rounded-md border border-input bg-background px-3 py-2 text-sm "
                        "shadow-sm focus-visible:outline-none "
                        "focus-visible:ring-1 focus-visible:ring-ring"
                    ),
                }
            ),
            "subject_area": _select_widget(element_id="id_subject_area"),
            "exam_type": _select_widget(element_id="id_exam_type"),
        }

    # ────────────────────────────────────────────────────────────────
    # Init: seed split date + inject Cambridge grade choices
    # ────────────────────────────────────────────────────────────────
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Prefill D/M/Y from existing exam_date
        ed = getattr(self.instance, "exam_date", None)
        if ed:
            self.initial.setdefault("exam_day", f"{ed.day}")
            self.initial.setdefault("exam_month", f"{ed.month}")
            self.initial.setdefault("exam_year", f"{ed.year}")

        # Inject grade choices with a placeholder (no dash shown)
        self.fields["cambridge_grade"].choices = [("", "Select grade…")] + list(
            Profile.CAMBRIDGE_GRADES
        )

    # ────────────────────────────────────────────────────────────────
    # Simple normalisations
    # ────────────────────────────────────────────────────────────────
    def clean_phone(self):
        return (self.cleaned_data.get("phone") or "").strip()

    # Assemble exam_date and mirror to instance so model.clean() can validate
    def clean(self):
        cleaned = super().clean()
        has_exam = cleaned.get("has_recent_english_exam") is True

        if has_exam:
            exam_type = cleaned.get("exam_type")
            d, m, y = cleaned.get("exam_day"), cleaned.get("exam_month"), cleaned.get("exam_year")

            if not exam_type:
                self.add_error("exam_type", "Please select the exam taken.")

            assembled = None
            if d and m and y:
                try:
                    assembled = date(int(y), int(m), int(d))
                except ValueError:
                    self.add_error("exam_day", "Enter a valid exam date.")
                else:
                    today = date.today()
                    min_date = date(today.year - 5, today.month, today.day)
                    if not (min_date <= assembled <= today):
                        self.add_error("exam_day", "Exam date must be within the last five years.")
                        assembled = None
            else:
                msg = "Please provide the exam date (day, month, and year)."
                if not d:
                    self.add_error("exam_day", msg)
                if not m:
                    self.add_error("exam_month", msg)
                if not y:
                    self.add_error("exam_year", msg)

            if self.instance:
                self.instance.exam_type = exam_type or ""
                self.instance.exam_date = assembled
            cleaned["exam_date"] = assembled
        else:
            if self.instance:
                self.instance.exam_type = ""
                self.instance.exam_date = None

        return cleaned
