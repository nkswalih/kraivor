import logging
from datetime import UTC, datetime

from django.db import transaction

from apps.chat.dynamodb import delete_message as dynamodb_delete_message
from apps.chat.dynamodb import get_message_by_id as dynamodb_get_message
from apps.chat.dynamodb import get_messages
from apps.chat.dynamodb import put_message as dynamodb_put_message
from apps.chat.dynamodb import update_message as dynamodb_update_message
from apps.chat.models import ChatRoom

logger = logging.getLogger(__name__)


class ChatRoomService:
    @staticmethod
    @transaction.atomic
    def create_room(
        *,
        workspace_id: str,
        name: str,
        room_type: str,
        created_by: str,
        topic: str = "",
    ) -> ChatRoom:
        room = ChatRoom.objects.create(
            workspace_id=workspace_id,
            name=name,
            room_type=room_type,
            topic=topic,
            created_by=created_by,
        )
        logger.info(
            "chat.room.created",
            extra={
                "room_id": str(room.id),
                "workspace_id": workspace_id,
                "room_type": room_type,
            },
        )
        return room

    @staticmethod
    def get_room(room_id: str) -> ChatRoom | None:
        try:
            return ChatRoom.objects.select_related("workspace").get(
                id=room_id, is_active=True
            )
        except ChatRoom.DoesNotExist:
            return None

    @staticmethod
    def list_rooms(workspace_id: str, user_id: str) -> list[ChatRoom]:
        return list(
            ChatRoom.objects.filter(workspace_id=workspace_id, is_active=True)
            .order_by("-last_message_at", "name")
            .only("id", "name", "room_type", "topic", "last_message_at", "created_at")
        )

    @staticmethod
    @transaction.atomic
    def update_room(room_id: str, user_id: str, data: dict) -> ChatRoom | None:
        room = ChatRoomService.get_room(room_id)
        if not room:
            return None

        allowed_fields = {"name", "topic"}
        for field, value in data.items():
            if field in allowed_fields:
                setattr(room, field, value)

        room.save(update_fields=list(data.keys() & allowed_fields) + ["updated_at"])
        logger.info("chat.room.updated", extra={"room_id": room_id, "user_id": user_id})
        return room

    @staticmethod
    @transaction.atomic
    def archive_room(room_id: str, user_id: str) -> bool:
        room = ChatRoomService.get_room(room_id)
        if not room:
            return False

        room.is_active = False
        room.save(update_fields=["is_active", "updated_at"])
        logger.info(
            "chat.room.archived", extra={"room_id": room_id, "user_id": user_id}
        )
        return True


class ChatMessageService:
    @staticmethod
    def get_messages(
        room_id: str, limit: int = 50, start_key: dict | None = None
    ) -> tuple[list[dict], dict | None]:
        messages, last_key = get_messages(
            room_id=room_id, limit=limit, start_key=start_key
        )
        filtered = [m for m in messages if not m.get("deleted_at")]
        return filtered, last_key

    @staticmethod
    def get_message(room_id: str, message_id: str) -> dict | None:
        return dynamodb_get_message(room_id=room_id, message_id=message_id)

    @staticmethod
    def update_message_content(
        room_id: str, message_id: str, sender_id: str, new_content: str
    ) -> dict | None:
        message = dynamodb_get_message(room_id=room_id, message_id=message_id)
        if not message:
            return None
        if message.get("sender_id") != sender_id:
            return None
        if message.get("deleted_at"):
            return None

        updated = dynamodb_update_message(
            room_id=room_id, message_id=message_id, content=new_content
        )
        logger.info(
            "chat.message.edited",
            extra={
                "message_id": message_id,
                "room_id": room_id,
                "sender_id": sender_id,
            },
        )
        return updated

    @staticmethod
    def delete_message(room_id: str, message_id: str) -> bool:
        message = dynamodb_get_message(room_id=room_id, message_id=message_id)
        if not message:
            return False
        if message.get("deleted_at"):
            return False

        dynamodb_delete_message(room_id=room_id, message_id=message_id)
        logger.info(
            "chat.message.deleted", extra={"message_id": message_id, "room_id": room_id}
        )
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
    ) -> dict:
        item = dynamodb_put_message(
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
            ChatRoom.objects.filter(id=room_id).update(
                last_message_at=datetime.now(tz=UTC)
            )
        except Exception as exc:
            logger.warning(
                "chat.room.last_message_at_update_failed",
                extra={"room_id": room_id, "error": str(exc)},
            )

        logger.info(
            "chat.message.api_sent",
            extra={
                "message_id": item["message_id"],
                "room_id": room_id,
                "sender_id": sender_id,
            },
        )
        return item

    @staticmethod
    def search_messages(room_id: str, query: str) -> list[dict]:
        messages, _ = get_messages(room_id=room_id, limit=100)
        query_lower = query.lower()
        results = []
        for msg in messages:
            if msg.get("deleted_at"):
                continue
            if query_lower in msg.get("content", "").lower():
                results.append(msg)
        return results
