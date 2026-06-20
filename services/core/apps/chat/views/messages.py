import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chat.models import ChatRoom
from apps.chat.permissions import IsChatRoomMember
from apps.chat.serializers import (
    MessageSerializer,
    MessageUpdateSerializer,
    SendMessageSerializer,
)
from apps.chat.services import ChatMessageService, ChatRoomService
from apps.chat.signals import message_sent
from apps.chat.views.exceptions import ServiceUnavailable
from apps.workspaces.permissions import IsAuthenticated

logger = logging.getLogger(__name__)


class MessageListSendView(APIView):
    permission_classes = [IsAuthenticated, IsChatRoomMember]

    def _get_room(self, room_pk: str) -> ChatRoom:
        room: ChatRoom | None = ChatRoomService.get_room(room_id=str(room_pk))
        if not room:
            raise NotFound("Chat room not found.")
        return room

    @extend_schema(
        operation_id="list_messages",
        tags=["chat-messages"],
        description="List messages in a chat room (cursor-paginated).",
        parameters=[
            OpenApiParameter(
                name="limit",
                description="Number of messages per page (max 200)",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="start_key",
                description="Cursor for pagination (JSON object from previous response)",
                required=False,
                type=str,
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="Paginated message list",
                response={
                    "type": "object",
                    "properties": {
                        "results": {"type": "array", "items": {"$ref": "#/components/schemas/Message"}},
                        "has_next": {"type": "boolean"},
                        "next_start_key": {"type": "string"},
                    },
                },
            ),
            400: OpenApiResponse(description="Invalid start_key format"),
        },
    )
    def get(self, request: Request, workspace_pk: str | None = None, room_pk: str | None = None) -> Response:
        self._get_room(room_pk)
        room_id: str = str(room_pk)
        limit: int = int(request.query_params.get("limit", 50))
        start_key: dict[str, Any] | None = None
        sk_param: str | None = request.query_params.get("start_key")
        if sk_param:
            try:
                start_key = json.loads(sk_param)
            except (json.JSONDecodeError, TypeError):
                return Response(
                    {"error": "Invalid start_key format. Must be a JSON object."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        try:
            messages: list[dict[str, Any]]
            last_key: dict[str, Any] | None
            messages, last_key = ChatMessageService.get_messages(
                room_id=room_id, limit=min(limit, 200), start_key=start_key
            )
        except Exception as exc:
            logger.error(
                "chat.messages.list_failed",
                extra={"room_id": room_id, "error": str(exc)},
            )
            raise ServiceUnavailable("Message store is temporarily unavailable.") from exc
        serializer: MessageSerializer = MessageSerializer(messages, many=True)
        result: dict[str, Any] = {
            "results": serializer.data,
            "has_next": last_key is not None,
        }
        if last_key:
            result["next_start_key"] = json.dumps(last_key)
        return Response(result)

    @extend_schema(
        operation_id="send_message",
        tags=["chat-messages"],
        description="Send a new message to a chat room.",
        request=SendMessageSerializer,
        responses={
            201: MessageSerializer,
            400: OpenApiResponse(description="Validation error"),
        },
        examples=[
            OpenApiExample(
                "Request example",
                value={
                    "content": "Hello world!",
                    "content_type": "text",
                    "mentions": [],
                    "reply_to": "",
                },
            ),
        ],
    )
    def post(self, request: Request, workspace_pk: str | None = None, room_pk: str | None = None) -> Response:
        self._get_room(room_pk)
        user_id: str = str(getattr(request, "user_id", ""))
        user_name: str = getattr(request, "user_name", "")
        s: SendMessageSerializer = SendMessageSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        room_id: str = str(room_pk)
        message_id: str = str(uuid.uuid4())
        now: str = datetime.now(tz=UTC).isoformat()
        item: dict[str, Any] = ChatMessageService.send_message_via_api(
            room_id=room_id,
            sender_id=user_id,
            sender_name=user_name,
            content=s.validated_data["content"],
            content_type=s.validated_data.get("content_type", "text"),
            reply_to=s.validated_data.get("reply_to"),
            mentions=s.validated_data.get("mentions", []),
            message_id=message_id,
        )
        broadcast_data: dict[str, Any] = {
            "message_id": message_id,
            "sender_id": user_id,
            "sender_name": user_name,
            "content": s.validated_data["content"],
            "content_type": s.validated_data.get("content_type", "text"),
            "reply_to": s.validated_data.get("reply_to", ""),
            "mentions": s.validated_data.get("mentions", []),
            "created_at": now,
        }
        message_sent.send(
            sender=MessageListSendView, room_id=room_id, data=broadcast_data
        )
        logger.info(
            "chat.message.sent_via_api",
            extra={"message_id": message_id, "room_id": room_id, "sender_id": user_id},
        )
        output: MessageSerializer = MessageSerializer(item)
        return Response(output.data, status=status.HTTP_201_CREATED)


class MessageDetailView(APIView):
    permission_classes = [IsAuthenticated, IsChatRoomMember]

    def _get_room(self, room_pk: str) -> ChatRoom:
        room: ChatRoom | None = ChatRoomService.get_room(room_id=str(room_pk))
        if not room:
            raise NotFound("Chat room not found.")
        return room

    @extend_schema(
        operation_id="get_message",
        tags=["chat-messages"],
        description="Retrieve a single message by ID.",
        responses={
            200: MessageSerializer,
            404: OpenApiResponse(description="Message not found"),
            503: OpenApiResponse(description="Message store unavailable"),
        },
    )
    def get(self, request: Request, pk: str | None = None, workspace_pk: str | None = None, room_pk: str | None = None) -> Response:
        self._get_room(room_pk)
        try:
            message: dict[str, Any] | None = ChatMessageService.get_message(
                room_id=str(room_pk), message_id=str(pk)
            )
        except Exception as exc:
            logger.error(
                "chat.message.get_failed",
                extra={"message_id": str(pk), "error": str(exc)},
            )
            raise ServiceUnavailable("Message store is temporarily unavailable.") from exc
        if not message or message.get("deleted_at"):
            raise NotFound("Message not found.")
        serializer: MessageSerializer = MessageSerializer(message)
        return Response(serializer.data)

    @extend_schema(
        operation_id="update_message",
        tags=["chat-messages"],
        description="Edit a message content.",
        request=MessageUpdateSerializer,
        responses={
            200: MessageSerializer,
            400: OpenApiResponse(description="Validation error"),
            404: OpenApiResponse(description="Message not found"),
            503: OpenApiResponse(description="Message store unavailable"),
        },
        examples=[
            OpenApiExample(
                "Request example",
                value={"content": "Updated content"},
            ),
        ],
    )
    def patch(self, request: Request, pk: str | None = None, workspace_pk: str | None = None, room_pk: str | None = None) -> Response:
        self._get_room(room_pk)
        user_id: str = str(getattr(request, "user_id", ""))
        serializer: MessageUpdateSerializer = MessageUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            updated: dict[str, Any] | None = ChatMessageService.update_message_content(
                room_id=str(room_pk),
                message_id=str(pk),
                sender_id=user_id,
                new_content=serializer.validated_data["content"],
            )
        except Exception as exc:
            logger.error(
                "chat.message.edit_failed",
                extra={"message_id": str(pk), "error": str(exc)},
            )
            raise ServiceUnavailable("Message store is temporarily unavailable.") from exc
        if updated is None:
            raise NotFound("Message not found or you can only edit your own messages.")
        output: MessageSerializer = MessageSerializer(updated)
        return Response(output.data)

    @extend_schema(
        operation_id="delete_message",
        tags=["chat-messages"],
        description="Soft-delete a message.",
        responses={
            200: OpenApiResponse(
                description="Message deleted",
                response={"type": "object", "properties": {"status": {"type": "string"}}},
            ),
            404: OpenApiResponse(description="Message not found"),
            503: OpenApiResponse(description="Message store unavailable"),
        },
    )
    def delete(self, request: Request, pk: str | None = None, workspace_pk: str | None = None, room_pk: str | None = None) -> Response:
        self._get_room(room_pk)
        try:
            success: bool = ChatMessageService.delete_message(
                room_id=str(room_pk), message_id=str(pk)
            )
        except Exception as exc:
            logger.error(
                "chat.message.delete_failed",
                extra={"message_id": str(pk), "error": str(exc)},
            )
            raise ServiceUnavailable("Message store is temporarily unavailable.") from exc
        if not success:
            raise NotFound("Message not found or already deleted.")
        return Response({"status": "deleted"}, status=status.HTTP_200_OK)


class MessageSearchView(APIView):
    permission_classes = [IsAuthenticated, IsChatRoomMember]

    def _get_room(self, room_pk: str) -> ChatRoom:
        room: ChatRoom | None = ChatRoomService.get_room(room_id=str(room_pk))
        if not room:
            raise NotFound("Chat room not found.")
        return room

    @extend_schema(
        operation_id="search_messages",
        tags=["chat-messages"],
        description="Search messages in a chat room by content (case-sensitive).",
        parameters=[
            OpenApiParameter(
                name="q",
                description="Search query (minimum 2 characters)",
                required=True,
                type=str,
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="Search results",
                response={
                    "type": "object",
                    "properties": {
                        "results": {"type": "array", "items": {"$ref": "#/components/schemas/Message"}},
                        "count": {"type": "integer"},
                    },
                },
            ),
            400: OpenApiResponse(description="Query too short"),
            503: OpenApiResponse(description="Message store unavailable"),
        },
        examples=[
            OpenApiExample(
                "Response example",
                value={"results": [], "count": 0},
            ),
        ],
    )
    def get(self, request: Request, workspace_pk: str | None = None, room_pk: str | None = None) -> Response:
        self._get_room(room_pk)
        query: str = request.query_params.get("q", "").strip()
        if not query or len(query) < 2:
            return Response(
                {"error": "Query must be at least 2 characters."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            results: list[dict[str, Any]] = ChatMessageService.search_messages(
                room_id=str(room_pk), query=query,
            )
        except Exception as exc:
            logger.error(
                "chat.messages.search_failed",
                extra={"room_id": str(room_pk), "error": str(exc)},
            )
            raise ServiceUnavailable("Message store is temporarily unavailable.") from exc
        serializer: MessageSerializer = MessageSerializer(results, many=True)
        return Response({"results": serializer.data, "count": len(results)})
