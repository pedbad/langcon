# src/users/management/commands/seed_students.py
#
# Seed student users from a CSV, safely and predictably.
# - CREATE: password = CSV password > --default-password > unusable (None)
# - UPDATE: names always update; password updates ONLY if CSV provides a password
#           (we IGNORE --default-password during updates to avoid accidental resets)
# - DRY RUN: prints "would create"/"would update" and, if --send-welcome, "would email"
# - EMAILS: when --send-welcome (and not --dry-run), send a welcome email with:
#           email, the temp password (if any), and a password reset link
#
# CSV columns supported:
#   email[,first_name,last_name,password]
#
# Examples:
#   python src/manage.py seed_students data/sample_students.csv --dry-run
#   python src/manage.py seed_students data/sample_students.csv --default-password=ChangeMe123!
#   python src/manage.py seed_students data/update_alice.csv --update --send-welcome \
#       --site-domain=127.0.0.1:8000
#
# Notes:
# - Emails are lowercased and validated; invalid or blank emails are skipped with a warning.
# - Extra CSV columns are ignored.

import csv
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

User = get_user_model()


class Command(BaseCommand):
    help = (
        "Seed student users from a CSV.\n"
        "Columns supported: email[,first_name,last_name,password]\n"
        "Extra CSV columns are ignored safely.\n\n"
        "Examples:\n"
        "  python src/manage.py seed_students students.csv --dry-run\n"
        "  python src/manage.py seed_students students.csv --default-password=ChangeMe123!\n"
        "  python src/manage.py seed_students students.csv --default-password=ChangeMe123!"
        " --update\n"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_path",
            type=str,
            help="Path to CSV file. Must at least include the 'email' column.",
        )
        parser.add_argument(
            "--default-password",
            dest="default_password",
            default=None,
            help="If provided, rows without a password will use this value.",
        )
        parser.add_argument(
            "--update",
            action="store_true",
            help="Update first/last name and password for existing users with the same email.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and report without writing to the database.",
        )
        parser.add_argument(
            "--send-welcome",
            action="store_true",
            help=(
                "Send (or preview) welcome emails to created users and to updates "
                "with new passwords."
            ),
        )
        parser.add_argument(
            "--site-domain",
            default=None,
            help="Domain for reset link (e.g. 127.0.0.1:8000 or app.example.edu). "
            "Required with --send-welcome.",
        )
        parser.add_argument(
            "--use-https",
            action="store_true",
            help="Use https for reset links (default: http).",
        )
        parser.add_argument(
            "--from-email",
            default=None,
            help="Override From: address (defaults to settings.DEFAULT_FROM_EMAIL).",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])
        default_password: str | None = options["default_password"]
        update: bool = options["update"]
        dry_run: bool = options["dry_run"]
        send_welcome: bool = options["send_welcome"]
        site_domain: str | None = options["site_domain"]
        use_https: bool = options["use_https"]
        from_email: str | None = options["from_email"]

        if not csv_path.exists():
            raise CommandError(f"CSV not found: {csv_path}")

        if send_welcome and not site_domain:
            raise CommandError("--site-domain is required when using --send-welcome")

        # --- Pass 1: validate headers ----------------------------------------
        try:
            with csv_path.open(newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []
        except Exception as exc:
            raise CommandError(f"Could not read CSV: {exc}") from exc

        if "email" not in headers:
            raise CommandError("CSV must include an 'email' column.")

        # New safety check: warn if no password column
        if "password" not in headers:
            self.stdout.write(
                self.style.WARNING(
                    "⚠️  CSV has no 'password' column. "
                    "Password updates will be skipped (creates still use --default-password)."
                )
            )

        self.stdout.write(self.style.NOTICE("== seed_students starting =="))
        self.stdout.write(f"File: {csv_path}")
        self.stdout.write(f"Headers: {headers}")
        self.stdout.write(
            f"Options: default_password={'***' if default_password else None}, "
            f"update={update}, dry_run={dry_run}, send_welcome={send_welcome}, "
            f"site_domain={site_domain}, use_https={use_https}"
        )

        created = 0
        updated = 0
        skipped = 0
        invalid = 0
        rows = 0

        # --- Pass 2: process rows --------------------------------------------
        with csv_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows += 1

                # --- sanitize inputs -----------------------------------------
                raw_email = (row.get("email") or "").strip()
                email = raw_email.lower()  # normalize and avoid case-duplicates

                if not email:
                    skipped += 1
                    self.stdout.write(self.style.WARNING(f"[row {rows}] missing email → skip"))
                    continue

                try:
                    validate_email(email)
                except ValidationError:
                    invalid += 1
                    self.stdout.write(
                        self.style.WARNING(f"[row {rows}] invalid email '{raw_email}' → skip")
                    )
                    continue

                first_name = (row.get("first_name") or "").strip()
                last_name = (row.get("last_name") or "").strip()

                # CSV-provided password (may be empty)
                csv_pwd = (row.get("password") or "").strip()

                # CREATE path password choice: CSV > --default > unusable(None)
                chosen_pwd_for_create = csv_pwd or (default_password or "")
                password_arg = chosen_pwd_for_create or None

                # --- upsert logic --------------------------------------------
                try:
                    user = User.objects.get(email=email)

                    if update:
                        changed = False
                        pwd_changed = False

                        # names update if provided and different
                        if first_name and user.first_name != first_name:
                            user.first_name = first_name
                            changed = True
                        if last_name and user.last_name != last_name:
                            user.last_name = last_name
                            changed = True

                        # For UPDATES, only change password if CSV provides one
                        if csv_pwd:
                            user.set_password(csv_pwd)
                            changed = True
                            pwd_changed = True

                        if changed:
                            if dry_run:
                                updated += 1
                                self.stdout.write(
                                    self.style.SUCCESS(f"[row {rows}] would update: {email}")
                                )
                                if send_welcome and pwd_changed:
                                    self.stdout.write(
                                        self.style.HTTP_INFO(f"    would email: {email}")
                                    )
                            else:
                                user.save()
                                updated += 1
                                self.stdout.write(
                                    self.style.SUCCESS(f"[row {rows}] updated: {email}")
                                )
                                if send_welcome and pwd_changed:
                                    self._send_welcome(
                                        user=user,
                                        email=email,
                                        plain_password=csv_pwd,
                                        site_domain=site_domain,
                                        use_https=use_https,
                                        from_email=from_email,
                                        dry_run=False,
                                    )
                        else:
                            skipped += 1
                            self.stdout.write(f"[row {rows}] no changes: {email}")

                    else:
                        skipped += 1
                        self.stdout.write(f"[row {rows}] exists → skip: {email}")

                except User.DoesNotExist:
                    if dry_run:
                        created += 1
                        self.stdout.write(
                            self.style.SUCCESS(f"[row {rows}] would create: {email} (student)")
                        )
                        if send_welcome:
                            self.stdout.write(self.style.HTTP_INFO(f"    would email: {email}"))
                    else:
                        user = User.objects.create_user(
                            email=email,
                            password=password_arg,  # manager handles hashing/unusable
                            role=User.Roles.STUDENT,
                            first_name=first_name,
                            last_name=last_name,
                            is_active=True,
                        )
                        created += 1
                        self.stdout.write(
                            self.style.SUCCESS(f"[row {rows}] created: {email} (student)")
                        )
                        if send_welcome:
                            self._send_welcome(
                                user=user,
                                email=email,
                                plain_password=chosen_pwd_for_create or None,
                                site_domain=site_domain,
                                use_https=use_https,
                                from_email=from_email,
                                dry_run=False,
                            )

        # --- Summary ---------------------------------------------------------
        self.stdout.write(
            self.style.NOTICE(
                f"rows={rows} created={created} updated={updated} "
                f"skipped={skipped} invalid_email={invalid} dry_run={dry_run}"
            )
        )
        self.stdout.write(self.style.SUCCESS("Done."))

    # --- helpers -------------------------------------------------------------

    def _send_welcome(
        self,
        user: User,
        email: str,
        plain_password: str | None,
        site_domain: str,
        use_https: bool,
        from_email: str | None,
        dry_run: bool,
    ):
        """Send a welcome email with login info and a password reset link."""
        scheme = "https" if use_https else "http"
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_path = reverse(
            "users:password_reset_confirm",
            kwargs={"uidb64": uidb64, "token": token},
        )
        reset_url = f"{scheme}://{site_domain}{reset_path}"

        subject = "Welcome — your account details"
        body_lines = [
            "Hello,",
            "",
            "Your account has been created.",
            f"Email: {email}",
            f"Temporary password: {plain_password or '(not set)'}",
            "",
            "For security, please set a new password now:",
            reset_url,
            "",
            "If you weren’t expecting this, you can ignore this message.",
        ]
        body = "\n".join(body_lines)

        if dry_run:
            self.stdout.write(self.style.HTTP_INFO(f"[email] would send to {email}: {subject}"))
            return

        send_mail(
            subject=subject,
            message=body,
            from_email=from_email,
            recipient_list=[email],
            fail_silently=False,
        )
