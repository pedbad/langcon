from django import forms

from .models import Profile


class ProfileForm(forms.ModelForm):
    # ────────────────────────────────────────────────────────────────
    # Visa (required Yes/No dropdown)
    # Coerces "True"/"False" → bool for the BooleanField (nullable in DB).
    # ────────────────────────────────────────────────────────────────
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

    # ────────────────────────────────────────────────────────────────
    # English exam decision (required Yes/No)
    # ────────────────────────────────────────────────────────────────
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

    class Meta:
        model = Profile
        fields = [
            "phone",
            "subject_area",
            "requires_uk_student_visa",
            "has_recent_english_exam",
            "exam_type",
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
                    "id": "id_subject_area",
                    "required": True,
                    "class": (
                        "w-full rounded-md border border-input bg-background px-3 py-2 text-sm "
                        "shadow-sm focus-visible:outline-none "
                        "focus-visible:ring-1 focus-visible:ring-ring "
                        "appearance-none pr-10"
                    ),
                }
            ),
            "exam_type": forms.Select(
                attrs={
                    "id": "id_exam_type",
                    "class": (
                        "w-full rounded-md border border-input bg-background px-3 py-2 text-sm "
                        "shadow-sm focus-visible:outline-none focus-visible:ring-1 "
                        "focus-visible:ring-ring appearance-none pr-10"
                    ),
                }
            ),
        }

    def clean_phone(self):
        value = (self.cleaned_data.get("phone") or "").strip()
        return value
