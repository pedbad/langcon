# src/users/forms.py
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm as DjangoUserCreationForm
from django.core.exceptions import ValidationError

# Unfold-styled admin forms
from unfold.forms import (
    UserChangeForm as UnfoldUserChangeForm,
    UserCreationForm as UnfoldUserCreationForm,
)

from profiles.models import Profile

User = get_user_model()


# --- Public (non-admin) registration form you already had --------------------
class RegisterForm(DjangoUserCreationForm):
    # expose role for now (default student)
    role = forms.ChoiceField(choices=User.Roles.choices, initial=User.Roles.STUDENT)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    student_number = forms.CharField(
        max_length=20,
        required=False,
        label="University Student Number (USN) or ADTIS identifier",
        help_text=(
            "Enter your University Student Number (USN). "
            "(USN is a 9 digit number that usually starts with a 3.)"
        ),
    )

    class Meta(DjangoUserCreationForm.Meta):
        model = User
        # our model uses email as USERNAME_FIELD
        fields = ("email", "first_name", "last_name", "role")

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")

        if role != User.Roles.STUDENT:
            return cleaned_data

        first_name = (cleaned_data.get("first_name") or "").strip()
        last_name = (cleaned_data.get("last_name") or "").strip()
        student_number = (cleaned_data.get("student_number") or "").strip()

        if not first_name:
            self.add_error("first_name", "First name is required for student accounts.")
        if not last_name:
            self.add_error("last_name", "Last name is required for student accounts.")
        if not student_number:
            self.add_error("student_number", "Student number (USN) is required for students.")
            return cleaned_data

        # Reuse Profile validators to keep USN format rules consistent.
        field = Profile._meta.get_field("student_number")
        for validator in field.validators:
            try:
                validator(student_number)
            except ValidationError as exc:
                self.add_error("student_number", exc)

        if Profile.objects.filter(student_number=student_number).exists():
            self.add_error("student_number", "This student number is already in use.")

        cleaned_data["first_name"] = first_name
        cleaned_data["last_name"] = last_name
        cleaned_data["student_number"] = student_number
        return cleaned_data


# --- Admin-only forms (Unfold-styled) ---------------------------------------
class AdminUserAddForm(UnfoldUserCreationForm):
    """Used by Django admin Add User page (gives Unfold-styled password1/2)."""

    class Meta(UnfoldUserCreationForm.Meta):
        model = User
        fields = ("email",)  # password1/password2 come from parent form


class AdminUserChangeForm(UnfoldUserChangeForm):
    """Used by Django admin Change User page (Unfold-styled widgets)."""

    class Meta(UnfoldUserChangeForm.Meta):
        model = User
        fields = (
            "email",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
        )
