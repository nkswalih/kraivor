"""DRF serializers for projects and tasks.

Separates read serializers (ModelSerializer, includes nested/annotated fields)
from write serializers (plain Serializer with explicit field declarations and
custom validation methods).

Design:
  - Read serializers include computed annotations like ``task_count``,
    ``blocked_task_count``, ``subtask_count`` via ``SerializerMethodField`` or
    ``IntegerField(read_only=True)`` — populated by service-layer annotations.
  - Write serializers use ``validate_<field>()`` methods for cross-field and
    cross-app validation (e.g. verifying a repository exists in the workspace).
  - Minimal serializers expose only ``id`` and a display-name field
    (``github_repo`` for repositories, ``name`` for knowledge spaces).
"""
import logging
from typing import Optional

from rest_framework import serializers

from .constants import (
    ProjectStatus,
    ProjectVisibility,
    TaskLinkType,
    TaskPriority,
    TaskStatus,
    TaskType,
)
from .models import (
    Project,
    Task,
    TaskKnowledgeLink,
    TaskLink,
    TaskRepositoryLink,
)

logger = logging.getLogger(__name__)


class RepositoryMinimalSerializer(serializers.Serializer):
    """Minimal repository representation (id + github_repo) for nested serialization."""
    id = serializers.UUIDField()
    github_repo = serializers.CharField()


class KnowledgeSpaceMinimalSerializer(serializers.Serializer):
    """Minimal knowledge space representation (id + name) for nested serialization."""
    id = serializers.UUIDField()
    name = serializers.CharField()


class TaskRepositoryLinkReadSerializer(serializers.ModelSerializer):
    """Read serializer for task-repository links; flattens the FK into id + github_repo."""
    repository_id = serializers.UUIDField(source="repository.id")
    repository_github_repo = serializers.CharField(source="repository.github_repo")

    class Meta:
        model = TaskRepositoryLink
        fields = ["id", "repository_id", "repository_github_repo"]


class TaskKnowledgeLinkReadSerializer(serializers.ModelSerializer):
    """Read serializer for task-knowledge links; flattens the FK into id + name."""
    knowledge_space_id = serializers.UUIDField(source="knowledge_space.id")
    space_name = serializers.CharField(source="knowledge_space.name")

    class Meta:
        model = TaskKnowledgeLink
        fields = ["id", "knowledge_space_id", "space_name"]


class TaskDependencyReadSerializer(serializers.ModelSerializer):
    """Read serializer for task dependencies; exposes target task id + title + relationship type."""
    task_id = serializers.UUIDField(source="target_task.id")
    title = serializers.CharField(source="target_task.title")

    class Meta:
        model = TaskLink
        fields = ["id", "task_id", "title", "relationship_type"]


class ProjectSerializer(serializers.ModelSerializer):
    """Read serializer for Project — includes nested repository/knowledge-space and annotated counts."""
    repository = RepositoryMinimalSerializer(read_only=True)
    knowledge_space = KnowledgeSpaceMinimalSerializer(read_only=True)
    task_count = serializers.IntegerField(read_only=True, default=0)
    blocked_task_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Project
        fields = [
            "id", "name", "description", "icon", "color",
            "status", "visibility", "owner_id", "created_by",
            "repository", "knowledge_space",
            "task_count", "blocked_task_count",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class ProjectCreateSerializer(serializers.Serializer):
    """Write serializer for creating a project. Validates repository/knowledge-space belong to the workspace."""
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    icon = serializers.CharField(max_length=50, required=False, allow_blank=True, default="")
    color = serializers.CharField(max_length=7, required=False, allow_blank=True, default="")
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
    knowledge_space_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    owner_id = serializers.UUIDField(required=False, allow_null=True, default=None)

    def validate_repository_id(self, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value

        from apps.repositories.models import Repository

        workspace_id = self.context.get("workspace_id")
        if not Repository.objects.filter(id=value, workspace_id=workspace_id).exists():
            raise serializers.ValidationError(
                "Repository not found in this workspace."
            )
        return value

    def validate_knowledge_space_id(self, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value

        from apps.knowledge.models import KnowledgeSpace

        workspace_id = self.context.get("workspace_id")
        if not KnowledgeSpace.objects.filter(id=value, workspace_id=workspace_id).exists():
            raise serializers.ValidationError(
                "Knowledge space not found in this workspace."
            )
        return value


class ProjectUpdateSerializer(serializers.Serializer):
    """Write serializer for updating a project — all fields optional for partial updates."""
    name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    icon = serializers.CharField(max_length=50, required=False, allow_blank=True)
    color = serializers.CharField(max_length=7, required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=ProjectStatus.choices, required=False)
    visibility = serializers.ChoiceField(choices=ProjectVisibility.choices, required=False)
    repository_id = serializers.UUIDField(required=False, allow_null=True)
    knowledge_space_id = serializers.UUIDField(required=False, allow_null=True)
    owner_id = serializers.UUIDField(required=False)


class TaskSerializer(serializers.ModelSerializer):
    """Read serializer for Task — includes nested links, dependencies, and subtask count."""
    repository_links = TaskRepositoryLinkReadSerializer(many=True, read_only=True)
    knowledge_links = TaskKnowledgeLinkReadSerializer(many=True, read_only=True)
    dependencies = TaskDependencyReadSerializer(
        source="outgoing_links", many=True, read_only=True
    )
    subtask_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Task
        fields = [
            "id", "project_id", "parent_task_id",
            "title", "description",
            "status", "priority", "task_type",
            "assignee_id", "reporter_id",
            "due_date", "estimate_points", "position",
            "subtask_count",
            "repository_links", "knowledge_links", "dependencies",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "reporter_id", "created_by", "created_at", "updated_at"]


class TaskCreateSerializer(serializers.Serializer):
    """Write serializer for creating a task. Validates parent task exists in project and assignee is a workspace member."""
    title = serializers.CharField(max_length=500)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    status = serializers.ChoiceField(
        choices=TaskStatus.choices, default=TaskStatus.BACKLOG, required=False
    )
    priority = serializers.ChoiceField(
        choices=TaskPriority.choices, default=TaskPriority.MEDIUM, required=False
    )
    task_type = serializers.ChoiceField(
        choices=TaskType.choices, default=TaskType.FEATURE, required=False
    )
    assignee_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    due_date = serializers.DateField(required=False, allow_null=True, default=None)
    estimate_points = serializers.IntegerField(
        required=False, allow_null=True, min_value=0, max_value=100, default=None
    )
    parent_task_id = serializers.UUIDField(required=False, allow_null=True, default=None)

    def validate_parent_task_id(self, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value

        project_id = self.context.get("project_id")
        if not Task.objects.filter(id=value, project_id=project_id).exists():
            raise serializers.ValidationError(
                "Parent task not found in this project."
            )
        return value

    def validate_assignee_id(self, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value

        from apps.workspaces.models import WorkspaceMember

        workspace_id = self.context.get("workspace_id")
        if not WorkspaceMember.objects.filter(
            workspace_id=workspace_id,
            user_id=value,
        ).exists():
            raise serializers.ValidationError(
                "Assignee must be an active workspace member."
            )
        return value


class TaskUpdateSerializer(serializers.Serializer):
    """Write serializer for updating a task — all fields optional for partial updates."""
    title = serializers.CharField(max_length=500, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=TaskStatus.choices, required=False)
    priority = serializers.ChoiceField(choices=TaskPriority.choices, required=False)
    task_type = serializers.ChoiceField(choices=TaskType.choices, required=False)
    assignee_id = serializers.UUIDField(required=False, allow_null=True)
    due_date = serializers.DateField(required=False, allow_null=True)
    estimate_points = serializers.IntegerField(
        required=False, allow_null=True, min_value=0, max_value=100
    )


class TaskStatusUpdateSerializer(serializers.Serializer):
    """Write serializer for the dedicated status-update endpoint. Requires ``status``, optional ``position``."""
    status = serializers.ChoiceField(choices=TaskStatus.choices)
    position = serializers.FloatField(required=False, allow_null=True, default=None)


class TaskDependencySerializer(serializers.Serializer):
    """Write serializer for creating a dependency link. Validates target task exists in the workspace."""
    target_task_id = serializers.UUIDField()
    relationship_type = serializers.ChoiceField(choices=TaskLinkType.choices)

    def validate_target_task_id(self, value: str) -> str:
        workspace_id = self.context.get("workspace_id")
        if not Task.objects.filter(
            id=value, project__workspace_id=workspace_id
        ).exists():
            raise serializers.ValidationError("Target task not found in this workspace.")
        return value


class TaskRepositoryLinkSerializer(serializers.Serializer):
    """Write serializer for linking a repository to a task."""
    repository_id = serializers.UUIDField()


class TaskKnowledgeLinkSerializer(serializers.Serializer):
    """Write serializer for linking a knowledge space to a task."""
    knowledge_space_id = serializers.UUIDField()
