from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django.urls import reverse
import pytest

from profiles.models import Profile

User = get_user_model()


@pytest.mark.django_db
def test_register_requires_staff_or_redirects_to_login(client):
    """
    Anonymous visitors cannot access /users/register/.
    They are redirected to login by AdminRequiredMixin.
    """
    url = reverse("users:register")
    resp = client.get(url)
    assert resp.status_code in (302, 303)
    assert reverse("users:login") in resp.headers.get("Location", "")


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_staff_can_register_user_and_invite_is_sent(client, django_capture_on_commit_callbacks):
    """
    GIVEN a logged-in staff/admin user
    WHEN they submit the register form
    THEN a new user is created with an unusable password,
         an invite email is sent (via post_save signal on_commit),
         and we redirect to the new user's role landing page.
    """
    # Log in as staff/admin
    admin = User.objects.create_user(
        email="admin@example.com",
        password="adminpass",
        is_active=True,
        is_staff=True,
        role="admin",
    )
    client.force_login(admin)

    url = reverse("users:register")
    form_data = {
        "email": "newstudent@example.com",
        "first_name": "New",
        "last_name": "Student",
        "student_number": "USN-1001",
        "password1": "pass1234ABC!",
        "password2": "pass1234ABC!",
        "role": "student",
    }

    # Execute on_commit callbacks that the signal registers
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        resp = client.post(url, data=form_data, follow=True)

    # We now keep the creator (admin) on their own dashboard
    assert resp.redirect_chain
    assert resp.resolver_match.view_name == "assessor:teacher_home"

    # New user exists and has an unusable password (invite flow)
    new_user = User.objects.get(email="newstudent@example.com")
    assert new_user.first_name == "New"
    assert new_user.last_name == "Student"
    assert not new_user.has_usable_password()
    assert Profile.objects.get(user=new_user).student_number == "USN-1001"

    # Exactly one invite email was sent by the signal
    assert len(callbacks) >= 1  # at least one callback was scheduled
    assert len(mail.outbox) == 1
    body = (
        mail.outbox[0].alternatives[0][0] if mail.outbox[0].alternatives else mail.outbox[0].body
    ).lower()
    assert "/users/reset/" in body


@pytest.mark.django_db
def test_register_rejects_duplicate_student_number(client):
    admin = User.objects.create_user(
        email="admin2@example.com",
        password="adminpass",
        is_active=True,
        is_staff=True,
        role="admin",
    )
    existing_user = User.objects.create_user(
        email="existing@example.com",
        password="pass1234ABC!",
        role="student",
    )
    Profile.objects.create(user=existing_user, phone="", student_number="USN-2000")

    client.force_login(admin)
    resp = client.post(
        reverse("users:register"),
        data={
            "email": "dupe@example.com",
            "first_name": "Dupe",
            "last_name": "User",
            "student_number": "USN-2000",
            "password1": "pass1234ABC!",
            "password2": "pass1234ABC!",
            "role": "student",
        },
    )

    assert resp.status_code == 200
    assert b"already in use" in resp.content
    assert not User.objects.filter(email="dupe@example.com").exists()


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_teacher_can_register_student(client, django_capture_on_commit_callbacks):
    teacher = User.objects.create_user(
        email="teacher@example.com",
        password="teachpass",
        is_active=True,
        is_staff=True,
        role="teacher",
    )
    client.force_login(teacher)

    with django_capture_on_commit_callbacks(execute=True):
        resp = client.post(
            reverse("users:register"),
            data={
                "email": "teachmade@example.com",
                "first_name": "Teach",
                "last_name": "Made",
                "student_number": "USN-3000",
                "password1": "pass1234ABC!",
                "password2": "pass1234ABC!",
                "role": "student",
            },
            follow=True,
        )

    assert resp.redirect_chain
    assert resp.resolver_match.view_name == "assessor:teacher_home"
    created = User.objects.get(email="teachmade@example.com")
    assert created.role == User.Roles.STUDENT
    assert Profile.objects.get(user=created).student_number == "USN-3000"


@pytest.mark.django_db
def test_teacher_cannot_register_admin_role(client):
    teacher = User.objects.create_user(
        email="teacher2@example.com",
        password="teachpass",
        is_active=True,
        is_staff=True,
        role="teacher",
    )
    client.force_login(teacher)

    resp = client.post(
        reverse("users:register"),
        data={
            "email": "shouldfail@example.com",
            "first_name": "Should",
            "last_name": "Fail",
            "student_number": "USN-3001",
            "password1": "pass1234ABC!",
            "password2": "pass1234ABC!",
            "role": "admin",
        },
    )

    assert resp.status_code == 200
    assert b"Select a valid choice" in resp.content
    assert not User.objects.filter(email="shouldfail@example.com").exists()
