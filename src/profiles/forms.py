from datetime import date

from django import forms

from .models import Profile


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
    # Visa Yes/No (you already had these)
    requires_uk_student_visa = forms.TypedChoiceField(
        label="Do you require a student visa to study in the UK?",
        choices=(("True", "Yes"), ("False", "No")),
        coerce=lambda v: v == "True",
        required=True,
        initial="True",
        widget=forms.Select(
            attrs={
                "id": "id_requires_uk_student_visa",
                "class": (
                    "w-full rounded-md border border-input bg-background px-3 py-2 text-sm "
                    "shadow-sm focus-visible:outline-none "
                    "focus-visible:ring-1 focus-visible:ring-ring"
                ),
            }
        ),
    )

    has_recent_english_exam = forms.TypedChoiceField(
        label="Have you taken an English language exam in the past five years?",
        choices=(("False", "No"), ("True", "Yes")),
        coerce=lambda v: v == "True",
        required=True,
        initial="False",
        widget=forms.Select(
            attrs={
                "id": "id_has_recent_english_exam",
                "class": (
                    "w-full rounded-md border border-input bg-background px-3 py-2 text-sm "
                    "shadow-sm focus-visible:outline-none "
                    "focus-visible:ring-1 focus-visible:ring-ring"
                ),
            }
        ),
    )

    # --- Date parts for exam_date (conditionally required) ---
    exam_day = forms.ChoiceField(
        label="Day",
        choices=_day_choices(),
        required=False,
        widget=forms.Select(
            attrs={
                "id": "id_exam_day",
                "class": (
                    "w-full rounded-md border border-input bg-background px-2 py-2 text-sm "
                    "shadow-sm focus-visible:outline-none focus-visible:ring-1 "
                    "focus-visible:ring-ring"
                ),
            }
        ),
    )
    exam_month = forms.ChoiceField(
        label="Month",
        choices=_month_choices(),
        required=False,
        widget=forms.Select(
            attrs={
                "id": "id_exam_month",
                "class": (
                    "w-full rounded-md border border-input bg-background px-2 py-2 text-sm "
                    "shadow-sm focus-visible:outline-none focus-visible:ring-1 "
                    "focus-visible:ring-ring"
                ),
            }
        ),
    )
    exam_year = forms.ChoiceField(
        label="Year",
        choices=_year_choices(span=5),
        required=False,
        widget=forms.Select(
            attrs={
                "id": "id_exam_year",
                "class": (
                    "w-full rounded-md border border-input bg-background px-2 py-2 text-sm "
                    "shadow-sm focus-visible:outline-none focus-visible:ring-1 "
                    "focus-visible:ring-ring"
                ),
            }
        ),
    )

    # Accept model.clean() errors keyed to "exam_date" without writing it back from the form
    exam_date = forms.DateField(required=False, widget=forms.HiddenInput())

    # ────────────────────────────────────────────────────────────────
    # Exam sub-scores and overall
    # ────────────────────────────────────────────────────────────────
    COMMON_SCORE_INPUT_ATTRS = {
        "step": "0.5",  # default; JS will adjust per exam type
        "placeholder": "—",
        "class": (
            "score-input w-full rounded-md border border-input bg-background px-3 py-2 text-sm "
            "shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        ),
    }

    reading_score = forms.DecimalField(
        label="Reading",
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs=COMMON_SCORE_INPUT_ATTRS),
        help_text="Your reading score.",
    )

    listening_score = forms.DecimalField(
        label="Listening",
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs=COMMON_SCORE_INPUT_ATTRS),
    )

    writing_score = forms.DecimalField(
        label="Writing",
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs=COMMON_SCORE_INPUT_ATTRS),
    )

    speaking_score = forms.DecimalField(
        label="Speaking",
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs=COMMON_SCORE_INPUT_ATTRS),
    )

    overall_score = forms.DecimalField(
        label="Overall",
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs=COMMON_SCORE_INPUT_ATTRS),
    )

    class Meta:
        model = Profile
        fields = [
            "phone",
            "subject_area",
            "requires_uk_student_visa",
            "has_recent_english_exam",
            "exam_type",
            # (exam_date handled by day/month/year)
            "reading_score",
            "listening_score",
            "writing_score",
            "speaking_score",
            "overall_score",
            "overall_manual_override",
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
            "subject_area": forms.Select(
                attrs={
                    "required": True,
                    "class": (
                        "w-full rounded-md border border-input bg-background px-3 py-2 text-sm "
                        "shadow-sm focus-visible:outline-none "
                        "focus-visible:ring-1 focus-visible:ring-ring appearance-none pr-10"
                    ),
                }
            ),
            "exam_type": forms.Select(
                attrs={
                    "class": (
                        "w-full rounded-md border border-input bg-background px-3 py-2 text-sm "
                        "shadow-sm focus-visible:outline-none focus-visible:ring-1 "
                        "focus-visible:ring-ring appearance-none pr-10"
                    ),
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Prefill day/month/year from existing exam_date when editing
        ed = getattr(self.instance, "exam_date", None)
        if ed:
            self.initial.setdefault("exam_day", f"{ed.day}")
            self.initial.setdefault("exam_month", f"{ed.month}")
            self.initial.setdefault("exam_year", f"{ed.year}")

    def clean_phone(self):
        v = (self.cleaned_data.get("phone") or "").strip()
        return v

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
                from datetime import date

                try:
                    assembled = date(int(y), int(m), int(d))
                except ValueError:
                    self.add_error("exam_day", "Enter a valid exam date.")

                if assembled:
                    today = date.today()
                    min_date = date(today.year - 5, today.month, today.day)
                    if not (min_date <= assembled <= today):
                        self.add_error("exam_day", "Exam date must be within the last five years.")
                        assembled = None
            else:
                # missing any part
                if not d or not m or not y:
                    msg = "Please provide the exam date (day, month, and year)."
                    if not d:
                        self.add_error("exam_day", msg)
                    if not m:
                        self.add_error("exam_month", msg)
                    if not y:
                        self.add_error("exam_year", msg)

            # 🔐 write both fields onto the instance before model.clean()
            if self.instance:
                self.instance.exam_type = exam_type or ""
                self.instance.exam_date = assembled
            # expose assembled date via cleaned_data (non-model field)
            cleaned["exam_date"] = assembled

        else:
            # switch OFF → normalize on the instance as well
            if self.instance:
                self.instance.exam_type = ""
                self.instance.exam_date = None

        return cleaned
