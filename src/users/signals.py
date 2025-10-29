# src/users/signals.py
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import transaction
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver

from .utils import get_domain_and_scheme, send_invite_email

User = get_user_model()
TEACHER_GROUP_NAME = "Teacher Admin"


# -------------------------------
# Invite email after user create
# -------------------------------
@receiver(post_save, sender=User)
def send_invite_on_create(sender, instance, created: bool, **kwargs):
    """
    When a new user is created without a usable password,
    send them a set-password invite after the transaction commits.
    """
    if not created:
        return

    # Skip superusers and anyone who already has a password.
    if instance.is_superuser or instance.has_usable_password():
        return

    def _send():
        domain, use_https = get_domain_and_scheme(None)
        send_invite_email(instance, domain=domain, use_https=use_https)

    # Run only after DB commit so uid/token are valid.
    transaction.on_commit(_send)


# -------------------------------
# Teacher Admin group bootstrap
# -------------------------------


@receiver(post_migrate)
def ensure_teacher_admin_group(sender, **kwargs):
    """
    Ensure Teacher Admin exists, has the right perms, and all teacher users
    are staff & in the group. Controlled by settings.TEACHER_ADMIN_FULL_PERMS.
    """
    full_perms = getattr(settings, "TEACHER_ADMIN_FULL_PERMS", True)

    group, _ = Group.objects.get_or_create(name=TEACHER_GROUP_NAME)
    perms_qs = (
        Permission.objects.all()
        if full_perms
        else Permission.objects.filter(codename__startswith="view_")
    )
    group.permissions.set(perms_qs)
    group.save()

    # Sync existing teachers
    for u in User.objects.filter(role="teacher"):
        if not u.is_staff:
            u.is_staff = True
            u.save(update_fields=["is_staff"])
        u.groups.add(group)


# Connect after migrations (use a stable dispatch_uid to avoid double-wiring)
post_migrate.connect(
    ensure_teacher_admin_group,
    dispatch_uid="users.ensure_teacher_admin_group",
)
