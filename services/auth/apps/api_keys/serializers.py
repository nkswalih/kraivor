"""
apps/api_keys/serializers.py
 
Serializers for the API key endpoints.
 
SECURITY RULE: raw_key appears ONLY in APIKeyCreateResponseSerializer,
attached transiently by the view after create_api_key() returns.
It is never on the model, never in the DB, never in list responses.
"""
 
from __future__ import annotations

from api_keys.models import VALID_SCOPES, APIKey
from rest_framework import serializers


class APIKeyCreateSerializer(serializers.Serializer):
    """Validates POST /api/auth/api-keys/ request body."""
 
    name = serializers.CharField(max_length=255, min_length=1, trim_whitespace=True)
    scopes = serializers.ListField(
        child=serializers.ChoiceField(choices=sorted(VALID_SCOPES)),
        min_length=1,
    )
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
 
    def validate_scopes(self, value: list[str]) -> list[str]:
        return sorted(set(value))
 
 
class APIKeyCreateResponseSerializer(serializers.ModelSerializer):
    """
    Response for POST /api/auth/api-keys/.
 
    Includes raw_key — shown once, then gone.
    """
 
    raw_key = serializers.CharField(read_only=True)
 
    class Meta:
        model = APIKey
        fields = ["id", "name", "prefix", "scopes", "created_at", "expires_at", "raw_key"]
        read_only_fields = fields
 
 
class APIKeyListSerializer(serializers.ModelSerializer):
    """
    Response for GET /api/auth/api-keys/ items.
 
    raw_key intentionally absent.
    prefix is shown so users can identify which key is which
    (same UX as GitHub/OpenAI — you see the first 8 chars).
    """
 
    class Meta:
        model = APIKey
        fields = [
            "id",
            "name",
            "prefix",
            "scopes",
            "created_at",
            "last_used_at",
            "expires_at",
        ]
        read_only_fields = fields