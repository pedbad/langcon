# src/profiles/models.py
from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models


class Profile(models.Model):
    """
    Stores additional student-specific details that extend the CustomUser model.
    Created automatically for each student upon registration (if PROFILES_AUTO_CREATE = True).
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        help_text="Linked user account for this profile.",
    )

    # 📞 Required contact phone number.
    # Validation ensures only digits, spaces, '+' or '-' are accepted.
    phone = models.CharField(
        max_length=20,
        blank=False,  # 🔒 required at form and DB level
        validators=[
            RegexValidator(
                regex=r"^\+?[0-9\s\-]{7,20}$",
                message="Enter a valid phone number (digits, spaces, +, -).",
            )
        ],
        help_text="Student contact number (required).",
    )

    # 🔐 Once a profile is locked, students can no longer edit it.
    is_locked = models.BooleanField(default=False)

    # 🕓 Timestamps for auditability.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Profile"
        verbose_name_plural = "Profiles"

    def __str__(self) -> str:
        """Readable string representation for admin/debug."""
        user_ident = getattr(self.user, "email", str(self.user))
        return f"Profile<{user_ident}>"

    def is_complete(self) -> bool:
        """
        Determines whether the profile is complete.
        This logic will expand as we add more required fields.
        """
        return bool(self.phone and not self.is_locked)
