import uuid

from rest_framework import status

from apps.notifications.models import FCMToken, Notification
from apps.notifications.views import FCMTokenViewSet, NotificationViewSet


def _build_request(method, path, user_id=None, data=None):
    from rest_framework.test import APIRequestFactory

    factory = APIRequestFactory()
    if data is not None:
        request = getattr(factory, method)(path, data, format="json")
    else:
        request = getattr(factory, method)(path)
    if user_id:
        request.user_id = user_id
    return request


class TestNotificationViewSetList:
    def test_returns_user_notifications(self, notification, user_id, db):
        request = _build_request("get", "/api/notifications/", user_id=user_id)
        view = NotificationViewSet.as_view(actions={"get": "list"})
        response = view(request)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["id"] == str(notification.id)

    def test_returns_empty_for_no_notifications(self, db):
        request = _build_request("get", "/api/notifications/", user_id=uuid.uuid4())
        view = NotificationViewSet.as_view(actions={"get": "list"})
        response = view(request)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0

    def test_does_not_show_other_users_notifications(
        self, notification, user_id, other_user_id, db
    ):
        request = _build_request("get", "/api/notifications/", user_id=other_user_id)
        view = NotificationViewSet.as_view(actions={"get": "list"})
        response = view(request)
        assert len(response.data) == 0

    def test_returns_403_without_auth(self, db):
        request = _build_request("get", "/api/notifications/")
        view = NotificationViewSet.as_view(actions={"get": "list"})
        response = view(request)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_ordering_newest_first(self, user_id, db):
        n1 = Notification.objects.create(
            user_id=user_id, notification_type="system", title="Older"
        )
        n2 = Notification.objects.create(
            user_id=user_id, notification_type="system", title="Newer"
        )
        request = _build_request("get", "/api/notifications/", user_id=user_id)
        view = NotificationViewSet.as_view(actions={"get": "list"})
        response = view(request)
        assert response.data[0]["id"] == str(n2.id)
        assert response.data[1]["id"] == str(n1.id)


class TestNotificationViewSetRetrieve:
    def test_retrieve_own_notification(self, notification, user_id, db):
        request = _build_request(
            "get", f"/api/notifications/{notification.id}/", user_id=user_id
        )
        view = NotificationViewSet.as_view(actions={"get": "retrieve"})
        response = view(request, pk=str(notification.id))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == str(notification.id)

    def test_retrieve_others_notification_404(self, notification, other_user_id, db):
        request = _build_request(
            "get", f"/api/notifications/{notification.id}/", user_id=other_user_id
        )
        view = NotificationViewSet.as_view(actions={"get": "retrieve"})
        response = view(request, pk=str(notification.id))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_nonexistent_404(self, user_id, db):
        request = _build_request(
            "get",
            "/api/notifications/00000000-0000-0000-0000-000000000000/",
            user_id=user_id,
        )
        view = NotificationViewSet.as_view(actions={"get": "retrieve"})
        response = view(request, pk="00000000-0000-0000-0000-000000000000")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestNotificationViewSetMarkAllRead:
    def test_mark_all_read_marks_all_unread(self, user_id, db):
        Notification.objects.create(
            user_id=user_id, notification_type="system", title="A"
        )
        Notification.objects.create(
            user_id=user_id, notification_type="system", title="B"
        )
        request = _build_request(
            "post", "/api/notifications/mark_all_read/", user_id=user_id
        )
        view = NotificationViewSet.as_view(actions={"post": "mark_all_read"})
        response = view(request)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["marked_read"] == 2
        assert (
            Notification.objects.filter(user_id=user_id, read_at__isnull=True).count()
            == 0
        )

    def test_mark_all_read_idempotent(self, user_id, db):
        from django.utils import timezone

        Notification.objects.create(
            user_id=user_id,
            notification_type="system",
            title="A",
            read_at=timezone.now(),
        )
        request = _build_request(
            "post", "/api/notifications/mark_all_read/", user_id=user_id
        )
        view = NotificationViewSet.as_view(actions={"post": "mark_all_read"})
        response = view(request)
        assert response.data["marked_read"] == 0


class TestNotificationViewSetMarkRead:
    def test_mark_read_single(self, notification, user_id, db):
        request = _build_request(
            "post", f"/api/notifications/{notification.id}/mark_read/", user_id=user_id
        )
        view = NotificationViewSet.as_view(actions={"post": "mark_read"})
        response = view(request, pk=str(notification.id))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "ok"
        notification.refresh_from_db()
        assert notification.read_at is not None

    def test_mark_read_others_notification_404(self, notification, other_user_id, db):
        request = _build_request(
            "post",
            f"/api/notifications/{notification.id}/mark_read/",
            user_id=other_user_id,
        )
        view = NotificationViewSet.as_view(actions={"post": "mark_read"})
        response = view(request, pk=str(notification.id))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_mark_read_nonexistent_404(self, user_id, db):
        request = _build_request(
            "post", "/api/notifications/invalid/mark_read/", user_id=user_id
        )
        view = NotificationViewSet.as_view(actions={"post": "mark_read"})
        response = view(request, pk="00000000-0000-0000-0000-000000000000")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestNotificationViewSetDismiss:
    def test_dismiss_own_notification(self, notification, user_id, db):
        request = _build_request(
            "post", f"/api/notifications/{notification.id}/dismiss/", user_id=user_id
        )
        view = NotificationViewSet.as_view(actions={"post": "dismiss"})
        response = view(request, pk=str(notification.id))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "deleted"
        assert Notification.objects.filter(id=notification.id).count() == 0

    def test_dismiss_others_notification_404(self, notification, other_user_id, db):
        request = _build_request(
            "post",
            f"/api/notifications/{notification.id}/dismiss/",
            user_id=other_user_id,
        )
        view = NotificationViewSet.as_view(actions={"post": "dismiss"})
        response = view(request, pk=str(notification.id))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_dismiss_nonexistent_returns_not_found(self, user_id, db):
        request = _build_request(
            "post", "/api/notifications/nonexistent/dismiss/", user_id=user_id
        )
        view = NotificationViewSet.as_view(actions={"post": "dismiss"})
        response = view(request, pk="00000000-0000-0000-0000-000000000000")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestNotificationViewSetUnreadCount:
    def test_unread_count(self, user_id, db):
        Notification.objects.create(
            user_id=user_id, notification_type="system", title="Unread 1"
        )
        Notification.objects.create(
            user_id=user_id, notification_type="system", title="Unread 2"
        )
        from django.utils import timezone

        n = Notification.objects.create(
            user_id=user_id, notification_type="system", title="Read"
        )
        n.read_at = timezone.now()
        n.save(update_fields=["read_at"])
        request = _build_request(
            "get", "/api/notifications/unread_count/", user_id=user_id
        )
        view = NotificationViewSet.as_view(actions={"get": "unread_count"})
        response = view(request)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["unread_count"] == 2

    def test_unread_count_zero(self, user_id, db):
        request = _build_request(
            "get", "/api/notifications/unread_count/", user_id=user_id
        )
        view = NotificationViewSet.as_view(actions={"get": "unread_count"})
        response = view(request)
        assert response.data["unread_count"] == 0

    def test_unread_count_ignores_others(self, user_id, other_user_id, db):
        Notification.objects.create(
            user_id=other_user_id, notification_type="system", title="Theirs"
        )
        request = _build_request(
            "get", "/api/notifications/unread_count/", user_id=user_id
        )
        view = NotificationViewSet.as_view(actions={"get": "unread_count"})
        response = view(request)
        assert response.data["unread_count"] == 0


class TestFCMTokenViewSetCreate:
    def test_register_token(self, user_id, db):
        data = {"token": "new-fcm-token", "platform": "web"}
        request = _build_request("post", "/api/fcm-tokens/", user_id=user_id, data=data)
        view = FCMTokenViewSet.as_view(actions={"post": "create"})
        response = view(request)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["status"] == "registered"
        assert FCMToken.objects.filter(user_id=user_id, token="new-fcm-token").exists()

    def test_register_duplicate_token_updates_platform(self, user_id, db):
        FCMToken.objects.create(user_id=user_id, token="dup", platform="web")
        data = {"token": "dup", "platform": "android"}
        request = _build_request("post", "/api/fcm-tokens/", user_id=user_id, data=data)
        view = FCMTokenViewSet.as_view(actions={"post": "create"})
        response = view(request)
        assert response.status_code == status.HTTP_201_CREATED
        assert FCMToken.objects.filter(
            user_id=user_id, token="dup", platform="android"
        ).exists()
        assert FCMToken.objects.count() == 1

    def test_register_missing_field_400(self, user_id, db):
        data = {"token": "abc"}
        request = _build_request("post", "/api/fcm-tokens/", user_id=user_id, data=data)
        view = FCMTokenViewSet.as_view(actions={"post": "create"})
        response = view(request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_invalid_platform_400(self, user_id, db):
        data = {"token": "abc", "platform": "windows"}
        request = _build_request("post", "/api/fcm-tokens/", user_id=user_id, data=data)
        view = FCMTokenViewSet.as_view(actions={"post": "create"})
        response = view(request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_without_auth_403(self, db):
        data = {"token": "abc", "platform": "web"}
        request = _build_request("post", "/api/fcm-tokens/", data=data)
        view = FCMTokenViewSet.as_view(actions={"post": "create"})
        response = view(request)
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestFCMTokenViewSetDestroy:
    def test_delete_existing_token(self, fcm_token, user_id, db):
        request = _build_request(
            "delete", f"/api/fcm-tokens/{fcm_token.token}/", user_id=user_id
        )
        view = FCMTokenViewSet.as_view(actions={"delete": "destroy"})
        response = view(request, pk=fcm_token.token)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "removed"

    def test_delete_nonexistent_token(self, user_id, db):
        request = _build_request(
            "delete", "/api/fcm-tokens/nonexistent/", user_id=user_id
        )
        view = FCMTokenViewSet.as_view(actions={"delete": "destroy"})
        response = view(request, pk="nonexistent")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_other_users_token(self, fcm_token, other_user_id, db):
        request = _build_request(
            "delete", f"/api/fcm-tokens/{fcm_token.token}/", user_id=other_user_id
        )
        view = FCMTokenViewSet.as_view(actions={"delete": "destroy"})
        response = view(request, pk=fcm_token.token)
        assert response.status_code == status.HTTP_404_NOT_FOUND
