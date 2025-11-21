from django.db import migrations


def forwards(apps, schema_editor):
    Profile = apps.get_model("profiles", "Profile")

    # Only touch rows that are missing a student_number
    qs = Profile.objects.filter(student_number__isnull=True) | Profile.objects.filter(
        student_number=""
    )
    qs = qs.order_by("pk")

    for profile in qs:
        # USN000001 style, padded to 6 digits (adjust if you prefer)
        candidate = f"USN{profile.pk:06d}"

        # Ensure uniqueness in case something weird already exists
        suffix = 1
        base = candidate
        while Profile.objects.filter(student_number=candidate).exclude(pk=profile.pk).exists():
            candidate = f"{base}-{suffix}"
            suffix += 1

        profile.student_number = candidate
        profile.save(update_fields=["student_number"])


def backwards(apps, schema_editor):
    Profile = apps.get_model("profiles", "Profile")
    # Rollback: drop back to NULL for synthetic numbers
    Profile.objects.filter(student_number__startswith="USN").update(student_number=None)


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0023_profile_student_number"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
