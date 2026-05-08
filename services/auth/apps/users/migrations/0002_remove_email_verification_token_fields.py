# Generated for KRV-010 — Email Verification
# Removes legacy plaintext token fields from auth_users.
# Verification is now handled via stateless signed JWTs (no DB storage needed).

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="user",
            name="email_verification_token",
        ),
        migrations.RemoveField(
            model_name="user",
            name="email_verification_expires_at",
        ),
    ]
