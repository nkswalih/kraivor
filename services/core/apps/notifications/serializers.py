"""
DRF serializers for notifications and FCM token management.
"""

from rest_framework import serializers

from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "user_id",
            "workspace",
            "notification_type",
            "title",
            "body",
            "link",
            "actor_id",
            "read_at",
            "created_at",
            "expires_at",
        ]
        read_only_fields = ["id", "user_id", "created_at"]


class NotificationMarkReadSerializer(serializers.Serializer):
    notification_id = serializers.UUIDField(required=False)


class FCMTokenSerializer(serializers.Serializer):
    token = serializers.CharField()
    platform = serializers.ChoiceField(choices=["ios", "android", "web"])
