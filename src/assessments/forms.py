# src/assessments/forms.py
from django import forms


class WritingAnswerForm(forms.Form):
    writing_answer = forms.CharField(
        label="Your answer",
        widget=forms.Textarea(
            attrs={
                "rows": 10,
                "placeholder": "Write your 250–300 word answer here…",
                "maxlength": "3000",  # ≈500 words cap (client-side)
                "class": "writing-answer-input",
            }
        ),
        required=False,  # drafts can be empty
    )
