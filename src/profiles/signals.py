# src/profiles/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.apps import apps
from django.contrib.auth import get_user_model

User = get_user_model()

@receiver(post_save, sender=User)
def ensure_profile_for_student(sender, instance, created, **kwargs):
    if not created:
        return
    if getattr(instance, "role", None) != "student":
        return
    Profile = apps.get_model("profiles", "Profile")
    Profile.objects.get_or_create(user=instance)
