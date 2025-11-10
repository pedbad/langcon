# src/profiles/forms.py
from datetime import date

from django import forms

from .models import Profile

# ────────────────────────────────────────────────────────────────
# Shared CSS atoms (tweak once → everywhere updates)
# ────────────────────────────────────────────────────────────────
BASE_INPUT = (
    "w-full rounded-md border border-input bg-background text-sm shadow-sm "
    "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
)
SELECT_APPEARANCE = "appearance-none pr-10"

# For inputs that pair with a left addon icon:
SCORE_INPUT_JOINED = "score-input h-10 rounded-r-md rounded-l-none -ml-px px-3 " + BASE_INPUT

PHONE_INPUT = BASE_INPUT + " px-3 py-2"  # phone row keeps its own look
SELECT_INPUT = BASE_INPUT + " px-3 py-2 " + SELECT_APPEARANCE


# ────────────────────────────────────────────────────────────────
# Tiny helpers to keep the form tidy
# ────────────────────────────────────────────────────────────────
def _select_widget(*, element_id: str | None = None) -> forms.Select:
    attrs = {"class": SELECT_INPUT}
    if element_id:
        attrs["id"] = element_id
    return forms.Select(attrs=attrs)


def _number_input_widget(*, step: str = "0.5") -> forms.NumberInput:
    # Default step=0.5 (IELTS); Use "1" for integer-only fields (e.g. Use of English)
    return forms.NumberInput(
        attrs={
            "step": step,
            "placeholder": "—",
            "class": SCORE_INPUT_JOINED,
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
    # Exam scores (left-addon friendly)
    # ─────────────────────────────
    reading_score = forms.DecimalField(
        label="Reading",
        required=False,
        min_value=0,
        widget=_number_input_widget(step="0.5"),
        help_text="Your reading score.",
    )
    listening_score = forms.DecimalField(
        label="Listening",
        required=False,
        min_value=0,
        widget=_number_input_widget(step="0.5"),
    )
    writing_score = forms.DecimalField(
        label="Writing",
        required=False,
        min_value=0,
        widget=_number_input_widget(step="0.5"),
    )
    speaking_score = forms.DecimalField(
        label="Speaking",
        required=False,
        min_value=0,
        widget=_number_input_widget(step="0.5"),
    )
    overall_score = forms.DecimalField(
        label="Overall",
        required=False,
        min_value=0,
        widget=_number_input_widget(step="0.5"),
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
        widget=_number_input_widget(step="1"),  # integers for C1/C2
        help_text="Whole number score (only for Cambridge C1/C2).",
    )

    # ─────────────────────────────
    # Honour code / confirmation
    # ─────────────────────────────
    academic_integrity_confirmed = forms.BooleanField(
        label=(
            "I confirm that all the information provided is accurate and that all future work will "
            "be my own unaided effort, completed without the use of AI or large language models."
        ),
        required=True,
        widget=forms.CheckboxInput(
            attrs={
                "id": "id_academic_integrity_confirmed",
                "class": (
                    "h-[1.125rem] w-[1.125rem] appearance-none rounded-[0.25rem] "
                    "border-[0.125rem] border-gray-400 outline-none cursor-pointer "
                    "checked:border-red-600 checked:bg-red-600"
                ),
            }
        ),
        help_text="This confirmation is required to save your profile.",
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
            "academic_integrity_confirmed",
        ]
        widgets = {
            "phone": forms.TextInput(
                attrs={
                    "id": "id_phone",
                    "placeholder": "Phone",
                    "required": True,
                    "class": PHONE_INPUT,
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

        # Cambridge grade choices with a placeholder
        self.fields["cambridge_grade"].choices = [("", "Select a grade…")] + list(
            Profile.CAMBRIDGE_GRADES
        )

        # 🔹 Add placeholders for Day / Month / Year selects
        self.fields["exam_day"].choices = [("", "Day")] + _day_choices()
        self.fields["exam_month"].choices = [("", "Month")] + _month_choices()
        # Use a sensible range and add placeholder
        self.fields["exam_year"].choices = [("", "Year")] + _year_choices(span=5)
