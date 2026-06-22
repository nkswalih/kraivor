from typing import Any

import logging

from apps.chat.dynamodb import get_repository

from .room import ChatRoomService

logger = logging.getLogger(__name__)


class ChatMessageService:
    _repo = get_repository()

    @staticmethod
    def get_messages(
        room_id: str, limit: int = 50, start_key: dict[str, Any] | None = None
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        messages, last_key = get_repository().get_messages(
            room_id=room_id, limit=limit, start_key=start_key
        )
        filtered: list[dict[str, Any]] = [
            m for m in messages if not m.get("deleted_at")
        ]
        return filtered, last_key

    @staticmethod
    def get_message(room_id: str, message_id: str) -> dict[str, Any] | None:
        return get_repository().get_message_by_id(
            room_id=room_id, message_id=message_id
        )

    @staticmethod
    def update_message_content(
        room_id: str, message_id: str, sender_id: str, new_content: str
    ) -> dict[str, Any] | None:
        message: dict[str, Any] | None = get_repository().get_message_by_id(
            room_id=room_id, message_id=message_id
        )
        if not message:
            return None
        if message.get("sender_id") != sender_id:
            return None
        if message.get("deleted_at"):
            return None
        updated: dict[str, Any] | None = get_repository().update_message(
            room_id=room_id, message_id=message_id, content=new_content
        )
        return updated

    @staticmethod
    def delete_message(room_id: str, message_id: str) -> bool:
        message: dict[str, Any] | None = get_repository().get_message_by_id(
            room_id=room_id, message_id=message_id
        )
        if not message:
            return False
        if message.get("deleted_at"):
            return False
        get_repository().delete_message(room_id=room_id, message_id=message_id)
        return True

    @staticmethod
    def send_message_via_api(
        *,
        room_id: str,
        sender_id: str,
        sender_name: str,
        content: str,
        content_type: str = "text",
        reply_to: str | None = None,
        mentions: list[str] | None = None,
        message_id: str | None = None,
        attachment_url: str = "",
    ) -> dict[str, Any]:
        item: dict[str, Any] = get_repository().put_message(
            room_id=room_id,
            sender_id=sender_id,
            sender_name=sender_name,
            content=content,
            content_type=content_type,
            reply_to=reply_to,
            mentions=mentions,
            message_id=message_id,
            attachment_url=attachment_url,
        )
        try:
            ChatRoomService.update_last_message(
                room_id=room_id, content=content, sender_name=sender_name
            )
        except Exception as exc:
            logger.warning(
                "chat.room.last_message_update_failed",
                extra={"room_id": room_id, "error": str(exc)},
            )
        return item

    @staticmethod
    def search_messages(
        room_id: str, query: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        return get_repository().search_messages(
            room_id=room_id, query=query, limit=limit
        )
