# src/profiles/tests/test_profile_view.py
from django.contrib.auth import get_user_model
from django.urls import reverse
import pytest

from profiles.models import Profile

User = get_user_model()


@pytest.fixture
def student_user(db):
    user = User.objects.create_user(
        email="student@example.com",
        password="pass1234",
        role="student",
    )
    return user


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


@pytest.mark.django_db
def test_profile_page_renders_phone_input_and_icon(client, student_user, settings):
    settings.PROFILES_AUTO_CREATE = True  # or False; view will create with defaults
    client.force_login(student_user)
    resp = client.get(reverse("profiles:profile"))
    assert resp.status_code == 200
    assert b'name="phone"' in resp.content
    # sanity check that an inline SVG icon rendered
    assert b"<svg" in resp.content and b'viewBox="0 -960 960 960"' in resp.content


@pytest.mark.django_db
def test_student_can_update_phone(client, student_user):
    client.force_login(student_user)
    resp = client.post(reverse("profiles:profile"), {"phone": "+441234567890"})
    assert resp.status_code == 302  # redirects after save
    student_user.refresh_from_db()
    assert student_user.profile.phone == "+441234567890"
    assert student_user.profile.is_complete() is True


@pytest.mark.django_db
def test_phone_is_required(client, student_user):
    client.force_login(student_user)
    resp = client.post(reverse("profiles:profile"), {"phone": ""})
    assert resp.status_code == 200  # stays on page with error
    assert (
        b"This field is required" in resp.content or b"Enter a valid phone number" in resp.content
    )
