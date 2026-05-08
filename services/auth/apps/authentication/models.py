import uuid

from django.db import models
from django.utils import timezone


class OAuthIdentity(models.Model):
    PROVIDER_CHOICES = [
        ('github', 'GitHub'),
        ('google', 'Google'),
        ('apple', 'Apple'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='oauth_identities')
    provider = models.CharField(max_length=50, choices=PROVIDER_CHOICES)
    provider_user_id = models.CharField(max_length=255)
    provider_email = models.EmailField(null=True, blank=True)
    access_token_encrypted = models.TextField(null=True, blank=True)
    refresh_token_encrypted = models.TextField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    raw_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'auth_oauth_identities'
        unique_together = [('provider', 'provider_user_id')]
        indexes = [
            models.Index(fields=['provider', 'provider_user_id']),
            models.Index(fields=['user', 'provider']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.provider}"


class RefreshToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='refresh_tokens')
    token_hash = models.CharField(max_length=255)
    device_id = models.CharField(max_length=255, null=True, blank=True)
    device_name = models.CharField(max_length=255, null=True, blank=True)
    device_type = models.CharField(max_length=50, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    expires_at = models.DateTimeField()
    revoked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'auth_refresh_tokens'
        indexes = [
            models.Index(fields=['user', 'device_id']),
            models.Index(fields=['token_hash']),
        ]

    def is_valid(self):
        return not self.revoked and self.expires_at > timezone.now()