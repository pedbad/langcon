# Generated manually to clear 'other' subject areas so the placeholder shows.
from django.db import migrations


def clear_other_to_blank(apps, schema_editor):
    Profile = apps.get_model("profiles", "Profile")
    Profile.objects.filter(subject_area="other").update(subject_area="")


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0016_alter_profile_subject_area"),
    ]

    operations = [
        migrations.RunPython(clear_other_to_blank, migrations.RunPython.noop),
    ]
