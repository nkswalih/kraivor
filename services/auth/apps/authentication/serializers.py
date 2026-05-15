from authentication.models import RefreshToken
from rest_framework import serializers

# ── KRV-011 ───────────────────────────────────────────────────────────────────

class SignInIdentifySerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class SignInPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)
    device_id = serializers.CharField(required=False, allow_blank=True)


class OTPSendSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class OTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    otp_code = serializers.CharField(max_length=6, min_length=6, required=True)
    device_id = serializers.CharField(required=False, allow_blank=True)


# ── KRV-014 ───────────────────────────────────────────────────────────────────

class SessionSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for active session display.
    GET /api/auth/sessions/

    Never exposes token_hash or any raw credential.
    is_current is True when the session's device_id matches
    the device_id extracted from the caller's JWT payload.
    """

    session_id = serializers.UUIDField(source="id", read_only=True)
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = RefreshToken
        fields = [
            "session_id",
            "device_name",
            "device_type",
            "ip_address",
            "last_used_at",
            "created_at",
            "is_current",
        ]
        read_only_fields = fields

    def get_is_current(self, obj) -> bool:
        current_device_id = self.context.get("current_device_id")
        if not current_device_id:
            return False
        return str(obj.device_id) == str(current_device_id)