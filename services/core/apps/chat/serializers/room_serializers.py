from rest_framework import serializers

from apps.chat.models import ChatRoom, ChatRoomParticipant


class ChatRoomListSerializer(serializers.ModelSerializer):
    room_type_display: serializers.CharField = serializers.CharField(
        source="get_room_type_display", read_only=True
    )
    last_message_at: serializers.DateTimeField = serializers.DateTimeField(
        read_only=True
    )
    participant_user_ids: serializers.SerializerMethodField = (
        serializers.SerializerMethodField()
    )
    unread_count: serializers.SerializerMethodField = (
        serializers.SerializerMethodField()
    )

    class Meta:
        model: type[ChatRoom] = ChatRoom
        fields: list[str] = [
            "id",
            "workspace",
            "name",
            "room_type",
            "room_type_display",
            "topic",
            "is_active",
            "last_message_at",
            "last_message_content",
            "last_message_sender_name",
            "participant_user_ids",
            "unread_count",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields: list[str] = [
            "id",
            "workspace",
            "created_by",
            "created_at",
            "updated_at",
            "is_active",
        ]

    def get_participant_user_ids(self, obj: ChatRoom) -> list[str]:
        if not hasattr(obj, "_participant_ids"):
            return []
        return obj._participant_ids

    def get_unread_count(self, obj: ChatRoom) -> int:
        request = self.context.get("request")
        if not request:
            return 0
        user_id: str = str(getattr(request, "user_id", ""))
        # If no participant record exists (e.g. workspace rooms), all messages are unread
        participant: ChatRoomParticipant | None = ChatRoomParticipant.objects.filter(
            room=obj, user_id=user_id
        ).first()
        if not participant:
            return obj.message_count
        count: int = obj.message_count - participant.last_read_message_count
        return max(count, 0)


class ChatRoomDetailSerializer(serializers.ModelSerializer):
    room_type_display: serializers.CharField = serializers.CharField(
        source="get_room_type_display", read_only=True
    )
    participant_user_ids: serializers.SerializerMethodField = (
        serializers.SerializerMethodField()
    )

    class Meta:
        model: type[ChatRoom] = ChatRoom
        fields: list[str] = [
            "id",
            "workspace",
            "name",
            "room_type",
            "room_type_display",
            "topic",
            "is_active",
            "last_message_at",
            "last_message_content",
            "last_message_sender_name",
            "participant_user_ids",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields: list[str] = [
            "id",
            "workspace",
            "created_by",
            "created_at",
            "updated_at",
        ]

    def get_participant_user_ids(self, obj: ChatRoom) -> list[str]:
        if not hasattr(obj, "_participant_ids"):
            return []
        return obj._participant_ids


class ChatRoomCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model: type[ChatRoom] = ChatRoom
        fields: list[str] = ["id", "name", "room_type", "topic"]
        read_only_fields: list[str] = ["id"]

    def validate_name(self, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError(
                "Room name must be at least 2 characters."
            )
        if len(value) > 255:
            raise serializers.ValidationError(
                "Room name must not exceed 255 characters."
            )
        return value

    def validate_room_type(self, value: str) -> str:
        valid_types: list[str] = [t.value for t in ChatRoom.RoomType]
        if value not in valid_types:
            raise serializers.ValidationError(
                f"Invalid room type. Choose from: {', '.join(valid_types)}"
            )
        return value


class ChatRoomUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model: type[ChatRoom] = ChatRoom
        fields: list[str] = ["name", "topic"]
        extra_kwargs: dict[str, dict[str, bool]] = {
            field: {"required": False} for field in fields
        }

    def validate_name(self, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError(
                "Room name must be at least 2 characters."
            )
        return value


class CreateDmSerializer(serializers.Serializer):
    target_user_id: serializers.UUIDField = serializers.UUIDField()
    target_user_name: serializers.CharField = serializers.CharField(max_length=255)

    def validate_target_user_name(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Target user name is required.")
        return value
