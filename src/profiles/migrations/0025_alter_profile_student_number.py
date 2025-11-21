# src/profiles/migrations/00XX_alter_profile_student_number.py
from django.db import migrations, models


def backfill_student_numbers(apps, schema_editor):
    Profile = apps.get_model("profiles", "Profile")

    # Only touch rows that are missing a student_number (NULL or empty string)
    qs = Profile.objects.filter(student_number__isnull=True) | Profile.objects.filter(
        student_number=""
    )
    qs = qs.order_by("pk")

    for profile in qs:
        # Base candidate: USN000001 style (pad pk to 6 digits)
        candidate = f"USN{profile.pk:06d}"
        base = candidate
        suffix = 1

        # Make sure we don't clash with any existing real student_number
        while Profile.objects.filter(student_number=candidate).exclude(pk=profile.pk).exists():
            candidate = f"{base}-{suffix}"
            suffix += 1

        profile.student_number = candidate
        profile.save(update_fields=["student_number"])


def undo_backfill_student_numbers(apps, schema_editor):
    Profile = apps.get_model("profiles", "Profile")
    # Best-effort rollback: clear synthetic USNs we generated
    Profile.objects.filter(student_number__startswith="USN").update(student_number=None)


class Migration(migrations.Migration):

    dependencies = [
        # 🔴 IMPORTANT: replace this with whatever Django just generated
        # e.g. ("profiles", "0020_profile_student_number")
        ("profiles", "0024_backfill_student_numbers"),
    ]

    operations = [
        migrations.RunPython(backfill_student_numbers, undo_backfill_student_numbers),
        migrations.AlterField(
            model_name="profile",
            name="student_number",
            field=models.CharField(
                max_length=20,
                unique=True,
                help_text="Unique Student Number (USN) or CRSid (up to 20 characters).",
            ),
        ),
    ]
