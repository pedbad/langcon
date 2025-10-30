# src/profiles/models.py
from django.conf import settings
from django.db import models


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    is_locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        user_ident = getattr(self.user, "email", str(self.user))
        return f"Profile<{user_ident}>"

    # Placeholder; we’ll flesh this out as we add fields.
    def is_complete(self) -> bool:
        return False
