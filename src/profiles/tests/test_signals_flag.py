# src/profiles/tests/test_signals_flag.py
from django.contrib.auth import get_user_model
from django.test import override_settings
import pytest

from profiles.models import Profile

User = get_user_model()


@pytest.mark.django_db
@override_settings(PROFILES_AUTO_CREATE=True)
def test_auto_create_enabled():
    u = User.objects.create_user(email="s1@example.com", password="x", role="student")
    assert Profile.objects.filter(user=u).exists()


@pytest.mark.django_db
@override_settings(PROFILES_AUTO_CREATE=False)
def test_auto_create_disabled():
    u = User.objects.create_user(email="s2@example.com", password="x", role="student")
    assert not Profile.objects.filter(user=u).exists()
