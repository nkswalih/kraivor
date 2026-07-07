# Generated manually — adds metadata JSONField to Notification model

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="metadata",
            field=models.JSONField(blank=True, default=dict, null=True),
        ),
    ]
