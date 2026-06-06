import uuid
from datetime import timedelta

from django.utils import timezone

from apps.notifications.models import FCMToken, Notification


class TestNotificationModel:
    def test_create_notification(self, db):
        user_id = uuid.uuid4()
        notif = Notification.objects.create(
            user_id=user_id,
            notification_type="workspace.invitation",
            title="Welcome!",
            body="You are invited to join workspace.",
        )
        assert notif.id is not None
        assert notif.user_id == user_id
        assert str(notif) == "[workspace.invitation] Welcome!"
        assert notif.is_read is False

    def test_notification_read_property(self, notification):
        assert notification.is_read is False
        notification.read_at = timezone.now()
        notification.save(update_fields=["read_at"])
        notification.refresh_from_db()
        assert notification.is_read is True

    def test_notification_default_values(self, db):
        user_id = uuid.uuid4()
        notif = Notification.objects.create(
            user_id=user_id,
            notification_type="system",
            title="System Notification",
        )
        assert notif.body == ""
        assert notif.link == ""
        assert notif.read_at is None
        assert notif.actor_id is None
        assert notif.workspace is None
        assert notif.expires_at is None

    def test_notification_optional_fields(self, db, workspace):
        user_id = uuid.uuid4()
        notif = Notification.objects.create(
            user_id=user_id,
            workspace=workspace,
            notification_type="workspace.member.joined",
            title="Member Joined",
            actor_id=uuid.uuid4(),
            expires_at=timezone.now() + timedelta(days=7),
        )
        assert notif.workspace == workspace
        assert notif.actor_id is not None
        assert notif.expires_at is not None

    def test_notification_ordering(self, user_id, db):
        notif1 = Notification.objects.create(
            user_id=user_id,
            notification_type="system",
            title="First",
        )
        notif2 = Notification.objects.create(
            user_id=user_id,
            notification_type="system",
            title="Second",
        )
        qs = Notification.objects.filter(user_id=user_id).order_by("-created_at")
        assert list(qs) == [notif2, notif1]

    def test_filter_by_user(self, user_id, other_user_id, db):
        Notification.objects.create(user_id=user_id, notification_type="system", title="Mine")
        Notification.objects.create(user_id=other_user_id, notification_type="system", title="Theirs")
        assert Notification.objects.filter(user_id=user_id).count() == 1
        assert Notification.objects.count() == 2

    def test_filter_unread(self, user_id, db):
        Notification.objects.create(user_id=user_id, notification_type="system", title="Unread 1")
        n2 = Notification.objects.create(user_id=user_id, notification_type="system", title="Unread 2")
        n3 = Notification.objects.create(user_id=user_id, notification_type="system", title="Read")
        n3.read_at = timezone.now()
        n3.save(update_fields=["read_at"])
        unread = Notification.objects.filter(user_id=user_id, read_at__isnull=True)
        assert unread.count() == 2

    def test_notification_type_choices(self, db):
        user_id = uuid.uuid4()
        for ntype, _ in Notification.NotificationType.choices:
            notif = Notification.objects.create(
                user_id=user_id,
                notification_type=ntype,
                title=f"Test {ntype}",
            )
            assert notif.notification_type == ntype

    def test_delete_cascade_workspace(self, workspace, db):
        user_id = uuid.uuid4()
        Notification.objects.create(
            user_id=user_id,
            workspace=workspace,
            notification_type="system",
            title="Test",
        )
        workspace.delete()
        assert Notification.objects.count() == 0

    def test_indexes_exist(self):
        from django.db import connection
        indexes = connection.introspection.get_constraints(connection.cursor(), Notification._meta.db_table)
        assert any("user_id" in str(idx) for idx in indexes)


class TestFCMTokenModel:
    def test_create_fcm_token(self, user_id, db):
        token = FCMToken.objects.create(
            user_id=user_id,
            token="device-token-abc",
            platform="android",
        )
        assert token.id is not None
        assert str(token) == f"{user_id} (android)"
        assert token.platform == "android"

    def test_unique_together_user_token(self, user_id, db):
        FCMToken.objects.create(
            user_id=user_id,
            token="duplicate-token",
            platform="web",
        )
        from django.db import IntegrityError
        import pytest
        with pytest.raises(IntegrityError):
            FCMToken.objects.create(
                user_id=user_id,
                token="duplicate-token",
                platform="ios",
            )

    def test_multiple_tokens_per_user(self, user_id, db):
        FCMToken.objects.create(user_id=user_id, token="token-1", platform="web")
        FCMToken.objects.create(user_id=user_id, token="token-2", platform="android")
        assert FCMToken.objects.filter(user_id=user_id).count() == 2

    def test_token_updated_at_changes(self, user_id, db):
        import time
        token = FCMToken.objects.create(
            user_id=user_id,
            token="test-token",
            platform="web",
        )
        original_updated = token.updated_at
        time.sleep(0.001)
        token.platform = "ios"
        token.save()
        token.refresh_from_db()
        assert token.updated_at > original_updated

    def test_platform_choices(self, user_id, db):
        for platform_code in ["ios", "android", "web"]:
            token = FCMToken.objects.create(
                user_id=user_id,
                token=f"token-{platform_code}",
                platform=platform_code,
            )
            assert token.platform == platform_code

    def test_different_users_same_token(self, user_id, other_user_id, db):
        FCMToken.objects.create(user_id=user_id, token="shared-token", platform="web")
        FCMToken.objects.create(user_id=other_user_id, token="shared-token", platform="web")
        assert FCMToken.objects.filter(token="shared-token").count() == 2
