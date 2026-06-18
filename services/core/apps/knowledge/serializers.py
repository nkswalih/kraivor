from rest_framework import serializers

from .models import KnowledgeAsset, KnowledgeSpace


class KnowledgeSpaceListSerializer(serializers.ModelSerializer):
    workspace_id = serializers.UUIDField()

    class Meta:
        model = KnowledgeSpace
        fields = [
            "id",
            "workspace_id",
            "name",
            "description",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class KnowledgeSpaceSerializer(serializers.ModelSerializer):
    workspace_id = serializers.UUIDField()

    class Meta:
        model = KnowledgeSpace
        fields = [
            "id",
            "workspace_id",
            "name",
            "description",
            "canvas_data",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class KnowledgeSpaceCreateSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=255, help_text="Name for this canvas (e.g. 'Authentication System')."
    )
    description = serializers.CharField(
        max_length=1000,
        required=False,
        allow_blank=True,
        allow_null=True,
        default=None,
        help_text="Optional description of the canvas purpose and scope.",
    )
    canvas_data = serializers.JSONField(
        required=False,
        default=dict,
        help_text="Initial canvas state. Defaults to an empty canvas ({}).",
    )

    def validate_name(self, value: str) -> str:
        value = value.strip()
        if len(value) < 1:
            raise serializers.ValidationError("Name must not be blank.")
        return value

    def validate_canvas_data(self, value) -> dict:
        if not isinstance(value, dict):
            raise serializers.ValidationError(
                "canvas_data must be a JSON object, not an array or scalar."
            )
        return value


class KnowledgeSpaceUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=255, help_text="Updated name for this canvas."
    )
    description = serializers.CharField(
        max_length=1000,
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Updated description. Omit to keep the existing value.",
    )
    canvas_data = serializers.JSONField(
        required=False,
        help_text=(
            "Full canvas state replacement. Omit to keep the existing canvas. "
            "When provided, replaces the entire canvas_data atomically."
        ),
    )

    def validate_name(self, value: str) -> str:
        value = value.strip()
        if len(value) < 1:
            raise serializers.ValidationError("Name must not be blank.")
        return value

    def validate_canvas_data(self, value) -> dict:
        if not isinstance(value, dict):
            raise serializers.ValidationError(
                "canvas_data must be a JSON object, not an array or scalar."
            )
        return value


class KnowledgeAssetInputSerializer(serializers.Serializer):
    file = serializers.FileField(
        help_text="The file to upload (image, PDF, or document).",
    )


class KnowledgeAssetSerializer(serializers.ModelSerializer):
    knowledge_space_id = serializers.UUIDField(source="knowledge_space_id")

    class Meta:
        model = KnowledgeAsset
        fields = [
            "id",
            "knowledge_space_id",
            "file_name",
            "file_size",
            "file_type",
            "mime_type",
            "storage_key",
            "url",
            "uploaded_by",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
