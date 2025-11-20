# src/profiles/admin.py
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
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

    # 👉 Make both ID and user (email) clickable to the Profile change page
    list_display_links = ("id", "user")

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
        (None, {"fields": ("user", "is_locked")}),
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
