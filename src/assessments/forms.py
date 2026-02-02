# src/assessments/forms.py
from django import forms


class WritingAnswerForm(forms.Form):
    writing_answer = forms.CharField(
        label="Your answer",
        widget=forms.Textarea(
            attrs={
                "rows": 10,
                "placeholder": "Write your 300–350 word answer here…",
                "maxlength": "3000",  # ≈500 words cap (client-side)
                "class": "writing-answer-input",
            }
        ),
        required=False,  # drafts can be empty
    )


class LLMQuestion1AnswerForm(forms.Form):
    llm_question_1_answer = forms.CharField(
        label="Your answer to follow-up question 1",
        widget=forms.Textarea(
            attrs={
                "rows": 8,
                "placeholder": "Write your answer to this follow-up question here…",
                "maxlength": "3000",
                "class": "writing-answer-input",
            }
        ),
        required=False,  # drafts can be empty
    )


class LLMQuestion2AnswerForm(forms.Form):
    llm_question_2_answer = forms.CharField(
        label="Your answer to follow-up question 2",
        widget=forms.Textarea(
            attrs={
                "rows": 8,
                "placeholder": "Write your answer to this second follow-up question here…",
                "maxlength": "3000",
                "class": "writing-answer-input",
            }
        ),
        required=False,
    )  # drafts can be empty


class ListeningAnswerForm(forms.Form):
    listening_answer = forms.CharField(
        label="Your listening summary",
        widget=forms.Textarea(
            attrs={
                "rows": 8,
                "placeholder": "Write your 250–350 word summary of the lecture here…",
                "maxlength": "3000",  # similar cap to other answers
                "class": "writing-answer-input",
            }
        ),
        required=False,  # drafts can be empty; submit handler will enforce band
    )


class ReadingAnswerForm(forms.Form):
    """
    Simple form for the student's Reading Comprehension answer.

    We keep it as a plain Form (not ModelForm) to mirror the other
    assessment forms and keep the view logic explicit.
    """

    reading_answer = forms.CharField(
        label="Reading answer",
        required=False,  # allow empty drafts
        widget=forms.Textarea(
            attrs={
                "id": "id_reading_answer",
                "rows": 10,
                "maxlength": "3000",  # ≈ 500 words, consistent with other tasks
                "class": "writing-answer-input",  # reuse the nice textarea styling
                "placeholder": (
                    "Summarise the two debate positions and state your view " "(250–300 words)…"
                ),
            }
        ),
    )
