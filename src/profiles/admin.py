# src/profiles/admin.py
from django import forms
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from .models import Profile


class ProfileAdminForm(forms.ModelForm):
    """
    Admin form for Profile:
    - Enforces student_number as required in the admin UI.
    - Makes subject_area required and shows an explicit blank choice
      so new profiles don't default visually to 'Arts and Humanities'.
    """

    class Meta:
        model = Profile
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ── Student number (USN) ───────────────────────────────────
        sn = self.fields.get("student_number")
        if sn:
            sn.required = True
            sn.help_text = (
                "Required: enter the student's real Unique Student Number (USN) "
                "or CRSid (letters and digits only)."
            )
            sn.widget.attrs.setdefault("placeholder", "e.g. 301004293")

        # ── Subject area ───────────────────────────────────────────
        sa = self.fields.get("subject_area")
        if sa:
            sa.required = True
            # Prepend an explicit blank option so an unset value doesn't
            # appear as a real subject (e.g. 'Arts and Humanities').
            choices = list(sa.choices)
            if not choices or choices[0][0] != "":
                choices.insert(0, ("", "---------"))
            sa.choices = choices


@admin.register(Profile)
class ProfileAdmin(ModelAdmin):
    form = ProfileAdminForm

    list_display = (
        "id",
        "user",  # usually shows email (CustomUser.__str__)
        "student_number",  # USN/CRSid column, right after email
        "is_locked",
        "subject_area",
        "phone",
        "requires_uk_student_visa",
        "has_recent_english_exam",
        "exam_type",
        "reading_score",
        "listening_score",
        "writing_score",
        "speaking_score",
        "overall_score",
        "academic_integrity_confirmed",
        "cambridge_grade",
        "cambridge_use_of_english",
        "created_at",
        "updated_at",
        "row_delete",
    )

    # Make ID, user (email) and student_number clickable to open the Profile
    list_display_links = ("id", "user", "student_number")

    list_filter = (
        "is_locked",
        "subject_area",
        "requires_uk_student_visa",
        "has_recent_english_exam",
        "exam_type",
        "academic_integrity_confirmed",
        "created_at",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "academic_integrity_confirmed_at",
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "user",
                    "student_number",  # shown prominently at the top
                    "is_locked",
                )
            },
        ),
        ("Contact & Area", {"fields": ("phone", "subject_area")}),
        ("Visa", {"fields": ("requires_uk_student_visa",)}),
        (
            "English Exam",
            {
                "fields": (
                    "has_recent_english_exam",
                    "exam_type",
                    "exam_date",
                    "reading_score",
                    "listening_score",
                    "writing_score",
                    "speaking_score",
                    "overall_score",
                    "overall_manual_override",
                    "cambridge_grade",
                    "cambridge_use_of_english",
                )
            },
        ),
        (
            "Honour Code",
            {
                "fields": (
                    "academic_integrity_confirmed",
                    "academic_integrity_confirmed_at",
                )
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["show_delete"] = True
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

    def row_delete(self, obj):
        url = reverse("admin:profiles_profile_delete", args=[obj.pk])
        return format_html('<a class="button button-danger" href="{}">Delete</a>', url)

    row_delete.short_description = "Delete"
