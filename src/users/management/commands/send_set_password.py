# src/users/management/commands/send_set_password.py
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from users.utils import send_set_password

User = get_user_model()


class Command(BaseCommand):
    help = "Send a set-password email (via password reset flow) to a user."

    def add_arguments(self, parser):
        parser.add_argument("email", help="Target user email.")
        parser.add_argument("--domain", default=None, help="Domain override, e.g. localhost:8000")
        parser.add_argument("--https", action="store_true", help="Use https in links")
        parser.add_argument("--from-email", default=None, help="From email override")

    def handle(self, *args, **opts):
        email = opts["email"]
        try:
            user = User.objects.get(email__iexact=email, is_active=True)
        except User.DoesNotExist:
            raise CommandError(f"Active user with email {email!r} does not exist.")

        domain = opts["domain"] or getattr(settings, "SITE_DOMAIN", "localhost:8000")
        use_https = opts["https"]
        from_email = opts["from_email"] or getattr(settings, "DEFAULT_FROM_EMAIL", None)

        ok = send_set_password(
            user.email, domain=domain, use_https=use_https, from_email=from_email
        )
        if not ok:
            raise CommandError("Password reset form was invalid; email not sent.")
        self.stdout.write(
            self.style.SUCCESS(f"Invite sent to {user.email} (domain={domain}, https={use_https})")
        )


# usage
# python src/manage.py send_set_password student_1@cam.ac.uk --domain=127.0.0.1:8000
# check tmp_emails/ for a new file
