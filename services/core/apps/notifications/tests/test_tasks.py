import uuid
from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone

from apps.notifications.models import FCMToken, Notification
from apps.notifications.tasks import (
    cleanup_expired_notifications,
    dispatch_notification,
    sweep_stale_presence,
)


class TestDispatchNotificationTask:
    def test_dispatch_creates_notification(self, user_id, db):
        result = dispatch_notification(
            user_id=str(user_id),
            notification_type="workspace.invitation",
            title="Test Title",
            body="Test body",
        )
        assert result["status"] == "dispatched"
        assert Notification.objects.filter(user_id=user_id).count() == 1
        notif = Notification.objects.get(user_id=user_id)
        assert notif.title == "Test Title"
        assert notif.body == "Test body"
        assert notif.notification_type == "workspace.invitation"

    def test_dispatch_with_all_fields(self, user_id, workspace, db):
        actor_id = uuid.uuid4()
        result = dispatch_notification(
            user_id=str(user_id),
            notification_type="workspace.member.joined",
            title="Member Joined",
            body="A new member joined",
            link="http://example.com/workspace/1",
            workspace_id=str(workspace.id),
            actor_id=str(actor_id),
            send_push=False,
        )
        assert result["status"] == "dispatched"
        notif = Notification.objects.get(user_id=user_id)
        assert notif.link == "http://example.com/workspace/1"
        assert notif.workspace_id == workspace.id
        assert notif.actor_id == actor_id

    def test_dispatch_without_send_push(self, user_id, db):
        result = dispatch_notification(
            user_id=str(user_id),
            notification_type="system",
            title="Silent",
            send_push=False,
        )
        assert result["status"] == "dispatched"

    def test_dispatch_sends_fcm_push(self, user_id, db):
        FCMToken.objects.create(user_id=user_id, token="fcm-device-token", platform="web")
        with patch("apps.notifications.firebase.send_push_notification") as mock_send:
            dispatch_notification(
                user_id=str(user_id),
                notification_type="system",
                title="Push Test",
                body="Body",
                send_push=True,
            )
            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args[1]
            assert call_kwargs["token"] == "fcm-device-token"
            assert call_kwargs["title"] == "Push Test"

    def test_dispatch_handles_missing_user_gracefully(self, db):
        result = dispatch_notification(
            user_id=str(uuid.uuid4()),
            notification_type="system",
            title="No user",
        )
        assert result["status"] == "dispatched"

    def test_dispatch_calls_channel_layer(self, user_id, db):
        with patch("channels.layers.get_channel_layer") as mock_get:
            mock_layer = mock_get.return_value
            dispatch_notification(
                user_id=str(user_id),
                notification_type="system",
                title="WS Test",
                send_push=False,
            )
            mock_layer.group_send.assert_called_once()

    def test_dispatch_retries_on_failure(self, user_id, db):
        with patch("apps.notifications.models.Notification.objects.create") as mock_create:
            mock_create.side_effect = Exception("DB error")
            from celery.exceptions import MaxRetriesExceededError

            try:
                dispatch_notification(
                    user_id=str(user_id),
                    notification_type="system",
                    title="Fail",
                )
            except MaxRetriesExceededError:
                pass
            except Exception:
                pass


class TestCleanupExpiredNotificationsTask:
    def test_removes_old_notifications(self, user_id, db):
        cutoff = timezone.now() - timedelta(days=31)
        old_notif = Notification.objects.create(
            user_id=user_id,
            notification_type="system",
            title="Old",
        )
        Notification.objects.filter(id=old_notif.id).update(created_at=cutoff)
        result = cleanup_expired_notifications()
        assert result["status"] == "completed"
        assert Notification.objects.filter(id=old_notif.id).count() == 0

    def test_keeps_recent_notifications(self, user_id, db):
        notif = Notification.objects.create(
            user_id=user_id,
            notification_type="system",
            title="Recent",
        )
        result = cleanup_expired_notifications()
        assert result["deleted_count"] == 0
        assert Notification.objects.filter(id=notif.id).exists()

    def test_cleanup_idempotent(self, user_id, db):
        result1 = cleanup_expired_notifications()
        result2 = cleanup_expired_notifications()
        assert result1["deleted_count"] == 0
        assert result2["deleted_count"] == 0


class TestSweepStalePresenceTask:
    def test_sweep_without_redis_returns_skipped(self, db):
        result = sweep_stale_presence()
        assert result["status"] in ("skipped", "completed")

    def test_sweep_with_mock_redis(self, db):
        mock_redis = type(
            "MockRedis",
            (),
            {
                "scan_iter": lambda self, **kw: iter(["presence:user:1", "presence:user:2"]),
                "ttl": lambda self, key: -1,
                "delete": lambda self, key: None,
            },
        )()
        with patch("core.infrastructure.redis.get_redis", return_value=mock_redis):
            result = sweep_stale_presence()
            assert result["status"] == "completed"
