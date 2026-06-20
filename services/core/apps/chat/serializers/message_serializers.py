
from rest_framework import serializers


class MessageSerializer(serializers.Serializer):
    message_id: serializers.CharField = serializers.CharField()
    room_id: serializers.CharField = serializers.CharField()
    sender_id: serializers.CharField = serializers.CharField()
    sender_name: serializers.CharField = serializers.CharField()
    content: serializers.CharField = serializers.CharField()
    content_type: serializers.CharField = serializers.CharField(default="text")
    reply_to: serializers.CharField = serializers.CharField(required=False, default="")
    mentions: serializers.ListField = serializers.ListField(child=serializers.CharField(), default=list)
    attachment_url: serializers.CharField = serializers.CharField(required=False, default="")
    created_at: serializers.CharField = serializers.CharField()
    edited_at: serializers.CharField = serializers.CharField(required=False, default="")
    deleted_at: serializers.CharField = serializers.CharField(required=False, default="")

    class Meta:
        fields: list[str] = [
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
    content: serializers.CharField = serializers.CharField()

    def validate_content(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Content cannot be empty.")
        if len(value) > 10000:
            raise serializers.ValidationError("Content must not exceed 10000 characters.")
        return value


class SendMessageSerializer(serializers.Serializer):
    content: serializers.CharField = serializers.CharField()
    content_type: serializers.CharField = serializers.CharField(default="text")
    mentions: serializers.ListField = serializers.ListField(
        child=serializers.CharField(), default=list
    )
    reply_to: serializers.CharField = serializers.CharField(
        required=False, allow_null=True, default=""
    )

    def validate_content(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Content cannot be empty.")
        return value
