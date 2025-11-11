# src/profiles/signals.py
"""
Signal handlers for the Profiles app.

- ensure_profile_for_student:
    On User creation (role=student), ensure the one-to-one Profile exists.

- create_assessment_when_profile_complete:
    On Profile save, if it just became "complete", ensure the one-to-one
    Assessment exists (created once, then left alone).
"""

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

# Importing Profile here is safe (same app); used as the sender for the second signal.
from .models import Profile

User = get_user_model()


# ---------------------------------------------------------------------
# 1) Ensure each student gets a Profile on User creation (your original)
# ---------------------------------------------------------------------
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

    ProfileModel = apps.get_model("profiles", "Profile")
    ProfileModel.objects.get_or_create(user=instance)


# ---------------------------------------------------------------------
# 2) Create an Assessment when the Profile is (now) complete
#    NOTE: This listens to Profile saves, not User saves.
# ---------------------------------------------------------------------
@receiver(post_save, sender=Profile)
def create_assessment_when_profile_complete(sender, instance: Profile, **kwargs):
    """
    When a student's profile becomes complete for the first time,
    create their Assessment record if it doesn't already exist.
    """
    # Only for students
    if getattr(instance.user, "role", None) != "student":
        return

    # Gate on completeness; if it's not complete, do nothing.
    if not instance.is_complete():
        return

    # Lazy import via apps to avoid tight coupling
    Assessment = apps.get_model("assessments", "Assessment")

    # Idempotent: if it already exists, this is a no-op.
    Assessment.objects.get_or_create(user=instance.user)
