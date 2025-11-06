# src/profiles/tests/test_profile_view.py
"""
Profiles: view form integration tests.

Covers:
- Auto-creation of Profile on first visit
- Rendering of phone icon, subject area select
- Required validation for phone/subject_area
- Visa English-exam decision fields (Yes/No) and persistence
"""

from datetime import date

from django.contrib.auth import get_user_model
from django.urls import reverse
import pytest

from profiles.models import Profile

User = get_user_model()


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture
def student_user(db):
    """Create a minimal student user for view/form tests."""
    return User.objects.create_user(
        email="student@example.com",
        password="pass1234",
        role="student",
    )


# -----------------------------------------------------------------------------
# View creates profile basic render
# -----------------------------------------------------------------------------
@pytest.mark.django_db
def test_profile_view_creates_profile_and_renders(client, settings):
    """GET /users/profile/ creates a Profile if missing and renders the page."""
    # Ensure signal doesn't mask the view's get_or_create behavior.
    settings.PROFILES_AUTO_CREATE = False

    student = User.objects.create_user(
        email="vp@example.com",
        password="pass1234",
        role="student",
    )
    client.login(email=student.email, password="pass1234")

    assert not Profile.objects.filter(user=student).exists()

    resp = client.get(reverse("profiles:profile"))
    assert resp.status_code == 200

    # Profile should now exist (created by the view).
    assert Profile.objects.filter(user=student).exists()
    # Smoke check for heading.
    assert b"Complete Your Profile" in resp.content


# -----------------------------------------------------------------------------
# Phone field rendering validation
# -----------------------------------------------------------------------------
@pytest.mark.django_db
def test_profile_page_renders_phone_input_and_icon(client, student_user, settings):
    """Page shows phone input and inline SVG icon."""
    settings.PROFILES_AUTO_CREATE = True  # or False; view creates with defaults.
    client.force_login(student_user)

    resp = client.get(reverse("profiles:profile"))
    assert resp.status_code == 200
    assert b'name="phone"' in resp.content
    # Sanity check that an inline SVG rendered (icon).
    assert b"<svg" in resp.content and b'viewBox="0 -960 960 960"' in resp.content


@pytest.mark.django_db
def test_phone_is_required(client, student_user):
    """POST with empty phone re-renders the page and shows an error."""
    client.force_login(student_user)

    resp = client.post(reverse("profiles:profile"), {"phone": ""})
    assert resp.status_code == 200  # stays on page with errors
    assert (
        b"This field is required" in resp.content or b"Enter a valid phone number" in resp.content
    )


# -----------------------------------------------------------------------------
# Subject area rendering validation
# -----------------------------------------------------------------------------
@pytest.mark.django_db
def test_profile_page_renders_subject_area_select(client, student_user):
    """Page shows Subject Area select with expected options."""
    client.force_login(student_user)

    resp = client.get(reverse("profiles:profile"))
    assert resp.status_code == 200
    assert b'name="subject_area"' in resp.content
    assert b"Arts and Humanities" in resp.content
    assert b"Computing" in resp.content
    assert b"Other" in resp.content


@pytest.mark.django_db
def test_subject_area_required(client, student_user):
    """POST without subject_area is rejected by the form."""
    client.force_login(student_user)

    resp = client.post(
        reverse("profiles:profile"),
        {"phone": "+441234567890"},
    )
    assert resp.status_code == 200
    assert b"This field is required" in resp.content or b"Select a valid choice" in resp.content


# -----------------------------------------------------------------------------
# English exam decision (past five years)
# -----------------------------------------------------------------------------
@pytest.mark.django_db
def test_profile_renders_english_exam_decision(client, student_user):
    """Page shows the required English exam Yes/No decision control."""
    client.force_login(student_user)

    resp = client.get(reverse("profiles:profile"))
    assert resp.status_code == 200
    assert b'name="has_recent_english_exam"' in resp.content
    assert b"Have you taken an English language exam in the past five years?" in resp.content


@pytest.mark.django_db
def test_english_exam_answer_required(client, student_user):
    """POST omitting exam decision re-renders with a required-field error."""
    client.force_login(student_user)

    resp = client.post(
        reverse("profiles:profile"),
        {
            "phone": "+441234567890",
            "subject_area": "computing",
            "requires_uk_student_visa": "True",
            # Missing has_recent_english_exam
        },
    )
    assert resp.status_code == 200
    assert b"This field is required" in resp.content


@pytest.mark.django_db
def test_english_exam_yes_requires_details_form_roundtrip(client, student_user):
    client.force_login(student_user)

    # Use a valid year from the dropdown but make it exactly 5 years + 1 day old
    from datetime import timedelta

    too_old_date = date.today() - timedelta(days=5 * 365 + 2)  # 5 years + 2 days

    resp = client.post(
        reverse("profiles:profile"),
        {
            "phone": "+441234567890",
            "subject_area": "computing",
            "requires_uk_student_visa": "False",
            "has_recent_english_exam": "True",
            "exam_type": "ielts",
            "exam_day": str(too_old_date.day),
            "exam_month": str(too_old_date.month),
            "exam_year": str(too_old_date.year),
        },
    )
    assert resp.status_code == 200
    assert b"Exam date must be within the last five years." in resp.content
