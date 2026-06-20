import logging
from typing import Any

from drf_spectacular.utils import (
    OpenApiExample,
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
    ChatRoomCreateSerializer,
    ChatRoomDetailSerializer,
    ChatRoomListSerializer,
    ChatRoomUpdateSerializer,
    CreateDmSerializer,
)
from apps.chat.services import ChatRoomService
from apps.workspaces.permissions import IsAuthenticated

logger = logging.getLogger(__name__)


class RoomListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsChatRoomMember]

    @extend_schema(
        operation_id="list_chat_rooms",
        tags=["chat-rooms"],
        description="List all chat rooms the user can see in a workspace.",
        responses={
            200: ChatRoomListSerializer(many=True),
        },
        examples=[
            OpenApiExample(
                "Response example",
                value=[{"id": "uuid", "name": "general", "room_type": "workspace"}],
            ),
        ],
    )
    def get(self, request: Request, workspace_pk: str | None = None) -> Response:
        user_id: str = str(getattr(request, "user_id", ""))
        workspace_id: str = str(workspace_pk)
        rooms: list[ChatRoom] = ChatRoomService.list_rooms(
            workspace_id=workspace_id, user_id=user_id
        )
        serializer: ChatRoomListSerializer = ChatRoomListSerializer(
            rooms, many=True, context={"request": request}
        )
        return Response(serializer.data)

    @extend_schema(
        operation_id="create_chat_room",
        tags=["chat-rooms"],
        description="Create a new channel or group chat room.",
        request=ChatRoomCreateSerializer,
        responses={
            201: ChatRoomDetailSerializer,
            400: OpenApiResponse(description="Validation error"),
        },
        examples=[
            OpenApiExample(
                "Request example",
                value={"name": "my-channel", "room_type": "group", "topic": "Chat about stuff"},
            ),
        ],
    )
    def post(self, request: Request, workspace_pk: str | None = None) -> Response:
        user_id: str = str(getattr(request, "user_id", ""))
        workspace_id: str = str(workspace_pk)
        serializer: ChatRoomCreateSerializer = ChatRoomCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        room: ChatRoom = ChatRoomService.create_room(
            workspace_id=workspace_id,
            name=serializer.validated_data["name"],
            room_type=serializer.validated_data.get("room_type", ChatRoom.RoomType.GROUP),
            created_by=user_id,
            topic=serializer.validated_data.get("topic", ""),
        )
        output: ChatRoomDetailSerializer = ChatRoomDetailSerializer(
            room, context={"request": request}
        )
        return Response(output.data, status=status.HTTP_201_CREATED)


class RoomDetailView(APIView):
    permission_classes = [IsAuthenticated, IsChatRoomMember]

    def _get_room(self, pk: str) -> ChatRoom:
        room: ChatRoom | None = ChatRoomService.get_room(room_id=str(pk))
        if not room:
            raise NotFound("Chat room not found.")
        return room

    @extend_schema(
        operation_id="get_chat_room",
        tags=["chat-rooms"],
        description="Retrieve a chat room by ID.",
        responses={
            200: ChatRoomDetailSerializer,
            404: OpenApiResponse(description="Chat room not found"),
        },
    )
    def get(self, request: Request, pk: str | None = None, workspace_pk: str | None = None) -> Response:
        room: ChatRoom = self._get_room(pk)
        serializer: ChatRoomDetailSerializer = ChatRoomDetailSerializer(
            room, context={"request": request}
        )
        return Response(serializer.data)

    @extend_schema(
        operation_id="update_chat_room",
        tags=["chat-rooms"],
        description="Update a chat room name and/or topic.",
        request=ChatRoomUpdateSerializer,
        responses={
            200: ChatRoomDetailSerializer,
            400: OpenApiResponse(description="Validation error"),
            404: OpenApiResponse(description="Chat room not found"),
        },
        examples=[
            OpenApiExample(
                "Request example",
                value={"name": "updated-name", "topic": "New topic"},
            ),
        ],
    )
    def patch(self, request: Request, pk: str | None = None, workspace_pk: str | None = None) -> Response:
        user_id: str = str(getattr(request, "user_id", ""))
        room: ChatRoom = self._get_room(pk)
        serializer: ChatRoomUpdateSerializer = ChatRoomUpdateSerializer(
            data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        updated: ChatRoom | None = ChatRoomService.update_room(
            room_id=str(pk), user_id=user_id, data=serializer.validated_data
        )
        if not updated:
            raise NotFound("Chat room not found.")
        output: ChatRoomDetailSerializer = ChatRoomDetailSerializer(
            updated, context={"request": request}
        )
        return Response(output.data)

    @extend_schema(
        operation_id="archive_chat_room",
        tags=["chat-rooms"],
        description="Soft-delete (archive) a chat room.",
        responses={
            200: OpenApiResponse(description="Room archived", response={"type": "object", "properties": {"status": {"type": "string"}}}),
            404: OpenApiResponse(description="Chat room not found"),
        },
    )
    def delete(self, request: Request, pk: str | None = None, workspace_pk: str | None = None) -> Response:
        user_id: str = str(getattr(request, "user_id", ""))
        success: bool = ChatRoomService.archive_room(room_id=str(pk), user_id=user_id)
        if not success:
            raise NotFound("Chat room not found.")
        return Response({"status": "archived"}, status=status.HTTP_200_OK)


class DMCreateView(APIView):
    permission_classes = [IsAuthenticated, IsChatRoomMember]

    @extend_schema(
        operation_id="create_dm_room",
        tags=["chat-dm"],
        description="Find an existing DM room with the target user, or create a new one.",
        request=CreateDmSerializer,
        responses={
            200: ChatRoomDetailSerializer,
            400: OpenApiResponse(description="Validation error"),
        },
        examples=[
            OpenApiExample(
                "Request example",
                value={"target_user_id": "uuid-of-target", "target_user_name": "jane"},
            ),
        ],
    )
    def post(self, request: Request, workspace_pk: str | None = None) -> Response:
        user_id: str = str(getattr(request, "user_id", ""))
        workspace_id: str = str(workspace_pk)
        serializer: CreateDmSerializer = CreateDmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        room: ChatRoom = ChatRoomService.get_or_create_dm_room(
            workspace_id=workspace_id,
            user_id_1=user_id,
            user_id_2=str(serializer.validated_data["target_user_id"]),
            target_name=serializer.validated_data["target_user_name"],
        )
        output: ChatRoomDetailSerializer = ChatRoomDetailSerializer(
            room, context={"request": request}
        )
        return Response(output.data, status=status.HTTP_200_OK)
