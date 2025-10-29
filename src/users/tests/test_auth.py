# src/users/tests/test_auth.py
#
# Purpose: End-to-end tests for login/logout and role-based redirects.

from django.contrib.auth import get_user_model
from django.urls import reverse
import pytest

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected_name",
    [
        # Each tuple = (role we assign, final view name we expect after login)
        ("student", "users:student_home"),
        ("teacher", "users:teacher_home"),
        ("admin", "users:admin_home"),
    ],
)
def test_login_redirects_by_role(client, role, expected_name):
    """
    GIVEN a user with a specific role
    WHEN they submit valid credentials to the login view
    THEN they should end up on the role-appropriate landing page
    """
    user = User.objects.create_user(email=f"{role}@ex.com", password="pass1234", role=role)

    login_url = reverse("users:login")
    resp = client.post(
        login_url,
        # Django's auth forms expect "username" (mapped to USERNAME_FIELD, which is email)
        {"username": user.email, "password": "pass1234"},
        follow=True,  # follow redirects to the final destination
    )

    # We should have been redirected at least once
    assert resp.redirect_chain
    # Final resolved view name should match the role's landing page
    assert resp.resolver_match.view_name == expected_name


@pytest.mark.django_db
def test_login_with_wrong_password_shows_error(client):
    """
    GIVEN a user exists
    WHEN they submit a wrong password
    THEN the login view should re-render with errors and NOT redirect
    """
    user = User.objects.create_user(email="wrong@ex.com", password="pass1234", role="student")

    login_url = reverse("users:login")
    resp = client.post(
        login_url, {"username": user.email, "password": "not-the-password"}, follow=True
    )

    # No redirect; we remain on the login page (HTTP 200)
    assert not resp.redirect_chain
    assert resp.status_code == 200
    # Ensure something sensible rendered
    assert b"form" in resp.content


@pytest.mark.django_db
def test_logout_renders_logged_out_page(client):
    """
    GIVEN an anonymous (or authenticated) session
    WHEN we POST /users/logout/
    THEN we render the logged_out template (status 200), not a redirect.
    """
    resp = client.post(reverse("users:logout"))
    assert resp.status_code == 200
    assert b"logged out" in resp.content.lower() or b"signed out" in resp.content.lower()
