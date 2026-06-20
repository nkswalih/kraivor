import logging
from datetime import UTC, datetime
from typing import Any

from django.db import transaction
from django.db.models import Count, QuerySet

from apps.chat.dynamodb import get_repository
from apps.chat.models import ChatRoom, ChatRoomParticipant

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
        participant_ids: list[str] | None = None,
    ) -> ChatRoom:
        room: ChatRoom = ChatRoom.objects.create(
            workspace_id=workspace_id,
            name=name,
            room_type=room_type,
            topic=topic,
            created_by=created_by,
        )
        if participant_ids:
            ChatRoomParticipant.objects.bulk_create(
                [
                    ChatRoomParticipant(room=room, user_id=uid)
                    for uid in participant_ids
                ],
                ignore_conflicts=True,
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
            room: ChatRoom = ChatRoom.objects.select_related("workspace").get(
                id=room_id, is_active=True
            )
            if room.room_type == "dm":
                p_ids: list[str] = list(
                    ChatRoomParticipant.objects.filter(room_id=room.id).values_list(
                        "user_id", flat=True
                    )
                )
                room._participant_ids = [str(uid) for uid in p_ids]
            return room
        except ChatRoom.DoesNotExist:
            return None

    @staticmethod
    def _attach_participant_ids(rooms: list[ChatRoom]) -> list[ChatRoom]:
        dm_rooms: list[ChatRoom] = [r for r in rooms if r.room_type == "dm"]
        if not dm_rooms:
            return rooms

        room_ids: list[str] = [str(r.id) for r in dm_rooms]
        participants: QuerySet = ChatRoomParticipant.objects.filter(room_id__in=room_ids)
        mapping: dict[str, list[str]] = {}
        for p in participants:
            mapping.setdefault(str(p.room_id), []).append(str(p.user_id))

        for r in dm_rooms:
            r._participant_ids = mapping.get(str(r.id), [])
        return rooms

    @staticmethod
    def list_rooms(workspace_id: str, user_id: str) -> list[ChatRoom]:
        non_dm: QuerySet = ChatRoom.objects.filter(
            workspace_id=workspace_id, is_active=True
        ).exclude(room_type="dm")

        dm_room_ids: QuerySet = ChatRoomParticipant.objects.filter(
            user_id=user_id,
            room__workspace_id=workspace_id,
            room__is_active=True,
            room__room_type="dm",
        ).values_list("room_id", flat=True)

        dm_rooms: QuerySet = ChatRoom.objects.filter(id__in=list(dm_room_ids))

        combined: list[ChatRoom] = list(non_dm) + list(dm_rooms)
        combined.sort(
            key=lambda r: (
                -(r.last_message_at.timestamp() if r.last_message_at else 0),
                r.name,
            )
        )
        return ChatRoomService._attach_participant_ids(combined)

    @staticmethod
    @transaction.atomic
    def get_or_create_dm_room(
        *,
        workspace_id: str,
        user_id_1: str,
        user_id_2: str,
        target_name: str,
    ) -> ChatRoom:
        existing_rooms: QuerySet = (
            ChatRoomParticipant.objects.filter(
                room__workspace_id=workspace_id,
                room__room_type="dm",
                room__is_active=True,
                user_id__in=[user_id_1, user_id_2],
            )
            .values("room_id")
            .annotate(cnt=Count("id"))
            .filter(cnt=2)
        )
        if existing_rooms:
            room_id: str = existing_rooms[0]["room_id"]
            room: ChatRoom = ChatRoom.objects.get(id=room_id)
            room._participant_ids = [user_id_1, user_id_2]
            return room

        room = ChatRoom.objects.create(
            workspace_id=workspace_id,
            name=target_name,
            room_type=ChatRoom.RoomType.DM,
            created_by=user_id_1,
        )
        ChatRoomParticipant.objects.bulk_create(
            [
                ChatRoomParticipant(room=room, user_id=user_id_1),
                ChatRoomParticipant(room=room, user_id=user_id_2),
            ]
        )
        room._participant_ids = [user_id_1, user_id_2]
        logger.info(
            "chat.dm.created",
            extra={
                "room_id": str(room.id),
                "workspace_id": workspace_id,
                "user_1": user_id_1,
                "user_2": user_id_2,
            },
        )
        return room

    @staticmethod
    def update_last_message(room_id: str, content: str, sender_name: str) -> None:
        ChatRoom.objects.filter(id=room_id).update(
            last_message_content=content,
            last_message_sender_name=sender_name,
            last_message_at=datetime.now(tz=UTC),
        )

    @staticmethod
    @transaction.atomic
    def update_room(room_id: str, user_id: str, data: dict[str, Any]) -> ChatRoom | None:
        room: ChatRoom | None = ChatRoomService.get_room(room_id)
        if not room:
            return None

        allowed_fields: set[str] = {"name", "topic"}
        for field, value in data.items():
            if field in allowed_fields:
                setattr(room, field, value)

        room.save(update_fields=list(data.keys() & allowed_fields) + ["updated_at"])
        logger.info("chat.room.updated", extra={"room_id": room_id, "user_id": user_id})
        return room

    @staticmethod
    @transaction.atomic
    def archive_room(room_id: str, user_id: str) -> bool:
        room: ChatRoom | None = ChatRoomService.get_room(room_id)
        if not room:
            return False

        room.is_active = False
        room.save(update_fields=["is_active", "updated_at"])
        logger.info("chat.room.archived", extra={"room_id": room_id, "user_id": user_id})
        return True


class ChatMessageService:
    _repo = get_repository()

    @staticmethod
    def get_messages(
        room_id: str, limit: int = 50, start_key: dict[str, Any] | None = None
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        messages, last_key = get_repository().get_messages(
            room_id=room_id, limit=limit, start_key=start_key
        )
        filtered: list[dict[str, Any]] = [m for m in messages if not m.get("deleted_at")]
        return filtered, last_key

    @staticmethod
    def get_message(room_id: str, message_id: str) -> dict[str, Any] | None:
        return get_repository().get_message_by_id(room_id=room_id, message_id=message_id)

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
        message: dict[str, Any] | None = get_repository().get_message_by_id(
            room_id=room_id, message_id=message_id
        )
        if not message:
            return False
        if message.get("deleted_at"):
            return False

        get_repository().delete_message(room_id=room_id, message_id=message_id)
        logger.info(
            "chat.message.deleted",
            extra={"message_id": message_id, "room_id": room_id},
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
    def search_messages(room_id: str, query: str, limit: int = 50) -> list[dict[str, Any]]:
        return get_repository().search_messages(
            room_id=room_id, query=query, limit=limit
        )
