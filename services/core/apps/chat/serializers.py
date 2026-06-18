from rest_framework import serializers

from apps.chat.models import ChatRoom


class ChatRoomListSerializer(serializers.ModelSerializer):
    room_type_display = serializers.CharField(
        source="get_room_type_display", read_only=True
    )
    last_message_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = ChatRoom
        fields = [
            "id",
            "workspace",
            "name",
            "room_type",
            "room_type_display",
            "topic",
            "is_active",
            "last_message_at",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "workspace",
            "created_by",
            "created_at",
            "updated_at",
            "is_active",
        ]


class ChatRoomDetailSerializer(serializers.ModelSerializer):
    room_type_display = serializers.CharField(
        source="get_room_type_display", read_only=True
    )

    class Meta:
        model = ChatRoom
        fields = [
            "id",
            "workspace",
            "name",
            "room_type",
            "room_type_display",
            "topic",
            "is_active",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "workspace", "created_by", "created_at", "updated_at"]


class ChatRoomCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatRoom
        fields = ["id", "name", "room_type", "topic"]
        read_only_fields = ["id"]

    def validate_name(self, value):
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

    def validate_room_type(self, value):
        valid_types = [t.value for t in ChatRoom.RoomType]
        if value not in valid_types:
            raise serializers.ValidationError(
                f"Invalid room type. Choose from: {', '.join(valid_types)}"
            )
        return value


class ChatRoomUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatRoom
        fields = ["name", "topic"]
        extra_kwargs = {field: {"required": False} for field in fields}

    def validate_name(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError(
                "Room name must be at least 2 characters."
            )
        return value


class MessageSerializer(serializers.Serializer):
    message_id = serializers.CharField()
    room_id = serializers.CharField()
    sender_id = serializers.CharField()
    sender_name = serializers.CharField()
    content = serializers.CharField()
    content_type = serializers.CharField(default="text")
    reply_to = serializers.CharField(required=False, default="")
    mentions = serializers.ListField(child=serializers.CharField(), default=list)
    attachment_url = serializers.CharField(required=False, default="")
    created_at = serializers.CharField()
    edited_at = serializers.CharField(required=False, default="")
    deleted_at = serializers.CharField(required=False, default="")

    class Meta:
        fields = [
            "message_id",
            "room_id",
            "sender_id",
            "sender_name",
            "content",
            "content_type",
            "reply_to",
            "mentions",
            "attachment_url",
            "created_at",
            "edited_at",
            "deleted_at",
        ]


class MessageUpdateSerializer(serializers.Serializer):
    content = serializers.CharField()

    def validate_content(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Content cannot be empty.")
        if len(value) > 10000:
            raise serializers.ValidationError(
                "Content must not exceed 10000 characters."
            )
        return value
