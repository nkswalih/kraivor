"""
Celery tasks for notification dispatch and lifecycle management.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    queue="notifications",
    max_retries=3,
    default_retry_delay=10,
    acks_late=True,
    name="notifications.dispatch_notification",
)
def dispatch_notification(
    self,
    *,
    user_id: str,
    notification_type: str,
    title: str,
    body: str = "",
    link: str = "",
    workspace_id: str | None = None,
    actor_id: str | None = None,
    send_push: bool = True,
) -> dict:
    """
    Dispatch a notification to a user.

    1. Creates a Notification record in PostgreSQL
    2. Broadcasts via Channels (WebSocket) if the user is connected
    3. Optionally sends a Firebase push notification

    Args:
        user_id:           UUID string of the recipient
        notification_type: Machine-readable type (e.g. 'workspace.member.joined')
        title:             Human-readable title
        body:              Human-readable body text
        link:              Deep link URL
        workspace_id:      Optional workspace context
        actor_id:          Optional user who triggered the notification
        send_push:         Whether to send a Firebase push notification
    """
    from apps.notifications.models import FCMToken, Notification

    logger.info(
        "task.notification.dispatch.started",
        extra={"user_id": user_id, "notification_type": notification_type},
    )

    # ── 1. Create PostgreSQL record ────────────────────────────────────────
    try:
        notif = Notification.objects.create(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            body=body,
            link=link,
            workspace_id=workspace_id,
            actor_id=actor_id,
        )
        logger.info(
            "task.notification.created",
            extra={"notification_id": str(notif.id), "user_id": user_id},
        )
    except Exception as exc:
        logger.error(
            "task.notification.create_failed",
            extra={"user_id": user_id, "error": str(exc)},
        )
        raise self.retry(exc=exc, countdown=30 * (2**self.request.retries)) from exc

    # ── 2. Broadcast via Channels ──────────────────────────────────────────
    try:
        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()
        if channel_layer is not None:
            from datetime import UTC, datetime

            group_name = f"notify_user_{user_id}"
            from asgiref.sync import async_to_sync

            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    "type": "send_notification",
                    "id": str(notif.id),
                    "notification_type": notification_type,
                    "title": title,
                    "body": body,
                    "link": link,
                    "workspace_id": workspace_id or "",
                    "actor_id": actor_id or "",
                    "created_at": datetime.now(tz=UTC).isoformat(),
                },
            )
    except Exception as exc:
        logger.warning(
            "task.notification.channels_failed",
            extra={"notification_id": str(notif.id), "error": str(exc)},
        )

    # ── 3. Send push notification ──────────────────────────────────────────
    if send_push:
        try:
            tokens = FCMToken.objects.filter(user_id=user_id).values_list(
                "token", flat=True
            )
            for token in tokens:
                from apps.notifications.firebase import send_push_notification

                send_push_notification(
                    token=token,
                    title=title,
                    body=body,
                    data={
                        "notification_id": str(notif.id),
                        "type": notification_type,
                        "link": link,
                    },
                )
        except Exception as exc:
            logger.warning(
                "task.notification.push_failed",
                extra={"user_id": user_id, "error": str(exc)},
            )

    return {
        "status": "dispatched",
        "notification_id": str(notif.id),
        "user_id": user_id,
    }


@shared_task(
    bind=True,
    queue="default",
    max_retries=2,
    default_retry_delay=30,
    name="notifications.cleanup_expired_notifications",
)
def cleanup_expired_notifications(self) -> dict:
    from apps.notifications.models import Notification

    cutoff = timezone.now() - timedelta(days=30)
    deleted_count, _ = Notification.objects.filter(created_at__lt=cutoff).delete()
    logger.info("task.notification.cleanup", extra={"deleted_count": deleted_count})
    return {"status": "completed", "deleted_count": deleted_count}


@shared_task(
    bind=True,
    queue="default",
    max_retries=2,
    default_retry_delay=15,
    name="notifications.sweep_stale_presence",
)
def sweep_stale_presence(self) -> dict:
    try:
        from core.infrastructure.redis import get_redis

        redis = get_redis()
        if redis is None:
            return {"status": "skipped", "reason": "redis_unavailable"}

        count = 0
        for key in redis.scan_iter(match="presence:user:*"):
            if redis.ttl(key) < 0:
                redis.delete(key)
                count += 1
        logger.info("task.presence.sweep", extra={"cleaned": count})
        return {"status": "completed", "cleaned": count}
    except Exception as exc:
        logger.error("task.presence.sweep_failed", extra={"error": str(exc)})
        raise self.retry(exc=exc, countdown=30) from exc
