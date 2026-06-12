"""
Celery tasks for chat operations.
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    queue="default",
    max_retries=3,
    default_retry_delay=10,
    acks_late=True,
    name="chat.persist_to_dynamodb",
)
def persist_to_dynamodb(
    self,
    *,
    room_id: str,
    sender_id: str,
    sender_name: str,
    content: str,
    content_type: str = "text",
    reply_to: str | None = None,
    mentions: list[str] | None = None,
    message_id: str | None = None,
) -> dict:
    from apps.chat.dynamodb import put_message

    logger.info(
        "task.chat.persist.started",
        extra={
            "room_id": room_id,
            "sender_id": sender_id,
            "message_id": message_id or "auto",
        },
    )
    try:
        item = put_message(
            room_id=room_id,
            sender_id=sender_id,
            sender_name=sender_name,
            content=content,
            content_type=content_type,
            reply_to=reply_to,
            mentions=mentions,
            message_id=message_id or None,
        )
        logger.info(
            "task.chat.persist.completed",
            extra={"room_id": room_id, "message_id": item["message_id"]},
        )
        return {"status": "persisted", "message_id": item["message_id"]}
    except Exception as exc:
        logger.error(
            "task.chat.persist.failed", extra={"room_id": room_id, "error": str(exc)}
        )
        raise self.retry(exc=exc, countdown=30 * (2**self.request.retries)) from exc


@shared_task(
    bind=True,
    queue="default",
    max_retries=2,
    default_retry_delay=30,
    acks_late=True,
    name="chat.trigger_ai_response",
)
def trigger_ai_response(
    self, *, room_id: str, message_id: str, content: str, workspace_id: str
) -> dict:
    logger.info(
        "task.chat.ai_triggered", extra={"room_id": room_id, "message_id": message_id}
    )
    # Placeholder: HTTP call to AI service goes here
    # ai_service_url = settings.AI_SERVICE_URL
    # requests.post(f"{ai_service_url}/api/chat/respond", json={...})
    return {"status": "dispatched", "room_id": room_id}
