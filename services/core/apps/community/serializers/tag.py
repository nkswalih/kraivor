from rest_framework import serializers

from ..models import Tag


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "slug", "description", "usage_count", "created_at"]
        read_only_fields = ["id", "usage_count", "created_at"]
