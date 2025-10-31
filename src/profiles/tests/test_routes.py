# src/profiles/tests/test_routes.py
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
import pytest

User = get_user_model()


@pytest.mark.django_db
def test_profile_requires_login(client):
    url = reverse("profiles:profile")
    resp = client.get(url)
    assert resp.status_code in (302, 301)
    assert settings.LOGIN_URL in resp.headers.get("Location", "")


@pytest.mark.django_db
def test_student_can_access(client):
    student = User.objects.create_user(
        email="stud@example.com",
        password="pass1234",
        role="student",
    )
    client.login(email=student.email, password="pass1234")
    url = reverse("profiles:profile")
    resp = client.get(url)
    assert resp.status_code == 200
    assert b"Complete Your Profile" in resp.content


@pytest.mark.django_db
def test_non_student_forbidden(client):
    teacher = User.objects.create_user(
        email="teach@example.com",
        password="pass1234",
        role="teacher",
    )
    client.login(email=teacher.email, password="pass1234")
    url = reverse("profiles:profile")
    resp = client.get(url)
    assert resp.status_code == 403
