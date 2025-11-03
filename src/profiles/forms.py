# src/profiles/forms.py
from django import forms
from .models import Profile

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["phone"]
        widgets = {
            "phone": forms.TextInput(
                attrs={
                    "id": "id_phone",
                    "placeholder": "Phone",
                    "required": True,  # HTML5 required to match blank=False
                    "class": "w-full rounded-md border border-input bg-background px-3 py-2 text-sm "
                             "shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
                }
            ),
        }

    def clean_phone(self):
        value = (self.cleaned_data.get("phone") or "").strip()
        return value
