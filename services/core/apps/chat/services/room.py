import logging
from datetime import UTC, datetime
from typing import Any

from django.db import transaction
from django.db.models import Count, QuerySet

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
        participants: QuerySet = ChatRoomParticipant.objects.filter(
            room_id__in=room_ids
        )
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
        return room

    @staticmethod
    def update_last_message(room_id: str, content: str, sender_name: str) -> None:
        ChatRoom.objects.filter(id=room_id).update(
            last_message_content=content,
            last_message_sender_name=sender_name,
            last_message_at=datetime.now(tz=UTC),
        )

    @staticmethod
    def increment_message_count(room_id: str) -> None:
        from django.db.models import F
        ChatRoom.objects.filter(id=room_id).update(message_count=F("message_count") + 1)

    @staticmethod
    def mark_room_read(room_id: str, user_id: str) -> None:
        room = ChatRoom.objects.filter(id=room_id).values_list("message_count", flat=True).first()
        if room is None:
            return
        ChatRoomParticipant.objects.update_or_create(
            room_id=room_id,
            user_id=user_id,
            defaults={"last_read_message_count": room},
        )

    @staticmethod
    @transaction.atomic
    def update_room(
        room_id: str, user_id: str, data: dict[str, Any]
    ) -> ChatRoom | None:
        room: ChatRoom | None = ChatRoomService.get_room(room_id)
        if not room:
            return None
        allowed_fields: set[str] = {"name", "topic"}
        for field, value in data.items():
            if field in allowed_fields:
                setattr(room, field, value)
        room.save(update_fields=list(data.keys() & allowed_fields) + ["updated_at"])
        return room

    @staticmethod
    @transaction.atomic
    def archive_room(room_id: str, user_id: str) -> bool:
        room: ChatRoom | None = ChatRoomService.get_room(room_id)
        if not room:
            return False
        room.is_active = False
        room.save(update_fields=["is_active", "updated_at"])
        return True
