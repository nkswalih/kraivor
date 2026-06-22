import uuid

from django.db import models
from django.utils import timezone

VALID_SCOPES = frozenset({"analysis:read", "analysis:write", "ai:chat", "admin"})
 
 
class APIKey(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="api_keys")
    name = models.CharField(max_length=255)
    key_hash = models.CharField(max_length=255)
    prefix = models.CharField(max_length=20)
    scopes = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked = models.BooleanField(default=False)
 
    class Meta:
        db_table = "identity_api_keys"
 
    def __str__(self) -> str:
        return f"{self.name} ({self.user_id})"
 
    def is_valid(self) -> bool:
        return not (
            self.revoked
            or (
                self.expires_at
                and self.expires_at < timezone.now()
            )
        )