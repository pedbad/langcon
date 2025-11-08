# src/profiles/admin.py
from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user_email",
        "is_locked",
        "subject_area",
        "phone",
        "requires_uk_student_visa",
        "has_recent_english_exam",
        "exam_type",
        "cambridge_grade",
        "cambridge_use_of_english",
        "created_at",
        "updated_at",
    )
    list_display_links = ("user_email",)
    list_filter = (
        "is_locked",
        "subject_area",
        "requires_uk_student_visa",
        "has_recent_english_exam",
        "exam_type",
        "created_at",
    )
    search_fields = ("user__email", "user__first_name", "user__last_name", "phone")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("user",)

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
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="User", ordering="user__email")
    def user_email(self, obj):
        return getattr(obj.user, "email", str(obj.user))

    # superuser-only edits (unchanged)
    def has_add_permission(self, request):
        return bool(request.user and request.user.is_superuser)

    def has_change_permission(self, request, obj=None):
        return bool(request.user and request.user.is_superuser)

    def has_delete_permission(self, request, obj=None):
        return bool(request.user and request.user.is_superuser)
