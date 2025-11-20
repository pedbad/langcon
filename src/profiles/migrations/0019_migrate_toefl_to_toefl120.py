from django.db import migrations


def forwards(apps, schema_editor):
    Profile = apps.get_model("profiles", "Profile")
    # Any existing rows using the old "toefl" key become "toefl_120"
    Profile.objects.filter(exam_type="toefl").update(exam_type="toefl_120")


def backwards(apps, schema_editor):
    Profile = apps.get_model("profiles", "Profile")
    Profile.objects.filter(exam_type="toefl_120").update(exam_type="toefl")


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0018_alter_profile_subject_area"),  # or your latest migration
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
