# src/users/tests/test_models.py
from django.contrib.auth import get_user_model
import pytest

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.parametrize("role", ["student", "teacher", "admin"])
def test_create_user_per_role(role):
    """
    Creating a regular user with any role (student/teacher/admin)
    should persist correctly, set the role, and allow password check.
    """
    u = User.objects.create_user(email=f"{role}@example.com", password="pass1234", role=role)

    # user was saved
    assert u.pk is not None
    # role was stored correctly
    assert u.role == role
    # password hash check works
    assert u.check_password("pass1234")
    # regular users should never be superusers by default
    assert u.is_superuser is False


@pytest.mark.django_db
def test_create_superuser_defaults_to_admin_role():
    """
    Creating a superuser should force is_staff=True, is_superuser=True,
    and default the role to 'admin' regardless of extra_fields.
    """
    su = User.objects.create_superuser(email="super@example.com", password="pass1234")

    # superuser must have these flags
    assert su.is_staff is True
    assert su.is_superuser is True
    # role should default to ADMIN
    assert su.role == User.Roles.ADMIN
