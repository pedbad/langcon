# src/profiles/signals.py
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

User = get_user_model()


@receiver(post_save, sender=User)
def ensure_profile_for_student(sender, instance, created, **kwargs):
    """
    When a new user is created with role == 'student',
    ensure a one-to-one Profile exists (feature-flagged).
    """
    # Feature flag: allow tests (or envs) to disable auto-creation
    if not getattr(settings, "PROFILES_AUTO_CREATE", True):
        return

    if not created:
        return
    if getattr(instance, "role", None) != "student":
        return

    Profile = apps.get_model("profiles", "Profile")
    Profile.objects.get_or_create(user=instance)
