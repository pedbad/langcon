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
        "created_at",
        "updated_at",
    )
    list_display_links = ("user_email",)  # 👈 make the email the link
    list_filter = ("is_locked", "subject_area", "created_at")
    search_fields = ("user__email", "user__first_name", "user__last_name", "phone")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("user",)
    fieldsets = (
        (None, {"fields": ("user", "is_locked")}),
        ("Contact & Area", {"fields": ("phone", "subject_area")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="User", ordering="user__email")
    def user_email(self, obj):
        return getattr(obj.user, "email", str(obj.user))

    # keep your superuser-only edits if you want
    def has_add_permission(self, request):
        return bool(request.user and request.user.is_superuser)

    def has_change_permission(self, request, obj=None):
        return bool(request.user and request.user.is_superuser)

    def has_delete_permission(self, request, obj=None):
        return bool(request.user and request.user.is_superuser)
