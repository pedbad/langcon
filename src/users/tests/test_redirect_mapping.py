# src/users/tests/test_redirect_mapping.py
#
# Purpose: Prove that USERS_ROLE_REDIRECTS from settings drives the post-login destination.
# This ensures the users app stays decoupled from other apps by using URL names only.

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
import pytest

User = get_user_model()


@pytest.mark.django_db
@override_settings(USERS_ROLE_REDIRECTS={"student": "users:teacher_home"})  # intentionally remap
def test_login_uses_settings_driven_role_mapping(client):
    """
    GIVEN we override USERS_ROLE_REDIRECTS to point 'student' to 'users:teacher_home'
    WHEN a student logs in
    THEN the initial redirect Location should be 'users:teacher_home'
    """
    user = User.objects.create_user(email="maptest@ex.com", password="pass1234", role="student")
    resp = client.post(
        reverse("users:login"),
        {"username": user.email, "password": "pass1234"},
        follow=False,
    )

    assert resp.status_code == 302
    assert resp["Location"].endswith(reverse("users:teacher_home"))
