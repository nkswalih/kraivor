import logging

from app.application.chat.chat_service import ChatService

logger = logging.getLogger(__name__)


async def handle_event(topic: str, event: dict) -> None:
    if topic == "ai.requests":
        user_id = event.get("user_id", "")
        message = event.get("message", "")
        conv_id = event.get("conversation_id")

        svc = ChatService()
        await svc.chat(
            user_id=user_id,
            message=message,
            conversation_id=conv_id,
        )
        logger.info("Processed ai.requests", user_id=user_id, conv_id=conv_id)

    elif topic == "ai.results":
        logger.info("Received ai.results event", event=event)
