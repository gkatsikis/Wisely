from django.db import migrations

LICENSE_TYPES = [
    "lcsw", "lmsw", "lmft", "lpc", "lmhc",
    "psychologist", "psychiatrist", "lpcc", "cadc",
]


def seed(apps, schema_editor):
    License = apps.get_model("clinicians", "License")
    for license_type in LICENSE_TYPES:
        License.objects.get_or_create(license_type=license_type)


def unseed(apps, schema_editor):
    License = apps.get_model("clinicians", "License")
    License.objects.filter(license_type__in=LICENSE_TYPES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("clinicians", "0003_clinician_video_bio_url"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
