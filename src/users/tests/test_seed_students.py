# src/users/tests/test_seed_students.py
#
# Purpose:
#   End-to-end tests for the `seed_students` management command.
#   We verify three core behaviors:
#     1) --dry-run: previews but does NOT write to the DB
#     2) normal run with --default-password: creates students and sets usable passwords
#     3) --update: updates names and passwords for existing emails
#
# Notes:
#   - We use the repo's sample CSV at: data/sample_students.csv (checked into git for dev)
#   - For the update test we generate a tiny one-off CSV in a temp directory.

import csv
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
import pytest

from profiles.models import Profile

User = get_user_model()


def _project_data_csv(name: str) -> Path:
    """
    Resolve a CSV path inside the repo-level `data/` directory.

    settings.BASE_DIR in this project points to the `src/` folder,
    so the repository root is BASE_DIR.parent, and the CSV lives at:
      <repo-root>/data/<name>
    """
    return Path(settings.BASE_DIR).parent / "data" / name


@pytest.mark.django_db
def test_seed_students_dry_run_uses_sample_csv_and_writes_nothing():
    """
    GIVEN the sample CSV (3 rows)
    WHEN we run the command with --dry-run
    THEN no users are created in the DB.
    """
    csv_path = _project_data_csv("sample_students.csv")

    # Sanity: make sure the sample file exists in the repo
    assert csv_path.exists(), f"Expected test sample CSV at {csv_path}"

    # Execute with --dry-run and a default password (should be ignored in dry-run)
    call_command(
        "seed_students",
        str(csv_path),
        "--default-password=ChangeMe123!",
        "--dry-run",
    )

    # No users are created during a dry run
    assert User.objects.count() == 0


@pytest.mark.django_db
def test_seed_students_creates_users_with_default_password_from_sample_csv():
    """
    GIVEN the sample CSV
    WHEN we run without --dry-run and WITH --default-password
    THEN users for each CSV row are created as students with the given default password.
    """
    csv_path = _project_data_csv("sample_students.csv")
    default_pwd = "ChangeMe123!"

    # Build expected emails directly from the CSV to avoid test drift
    expected_rows: dict[str, dict[str, str]] = {}
    with csv_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            email = (row.get("email") or "").strip().lower()
            if not email:
                continue
            expected_rows[email] = {
                "first_name": (row.get("first_name") or "").strip(),
                "last_name": (row.get("last_name") or "").strip(),
                "student_number": (row.get("student_number") or "").strip(),
            }
    expected_emails = set(expected_rows.keys())

    call_command("seed_students", str(csv_path), f"--default-password={default_pwd}")

    got_emails = set(User.objects.values_list("email", flat=True))
    assert expected_emails == got_emails

    for u in User.objects.all():
        assert u.role == User.Roles.STUDENT
        assert u.is_active is True
        assert u.check_password(default_pwd)
        expected = expected_rows[u.email]
        assert u.first_name == expected["first_name"]
        assert u.last_name == expected["last_name"]
        assert Profile.objects.get(user=u).student_number == expected["student_number"]


@pytest.mark.django_db
def test_seed_students_update_changes_names_and_password(tmp_path):
    """
    GIVEN an existing user (seeded earlier)
    WHEN we provide a new CSV row with corrected names and a new password AND pass --update
    THEN the user's names are updated and the password is changed.
    """
    # 1) Create a base user (as if seeded already)
    u = User.objects.create_user(
        email="update_me@example.com",
        password="OldPass!1",
        role=User.Roles.STUDENT,
        first_name="Old",
        last_name="Name",
        is_active=True,
    )
    assert u.check_password("OldPass!1")
    Profile.objects.create(user=u, phone="", student_number="300000001")

    # 2) Build a one-row CSV that updates first/last and sets a new password
    csv_path = tmp_path / "update.csv"
    fieldnames = ["email", "first_name", "last_name", "student_number", "password"]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerow(
            {
                "email": "update_me@example.com",
                "first_name": "NewFirst",
                "last_name": "NewLast",
                "student_number": "300000999",
                "password": "NewPass!2",
            }
        )

    # 3) Run with --update so it modifies the existing record
    call_command(
        "seed_students",
        str(csv_path),
        "--update",
        "--default-password=IGNORED_IF_ROW_HAS_PASSWORD",
    )

    # 4) Verify updates
    u.refresh_from_db()
    assert u.first_name == "NewFirst"
    assert u.last_name == "NewLast"
    assert u.check_password("NewPass!2")
    assert Profile.objects.get(user=u).student_number == "300000999"


@pytest.mark.django_db
def test_seed_students_requires_student_number_header(tmp_path):
    csv_path = tmp_path / "missing_usn.csv"
    fieldnames = ["email", "first_name", "last_name"]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerow(
            {
                "email": "no_usn@example.com",
                "first_name": "No",
                "last_name": "Usn",
            }
        )

    with pytest.raises(CommandError, match="student_number"):
        call_command("seed_students", str(csv_path), "--dry-run")
