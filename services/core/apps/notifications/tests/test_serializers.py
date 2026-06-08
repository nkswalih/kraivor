import uuid

import pytest

from apps.notifications.models import Notification
from apps.notifications.serializers import (
    FCMTokenSerializer,
    NotificationMarkReadSerializer,
    NotificationSerializer,
)


class TestNotificationSerializer:
    def test_serialize_notification(self, notification):
        serializer = NotificationSerializer(notification)
        data = serializer.data
        assert data["id"] == str(notification.id)
        assert data["user_id"] == str(notification.user_id)
        assert data["notification_type"] == "workspace.invitation"
        assert data["title"] == "Test Notification"
        assert data["body"] == "This is a test notification body"
        assert data["link"] == "http://example.com"
        assert data["read_at"] is None
        assert "created_at" in data

    def test_serialize_read_notification(self, user_id, db):
        from django.utils import timezone

        notif = Notification.objects.create(
            user_id=user_id,
            notification_type="system",
            title="Read Test",
            read_at=timezone.now(),
        )
        serializer = NotificationSerializer(notif)
        assert serializer.data["read_at"] is not None

    def test_deserialize_notification_read_only_fields(self, user_id, db):
        payload = {
            "user_id": str(uuid.uuid4()),
            "notification_type": "system",
            "title": "Test",
        }
        serializer = NotificationSerializer(data=payload)
        assert serializer.is_valid() is True
        assert "user_id" not in serializer.validated_data
        assert "id" not in serializer.validated_data

    def test_serializer_reads_type_choice(self, user_id, db):
        notif = Notification.objects.create(
            user_id=user_id,
            notification_type="analysis.completed",
            title="Analysis Done",
        )
        serializer = NotificationSerializer(notif)
        assert serializer.data["notification_type"] == "analysis.completed"

    @pytest.mark.parametrize("field", ["id", "user_id", "created_at"])
    def test_read_only_fields(self, notification, field):
        serializer = NotificationSerializer(notification)
        assert field in serializer.get_fields()
        assert serializer.get_fields()[field].read_only is True

    def test_serializer_includes_workspace(self, notification, workspace):
        notification.workspace = workspace
        notification.save(update_fields=["workspace"])
        serializer = NotificationSerializer(notification)
        assert serializer.data["workspace"] is not None


class TestNotificationMarkReadSerializer:
    def test_valid_with_notification_id(self):
        serializer = NotificationMarkReadSerializer(data={"notification_id": str(uuid.uuid4())})
        assert serializer.is_valid() is True

    def test_valid_without_notification_id(self):
        serializer = NotificationMarkReadSerializer(data={})
        assert serializer.is_valid() is True

    def test_invalid_notification_id_type(self):
        serializer = NotificationMarkReadSerializer(data={"notification_id": "not-a-uuid"})
        assert serializer.is_valid() is False


class TestFCMTokenSerializer:
    def test_valid_token(self):
        serializer = FCMTokenSerializer(
            data={
                "token": "valid-fcm-token-123",
                "platform": "android",
            }
        )
        assert serializer.is_valid() is True

    def test_missing_token(self):
        serializer = FCMTokenSerializer(data={"platform": "ios"})
        assert serializer.is_valid() is False

    def test_invalid_platform(self):
        serializer = FCMTokenSerializer(
            data={
                "token": "abc",
                "platform": "windows",
            }
        )
        assert serializer.is_valid() is False

    @pytest.mark.parametrize("platform", ["ios", "android", "web"])
    def test_valid_platforms(self, platform):
        serializer = FCMTokenSerializer(
            data={
                "token": "abc",
                "platform": platform,
            }
        )
        assert serializer.is_valid() is True

    def test_empty_token(self):
        serializer = FCMTokenSerializer(
            data={
                "token": "",
                "platform": "web",
            }
        )
        assert serializer.is_valid() is False
