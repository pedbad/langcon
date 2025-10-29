# users/utils.py
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .constants import PWD_RESET_TPLS
from .forms_invite import InvitePasswordResetForm


def send_set_password(email, *, domain="localhost:8000", use_https=False, from_email=None):
    form = InvitePasswordResetForm({"email": email})
    if form.is_valid():
        form.save(
            from_email=from_email or getattr(settings, "DEFAULT_FROM_EMAIL", None),
            use_https=use_https,
            domain_override=domain,
            email_template_name=PWD_RESET_TPLS["email_txt"],
            subject_template_name=PWD_RESET_TPLS["subject"],
            html_email_template_name=PWD_RESET_TPLS.get("email_html"),
        )
        # Return True only if at least one user matched
        return True
    return False


def get_domain_and_scheme(request=None):
    """
    Returns (domain, use_https).
    - If request is provided: prefer request host + request.is_secure().
    - Else: fall back to settings.SITE_DOMAIN and assume https=False.
    """
    if request is not None:
        domain = getattr(settings, "SITE_DOMAIN", None) or request.get_host()
        use_https = request.is_secure()
        return domain, use_https

    # No request context (e.g., management command)
    domain = getattr(settings, "SITE_DOMAIN", "") or "localhost"
    return domain, False


def send_invite_email(user, *, domain: str, use_https: bool):
    """
    Build a password-set (reset) link for the user and send an invite email.
    Uses your existing HTML template; falls back to plain text body.
    """
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    path = reverse("users:password_reset_confirm", kwargs={"uidb64": uidb64, "token": token})
    scheme = "https" if use_https else "http"
    reset_url = f"{scheme}://{domain}{path}"

    context = {
        "user": user,
        "reset_url": reset_url,
        "site_name": getattr(settings, "SITE_NAME", "LangCen Base"),
        "domain": domain,
        "protocol": scheme,
        "uidb64": uidb64,
        "uid": uidb64,
        "token": token,
    }

    subject = "Set your password"
    # Plain-text fallback (kept short)
    text_body = (
        f"You’ve been invited to join {context['site_name']}.\nSet your password: {reset_url}\n"
    )

    html_body = render_to_string("users/registration/password_reset_email.html", context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com"),
        to=[user.email],
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send()
