# src/assessor/forms.py
from django import forms

from assessments.models import AssessmentEvaluation


class AssessmentEvaluationDecisionForm(forms.ModelForm):
    class Meta:
        model = AssessmentEvaluation
        fields = [
            "recommendation",
            "assessor_comment",
            "exam_marked",
            "phone_follow_up",
            "exam_archived",
        ]
        widgets = {
            "assessor_comment": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # For CharField(choices=...), Django uses a ChoiceField.
        # It inserts ("", "---------") when the model field has blank=True.
        # We replace that empty label with our own.
        choices = list(self.fields["recommendation"].choices)
        if choices and choices[0][0] == "":
            choices[0] = ("", "Select a recommendation")
        else:
            choices.insert(0, ("", "Select a recommendation"))
        self.fields["recommendation"].choices = choices
