# src/profiles/apps.py
from django.apps import AppConfig


class ProfilesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "profiles"
    verbose_name = "Profiles"

    # def ready(self):
    #     # We'll import signals here in Step 3 (after the model exists)
    #     from . import signals  # noqa: F401
