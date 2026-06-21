import logging

from rest_framework import serializers

from ..constants import ProjectStatus, ProjectVisibility
from ..models import Project

logger = logging.getLogger(__name__)


class RepositoryMinimalSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    github_repo = serializers.CharField()


class KnowledgeSpaceMinimalSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()


class ProjectSerializer(serializers.ModelSerializer):
    repository = RepositoryMinimalSerializer(read_only=True)
    knowledge_space = KnowledgeSpaceMinimalSerializer(read_only=True)
    task_count = serializers.IntegerField(read_only=True, default=0)
    blocked_task_count = serializers.IntegerField(read_only=True, default=0)
    done_task_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Project
        fields = [
            "id",
            "name",
            "description",
            "icon",
            "color",
            "status",
            "visibility",
            "owner_id",
            "created_by",
            "repository",
            "knowledge_space",
            "task_count",
            "blocked_task_count",
            "done_task_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class ProjectCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    icon = serializers.CharField(
        max_length=50, required=False, allow_blank=True, default=""
    )
    color = serializers.CharField(
        max_length=7, required=False, allow_blank=True, default=""
    )
    status = serializers.ChoiceField(
        choices=ProjectStatus.choices,
        default=ProjectStatus.PLANNING,
        required=False,
    )
    visibility = serializers.ChoiceField(
        choices=ProjectVisibility.choices,
        default=ProjectVisibility.WORKSPACE,
        required=False,
    )
    repository_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    knowledge_space_id = serializers.UUIDField(
        required=False, allow_null=True, default=None
    )
    owner_id = serializers.UUIDField(required=False, allow_null=True, default=None)

    def validate_repository_id(self, value: str | None) -> str | None:
        if value is None:
            return value

        from apps.repositories.models import Repository

        workspace_id = self.context.get("workspace_id")
        if not Repository.objects.filter(id=value, workspace_id=workspace_id).exists():
            raise serializers.ValidationError("Repository not found in this workspace.")
        return value

    def validate_knowledge_space_id(self, value: str | None) -> str | None:
        if value is None:
            return value

        from apps.knowledge.models import KnowledgeSpace

        workspace_id = self.context.get("workspace_id")
        if not KnowledgeSpace.objects.filter(
            id=value, workspace_id=workspace_id
        ).exists():
            raise serializers.ValidationError(
                "Knowledge space not found in this workspace."
            )
        return value


class ProjectUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    icon = serializers.CharField(max_length=50, required=False, allow_blank=True)
    color = serializers.CharField(max_length=7, required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=ProjectStatus.choices, required=False)
    visibility = serializers.ChoiceField(
        choices=ProjectVisibility.choices, required=False
    )
    repository_id = serializers.UUIDField(required=False, allow_null=True)
    knowledge_space_id = serializers.UUIDField(required=False, allow_null=True)
    owner_id = serializers.UUIDField(required=False)
