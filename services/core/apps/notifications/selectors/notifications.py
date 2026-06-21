import uuid

from django.db.models import QuerySet
from django.utils import timezone

from core.cache import CacheService

from ..models import FCMToken, Notification


class NotificationSelector:
    NOTIFICATION_CACHE_PREFIX = "notif:unread"

    @staticmethod
    def list_user_notifications(user_id: uuid.UUID) -> QuerySet[Notification]:
        return (
            Notification.objects.filter(user_id=user_id)
            .select_related("workspace")
            .order_by("-created_at")
        )

    @staticmethod
    def get_unread_count(user_id: uuid.UUID) -> int:
        key = f"{NotificationSelector.NOTIFICATION_CACHE_PREFIX}:{user_id}"
        return CacheService.get_or_set(
            key=key,
            timeout=30,
            fallback=lambda: Notification.objects.filter(
                user_id=user_id, read_at__isnull=True
            ).count(),
        )

    @staticmethod
    def get_notification(notification_id: uuid.UUID, user_id: uuid.UUID) -> Notification | None:
        try:
            return Notification.objects.select_related("workspace").get(
                id=notification_id, user_id=user_id
            )
        except Notification.DoesNotExist:
            return None

    @staticmethod
    def mark_all_read(user_id: uuid.UUID) -> int:
        count = Notification.objects.filter(
            user_id=user_id, read_at__isnull=True
        ).update(read_at=timezone.now())
        CacheService.delete(f"{NotificationSelector.NOTIFICATION_CACHE_PREFIX}:{user_id}")
        return count

    @staticmethod
    def mark_read(notification: Notification) -> None:
        if not notification.read_at:
            notification.read_at = timezone.now()
            notification.save(update_fields=["read_at", "updated_at"])
            CacheService.delete(
                f"{NotificationSelector.NOTIFICATION_CACHE_PREFIX}:{notification.user_id}"
            )

    @staticmethod
    def dismiss(notification: Notification) -> None:
        CacheService.delete(
            f"{NotificationSelector.NOTIFICATION_CACHE_PREFIX}:{notification.user_id}"
        )
        notification.delete()

    @staticmethod
    def register_fcm_token(user_id: uuid.UUID, token: str, platform: str = "web") -> tuple[FCMToken, bool]:
        obj, created = FCMToken.objects.get_or_create(
            user_id=user_id,
            token=token,
            defaults={"platform": platform},
        )
        return obj, created

    @staticmethod
    def delete_fcm_token(user_id: uuid.UUID, token: str) -> bool:
        deleted = FCMToken.objects.filter(user_id=user_id, token=token).delete()
        return deleted[0] > 0
