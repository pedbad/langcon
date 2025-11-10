# src/assessments/tests/test_assessment_access.py
from django.urls import reverse
import pytest

from profiles.models import Profile


@pytest.fixture
def student(db, django_user_model):
    user = django_user_model.objects.create_user(
        email="s@example.com",
        password="pass",
        role="student",
        first_name="Stu",
        last_name="Dent",
    )
    Profile.objects.get_or_create(user=user)
    return user


def test_assessment_redirects_when_profile_incomplete(client, student):
    client.login(email=student.email, password="pass")
    url = reverse("assessments:home")
    resp = client.get(url, follow=True)
    # Should redirect to profile page
    assert resp.resolver_match.namespace == "profiles"
    assert resp.resolver_match.url_name == "profile"


def test_assessment_allowed_when_profile_complete(client, student):
    prof = student.profile
    # minimal completion flags to satisfy is_complete()
    prof.phone = "+44 7777 777777"
    prof.subject_area = "other"
    prof.requires_uk_student_visa = True
    prof.academic_integrity_confirmed = True
    prof.has_recent_english_exam = False
    prof.full_clean()
    prof.save()

    client.login(email=student.email, password="pass")
    url = reverse("assessments:home")
    resp = client.get(url)
    assert resp.status_code == 200
    assert b"Assessment" in resp.content


def test_profile_page_shows_begin_assessment_cta_when_complete(client, student):
    prof = student.profile
    prof.phone = "+44 7777 777777"
    prof.subject_area = "other"
    prof.requires_uk_student_visa = True
    prof.academic_integrity_confirmed = True
    prof.has_recent_english_exam = False
    prof.full_clean()
    prof.save()

    client.login(email=student.email, password="pass")
    resp = client.get(reverse("profiles:profile"))
    assert resp.status_code == 200
    assert b"Begin your assessment" in resp.content
