import json
import logging
import uuid
from datetime import UTC, datetime

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, NotFound
from rest_framework.pagination import CursorPagination
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from apps.chat.models import ChatRoom
from apps.chat.permissions import IsChatRoomMember
from apps.chat.serializers import (
    ChatRoomCreateSerializer,
    ChatRoomDetailSerializer,
    ChatRoomListSerializer,
    ChatRoomUpdateSerializer,
    MessageSerializer,
    MessageUpdateSerializer,
)
from apps.chat.services import ChatMessageService, ChatRoomService
from apps.workspaces.permissions import IsAuthenticated

logger = logging.getLogger(__name__)


def _str_uuid(value):
    if isinstance(value, str):
        return value
    return str(value)


class ServiceUnavailable(APIException):
    status_code = 503
    default_detail = "Service temporarily unavailable, please try again."
    default_code = "service_unavailable"


class MessageCursorPagination(CursorPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200
    ordering = "-created_at"


class ChatRoomViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsChatRoomMember]

    def get_serializer_class(self):
        if self.action == "create":
            return ChatRoomCreateSerializer
        if self.action in ("partial_update", "update"):
            return ChatRoomUpdateSerializer
        if self.action == "retrieve":
            return ChatRoomDetailSerializer
        return ChatRoomListSerializer

    def list(self, request, workspace_pk=None):
        user_id = _str_uuid(getattr(request, "user_id", ""))
        workspace_id = _str_uuid(workspace_pk)
        rooms = ChatRoomService.list_rooms(workspace_id=workspace_id, user_id=user_id)
        serializer = ChatRoomListSerializer(rooms, many=True, context={"request": request})
        return Response(serializer.data)

    def create(self, request, workspace_pk=None):
        user_id = _str_uuid(getattr(request, "user_id", ""))
        workspace_id = _str_uuid(workspace_pk)
        serializer = ChatRoomCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        room = ChatRoomService.create_room(
            workspace_id=workspace_id,
            name=serializer.validated_data["name"],
            room_type=serializer.validated_data.get("room_type", ChatRoom.RoomType.GROUP),
            created_by=user_id,
            topic=serializer.validated_data.get("topic", ""),
        )
        output = ChatRoomDetailSerializer(room, context={"request": request})
        return Response(output.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None, workspace_pk=None):
        room = ChatRoomService.get_room(room_id=_str_uuid(pk))
        if not room:
            raise NotFound("Chat room not found.")
        serializer = ChatRoomDetailSerializer(room, context={"request": request})
        return Response(serializer.data)

    def partial_update(self, request, pk=None, workspace_pk=None):
        user_id = _str_uuid(getattr(request, "user_id", ""))
        serializer = ChatRoomUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        room = ChatRoomService.update_room(
            room_id=_str_uuid(pk),
            user_id=user_id,
            data=serializer.validated_data,
        )
        if not room:
            raise NotFound("Chat room not found.")

        output = ChatRoomDetailSerializer(room, context={"request": request})
        return Response(output.data)

    def destroy(self, request, pk=None, workspace_pk=None):
        user_id = _str_uuid(getattr(request, "user_id", ""))
        success = ChatRoomService.archive_room(room_id=_str_uuid(pk), user_id=user_id)
        if not success:
            raise NotFound("Chat room not found.")
        return Response({"status": "archived"}, status=status.HTTP_200_OK)


class MessageViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsChatRoomMember]
    pagination_class = MessageCursorPagination

    def _get_room_or_error(self, room_id):
        room = ChatRoomService.get_room(room_id=_str_uuid(room_id))
        if not room:
            raise NotFound("Chat room not found.")
        return room

    def list(self, request, workspace_pk=None, room_pk=None):
        self._get_room_or_error(room_pk)
        room_id = _str_uuid(room_pk)

        limit = int(request.query_params.get("limit", 50))
        start_key_param = request.query_params.get("start_key")
        start_key = None
        if start_key_param:
            try:
                start_key = json.loads(start_key_param)
            except (json.JSONDecodeError, TypeError):
                return Response(
                    {"error": "Invalid start_key format. Must be a JSON object."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            messages, last_key = ChatMessageService.get_messages(
                room_id=room_id,
                limit=min(limit, 200),
                start_key=start_key,
            )
        except Exception as exc:
            logger.error("chat.messages.list_failed", extra={"room_id": room_id, "error": str(exc)})
            raise ServiceUnavailable("Message store is temporarily unavailable.") from exc

        serializer = MessageSerializer(messages, many=True)
        response_data = {
            "results": serializer.data,
            "has_next": last_key is not None,
        }
        if last_key:
            response_data["next_start_key"] = json.dumps(last_key)

        return Response(response_data)

    def retrieve(self, request, pk=None, workspace_pk=None, room_pk=None):
        self._get_room_or_error(room_pk)

        try:
            message = ChatMessageService.get_message(
                room_id=_str_uuid(room_pk),
                message_id=_str_uuid(pk),
            )
        except Exception as exc:
            logger.error("chat.message.get_failed", extra={"message_id": str(pk), "error": str(exc)})
            raise ServiceUnavailable("Message store is temporarily unavailable.") from exc

        if not message:
            raise NotFound("Message not found.")
        if message.get("deleted_at"):
            raise NotFound("Message not found.")

        serializer = MessageSerializer(message)
        return Response(serializer.data)

    def partial_update(self, request, pk=None, workspace_pk=None, room_pk=None):
        self._get_room_or_error(room_pk)
        user_id = _str_uuid(getattr(request, "user_id", ""))

        serializer = MessageUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated = ChatMessageService.update_message_content(
                room_id=_str_uuid(room_pk),
                message_id=_str_uuid(pk),
                sender_id=user_id,
                new_content=serializer.validated_data["content"],
            )
        except Exception as exc:
            logger.error("chat.message.edit_failed", extra={"message_id": str(pk), "error": str(exc)})
            raise ServiceUnavailable("Message store is temporarily unavailable.") from exc

        if updated is None:
            raise NotFound("Message not found or you can only edit your own messages.")

        output = MessageSerializer(updated)
        return Response(output.data)

    def destroy(self, request, pk=None, workspace_pk=None, room_pk=None):
        self._get_room_or_error(room_pk)

        try:
            success = ChatMessageService.delete_message(
                room_id=_str_uuid(room_pk),
                message_id=_str_uuid(pk),
            )
        except Exception as exc:
            logger.error("chat.message.delete_failed", extra={"message_id": str(pk), "error": str(exc)})
            raise ServiceUnavailable("Message store is temporarily unavailable.") from exc

        if not success:
            raise NotFound("Message not found or already deleted.")

        return Response({"status": "deleted"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def send(self, request, workspace_pk=None, room_pk=None):
        self._get_room_or_error(room_pk)
        user_id = _str_uuid(getattr(request, "user_id", ""))
        user_name = getattr(request, "user_name", "")

        content = request.data.get("content", "").strip()
        if not content:
            return Response({"error": "Content is required."}, status=status.HTTP_400_BAD_REQUEST)

        room_id = _str_uuid(room_pk)
        message_id = str(uuid.uuid4())
        now = datetime.now(tz=UTC).isoformat()
        content_type = request.data.get("content_type", "text")
        mentions = request.data.get("mentions", [])
        reply_to = request.data.get("reply_to")

        item = ChatMessageService.send_message_via_api(
            room_id=room_id,
            sender_id=user_id,
            sender_name=user_name,
            content=content,
            content_type=content_type,
            reply_to=reply_to,
            mentions=mentions,
            message_id=message_id,
        )

        try:
            channel_layer = get_channel_layer()
            if channel_layer is not None:
                group_name = f"chat_{room_id}"
                async_to_sync(channel_layer.group_send)(
                    group_name,
                    {
                        "type": "chat_message",
                        "message_id": message_id,
                        "sender_id": user_id,
                        "sender_name": user_name,
                        "content": content,
                        "content_type": content_type,
                        "reply_to": reply_to or "",
                        "mentions": mentions or [],
                        "created_at": now,
                    },
                )
        except Exception as exc:
            logger.warning("chat.message.broadcast_failed", extra={"room_id": room_id, "error": str(exc)})

        try:
            ChatRoom.objects.filter(id=room_id).update(last_message_at=now)
        except Exception as exc:
            logger.warning("chat.message.last_message_at_update_failed", extra={"room_id": room_id, "error": str(exc)})

        logger.info(
            "chat.message.sent_via_api",
            extra={"message_id": message_id, "room_id": room_id, "sender_id": user_id},
        )

        output = MessageSerializer(item)
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def search(self, request, workspace_pk=None, room_pk=None):
        self._get_room_or_error(room_pk)
        query = request.query_params.get("q", "").strip()
        if not query or len(query) < 2:
            return Response(
                {"error": "Query must be at least 2 characters."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            results = ChatMessageService.search_messages(
                room_id=_str_uuid(room_pk),
                query=query,
            )
        except Exception as exc:
            logger.error("chat.messages.search_failed", extra={"room_id": str(room_pk), "error": str(exc)})
            raise ServiceUnavailable("Message store is temporarily unavailable.") from exc

        serializer = MessageSerializer(results, many=True)
        return Response({"results": serializer.data, "count": len(results)})
