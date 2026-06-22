import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.dispatch import receiver

from apps.chat.signals import message_sent

logger = logging.getLogger(__name__)


@receiver(message_sent)
def handle_message_sent(sender: type, **kwargs: dict) -> None:
    room_id: str | None = kwargs.get("room_id")
    data: dict = kwargs.get("data", {})
    if not room_id:
        return
    try:
        channel_layer = get_channel_layer()
        if channel_layer is not None:
            async_to_sync(channel_layer.group_send)(
                f"chat_{room_id}",
                {
                    "type": "chat_message",
                    **data,
                },
            )
    except Exception as exc:
        logger.warning(
            "chat.message.broadcast_failed",
            extra={"room_id": room_id, "error": str(exc)},
        )
