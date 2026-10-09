import logging
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
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
from apps.workspaces.models import WorkspaceMember
from apps.workspaces.permissions import IsAuthenticated

logger = logging.getLogger(__name__)


class RoomListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsChatRoomMember]

    @extend_schema(
        operation_id="list_chat_rooms",
        tags=["chat-rooms"],
        description="List all chat rooms the user can see in a workspace.",
        responses={200: ChatRoomListSerializer(many=True)},
        examples=[
            OpenApiExample(
                "Response example",
                value=[{"id": "uuid", "name": "general", "room_type": "workspace"}],
            )
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
                value={
                    "name": "my-channel",
                    "room_type": "group",
                    "topic": "Chat about stuff",
                },
            )
        ],
    )
    def post(self, request: Request, workspace_pk: str | None = None) -> Response:
        user_id: str = str(getattr(request, "user_id", ""))
        workspace_id: str = str(workspace_pk)
        serializer: ChatRoomCreateSerializer = ChatRoomCreateSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        room: ChatRoom = ChatRoomService.create_room(
            workspace_id=workspace_id,
            name=serializer.validated_data["name"],
            room_type=serializer.validated_data.get(
                "room_type", ChatRoom.RoomType.GROUP
            ),
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
    def get(
        self, request: Request, pk: str | None = None, workspace_pk: str | None = None
    ) -> Response:
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
                "Request example", value={"name": "updated-name", "topic": "New topic"}
            )
        ],
    )
    def patch(
        self, request: Request, pk: str | None = None, workspace_pk: str | None = None
    ) -> Response:
        user_id: str = str(getattr(request, "user_id", ""))
        self._get_room(pk)
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
            200: OpenApiResponse(
                description="Room archived",
                response={
                    "type": "object",
                    "properties": {"status": {"type": "string"}},
                },
            ),
            404: OpenApiResponse(description="Chat room not found"),
        },
    )
    def delete(
        self, request: Request, pk: str | None = None, workspace_pk: str | None = None
    ) -> Response:
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
            403: OpenApiResponse(
                description="Target is not a member of this workspace"
            ),
        },
        examples=[
            OpenApiExample(
                "Request example",
                value={"target_user_id": "uuid-of-target", "target_user_name": "jane"},
            )
        ],
    )
    def post(self, request: Request, workspace_pk: str | None = None) -> Response:
        user_id: str = str(getattr(request, "user_id", ""))
        workspace_id: str = str(workspace_pk)
        serializer: CreateDmSerializer = CreateDmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_id: str = str(serializer.validated_data["target_user_id"])

        # Both checks read `validated_data`, never `request.data`. The serializer
        # is what guarantees the id parses as a UUID and the name fits the column;
        # reaching past it would put the over-length and blank cases back to the
        # driver-dependent 500s it currently prevents.
        self._reject_a_dm_to_oneself(user_id, target_id)
        self._reject_an_unreachable_target(workspace_id, target_id)

        room: ChatRoom = ChatRoomService.get_or_create_dm_room(
            workspace_id=workspace_id,
            user_id_1=user_id,
            user_id_2=target_id,
            target_name=serializer.validated_data["target_user_name"],
        )
        output: ChatRoomDetailSerializer = ChatRoomDetailSerializer(
            room, context={"request": request}
        )
        return Response(output.data, status=status.HTTP_200_OK)

    @staticmethod
    def _reject_a_dm_to_oneself(user_id: str, target_id: str) -> None:
        """Refuse a self-DM before it reaches the service, where it was a 500.

        `get_or_create_dm_room` finds an existing conversation by counting
        participants whose id is in `[user_id_1, user_id_2]`. With the two equal,
        that `cnt=2` can never match -- one user, one row -- so the lookup always
        fell through to creating a room and inserting the *same* participant twice.
        `ChatRoomParticipant` has `unique_together(room, user_id)` and that
        `bulk_create` has no `ignore_conflicts`, so the insert raised
        `IntegrityError` and the client got a 500 for asking a question with an
        obvious answer.

        400 rather than 403: nobody was forbidden, the request itself cannot be
        satisfied. Checked first because a self-DM is also a membership question
        that would pass, and reporting the wrong one of two true things is a small
        waste of the reader's time.
        """
        if str(target_id) != str(user_id):
            return
        raise ValidationError({"target_user_id": "You cannot direct message yourself."})

    @staticmethod
    def _reject_an_unreachable_target(workspace_id: str, target_id: str) -> None:
        """Refuse a target who is not a live member of *this* workspace.

        `IsChatRoomMember` checks the *caller* and this view had no `pk`, so it
        checked nobody else. A room was therefore created with a participant row
        for whatever id arrived: a user who never joined, a user who has since left,
        a user belonging to a different workspace. The other participant's sidebar
        rendered a DM to somebody no request could ever reach.

        The predicate is `WorkspaceMember.objects`, whose queryset is already
        `.alive()` -- the same manager the caller's own check goes through, so this
        is the same definition of "belongs here" rather than a second one.

        One 403 for all three cases, deliberately. A 404 for "no such user" next to
        a 403 for "not in your workspace" is a reliable oracle: post any UUID and
        learn whether it belongs to an account. The message names none of them.
        """
        is_reachable: bool = WorkspaceMember.objects.filter(
            workspace_id=workspace_id, user_id=target_id
        ).exists()
        if is_reachable:
            return
        raise PermissionDenied("That user is not a member of this workspace.")
