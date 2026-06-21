from rest_framework import serializers

from ..models import KnowledgeAsset


class KnowledgeAssetInputSerializer(serializers.Serializer):
    file = serializers.FileField(
        help_text="The file to upload (image, PDF, or document).",
    )


class KnowledgeAssetSerializer(serializers.ModelSerializer):
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
