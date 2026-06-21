import re

from rest_framework import serializers

from ..models import Repository


class RepositorySerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()

    class Meta:
        model = Repository
        fields = [
            "id",
            "workspace_id",
            "github_repo",
            "github_id",
            "default_branch",
            "language",
            "description",
            "is_private",
            "last_analyzed_at",
            "last_analysis_score",
            "indexed",
            "connected_by_id",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_status(self, obj: Repository) -> str:
        return "disconnected" if obj.is_deleted else "connected"


class RepositoryConnectSerializer(serializers.Serializer):
    github_repo = serializers.CharField(
        max_length=255,
        help_text="GitHub repository in 'owner/repo' format (e.g. 'acme/api').",
    )

    _GITHUB_REPO_RE = re.compile(
        r"^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?/[a-zA-Z0-9._-]+$"
    )

    def validate_github_repo(self, value: str) -> str:
        value = value.strip()
        if not self._GITHUB_REPO_RE.match(value):
            raise serializers.ValidationError(
                "Must be in 'owner/repo' format. "
                "Both owner and repo may only contain letters, digits, hyphens, "
                "underscores, and dots (e.g. 'acme/my-api')."
            )
        return value
