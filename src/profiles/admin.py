from django.contrib import admin

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
        "academic_integrity_confirmed",  # NEW
        "created_at",
        "updated_at",
    )

    list_filter = (
        "is_locked",
        "subject_area",
        "requires_uk_student_visa",
        "has_recent_english_exam",
        "exam_type",
        "academic_integrity_confirmed",  # NEW
        "created_at",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "academic_integrity_confirmed_at",  # NEW
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
