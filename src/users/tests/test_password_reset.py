# src/users/tests/test_password_reset.py
#
# Purpose: Verify that the password-reset start page renders and
# that posting a user's email queues an email (using Django's locmem backend in tests).

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django.urls import reverse
import pytest

User = get_user_model()


@pytest.mark.django_db
def test_password_reset_start_renders(client):
    """
    GET /users/password-reset/ should render the form successfully.
    """
    url = reverse("users:password_reset")
    resp = client.get(url)
    assert resp.status_code == 200
    # Rendered form contains the email field
    assert b"email" in resp.content


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_password_reset_sends_email(client):
    """
    GIVEN a registered user
    WHEN they request a password reset
    THEN an email is sent and we redirect to the 'done' page.
    """
    User.objects.create_user(email="resetme@example.com", password="oldpass123", role="student")

    url = reverse("users:password_reset")
    resp = client.post(url, {"email": "resetme@example.com"}, follow=True)

    # Should redirect to 'done' page
    assert resp.redirect_chain
    assert resp.resolver_match.view_name == "users:password_reset_done"

    # Using locmem backend, emails are captured in django.core.mail.outbox
    assert len(mail.outbox) == 1
    message = mail.outbox[0]

    # Subject can vary slightly depending on template wording.
    subj = message.subject.lower()
    assert ("password reset" in subj) or ("reset your password" in subj), subj

    # Body should include a reset link containing uid/token
    assert "reset/" in message.body
