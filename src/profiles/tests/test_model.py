# src/profiles/tests/test_model.py
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import override_settings
import pytest

from profiles.models import Profile

User = get_user_model()


@pytest.mark.django_db
@override_settings(PROFILES_AUTO_CREATE=False)  # ← disable signal here
def test_profile_one_to_one_and_defaults():
    u = User.objects.create_user(email="p1@example.com", password="pass1234", role="student")
    p = Profile.objects.create(user=u)
    assert p.user == u
    assert p.is_locked is False
    assert p.created_at is not None and p.updated_at is not None


@pytest.mark.django_db
@override_settings(PROFILES_AUTO_CREATE=False)  # ← disable signal here
def test_profile_one_per_user_unique():
    u = User.objects.create_user(email="p2@example.com", password="pass1234", role="student")
    Profile.objects.create(user=u)
    with pytest.raises(IntegrityError):
        Profile.objects.create(user=u)  # violates OneToOne uniqueness
