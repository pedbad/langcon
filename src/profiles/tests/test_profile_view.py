# src/profiles/tests/test_profile_view.py
from django.contrib.auth import get_user_model
from django.urls import reverse
import pytest

from profiles.models import Profile

User = get_user_model()


@pytest.mark.django_db
def test_profile_view_creates_profile_and_renders(client, settings):
    # (Optional) ensure signal isn’t masking the get_or_create behavior
    settings.PROFILES_AUTO_CREATE = False

    student = User.objects.create_user(email="vp@example.com", password="pass1234", role="student")
    client.login(email=student.email, password="pass1234")

    assert not Profile.objects.filter(user=student).exists()
    resp = client.get(reverse("profiles:profile"))
    assert resp.status_code == 200

    # Profile should now exist (created by the view)
    assert Profile.objects.filter(user=student).exists()
    # Smoke check for the page title/heading
    assert b"Complete Your Profile" in resp.content
