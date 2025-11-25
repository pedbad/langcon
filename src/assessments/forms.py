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
                "placeholder": "Write your 250–300 word summary of the lecture here…",
                "maxlength": "3000",  # similar cap to other answers
                "class": "writing-answer-input",
            }
        ),
        required=False,  # drafts can be empty; submit handler will enforce band
    )
