# src/users/admin.py
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.urls import NoReverseMatch, reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from import_export.admin import ImportExportModelAdmin
from unfold.admin import ModelAdmin
from unfold.contrib.import_export.forms import ExportForm, ImportForm
from unfold.forms import AdminPasswordChangeForm as UnfoldAdminPasswordChangeForm

from .forms import AdminUserAddForm, AdminUserChangeForm
from .models import User
from .resources import UserResource


@admin.register(User)
class UserAdmin(ImportExportModelAdmin, BaseUserAdmin, ModelAdmin):
    """
    Custom User admin:
    - Unfold styling via ModelAdmin
    - CSV Import/Export via django-import-export (with Unfold forms)
    - Styled password change page (Unfold AdminPasswordChangeForm)
    - 'Set password' button on the change page
    """

    # Unfold-styled forms for add/change
    add_form = AdminUserAddForm
    form = AdminUserChangeForm

    # Use Unfold's styled password form on /password/ page
    change_password_form = UnfoldAdminPasswordChangeForm

    # django-import-export config (Unfold-styled forms)
    resource_classes = [UserResource]
    import_form_class = ImportForm
    export_form_class = ExportForm

    # List / search
    ordering = ("email",)
    list_display = ("email", "first_name", "last_name", "role", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")
    search_fields = ("email", "first_name", "last_name")

    # Read-only helpers on the change form
    readonly_fields = ("date_joined", "password_link")

    def password_link(self, obj):
        """
        'Set password' button that lands on Django's built-in password form.
        Tries common admin URL names; falls back to canonical /admin/<app>/<model>/<pk>/password/.
        """
        if not obj or not obj.pk:
            return "Save user first to set a password."

        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name

        try:
            # Most custom models: admin:<app>_<model>_password_change
            url = reverse(f"admin:{app_label}_{model_name}_password_change", args=[obj.pk])
        except NoReverseMatch:
            try:
                # Built-in auth.User style
                url = reverse("admin:auth_user_password_change", args=[obj.pk])
            except NoReverseMatch:
                # Final fallback: build the canonical path (works regardless of URL names)
                admin_base = (getattr(settings, "UNFOLD", {}) or {}).get("SITE_URL", "/admin/")
                admin_base = admin_base.rstrip("/")
                url = f"{admin_base}/{app_label}/{model_name}/{obj.pk}/password/"

        return format_html('<a class="button" href="{}">Set password</a>', url)

    password_link.short_description = "Password"

    # Keep your existing fieldsets
    fieldsets = (
        (
            None,
            {"fields": ("email", "password_link")},
        ),  # button instead of raw password field
        (_("Personal info"), {"fields": ("first_name", "last_name")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "role",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    # Keep your add form layout
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "role",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )
