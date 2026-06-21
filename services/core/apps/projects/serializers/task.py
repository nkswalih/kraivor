import logging

from rest_framework import serializers

from ..constants import TaskLinkType, TaskPriority, TaskStatus, TaskType
from ..models import Task, TaskKnowledgeLink, TaskLink, TaskRepositoryLink

logger = logging.getLogger(__name__)


class TaskRepositoryLinkReadSerializer(serializers.ModelSerializer):
    repository_id = serializers.UUIDField(source="repository.id")
    repository_github_repo = serializers.CharField(source="repository.github_repo")

    class Meta:
        model = TaskRepositoryLink
        fields = ["id", "repository_id", "repository_github_repo"]


class TaskKnowledgeLinkReadSerializer(serializers.ModelSerializer):
    knowledge_space_id = serializers.UUIDField(source="knowledge_space.id")
    space_name = serializers.CharField(source="knowledge_space.name")

    class Meta:
        model = TaskKnowledgeLink
        fields = ["id", "knowledge_space_id", "space_name"]


class TaskDependencyReadSerializer(serializers.ModelSerializer):
    task_id = serializers.UUIDField(source="target_task.id")
    title = serializers.CharField(source="target_task.title")

    class Meta:
        model = TaskLink
        fields = ["id", "task_id", "title", "relationship_type"]


class TaskSerializer(serializers.ModelSerializer):
    repository_links = TaskRepositoryLinkReadSerializer(many=True, read_only=True)
    knowledge_links = TaskKnowledgeLinkReadSerializer(many=True, read_only=True)
    dependencies = TaskDependencyReadSerializer(
        source="outgoing_links", many=True, read_only=True
    )
    subtask_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Task
        fields = [
            "id",
            "project_id",
            "parent_task_id",
            "title",
            "description",
            "status",
            "priority",
            "task_type",
            "assignee_id",
            "reporter_id",
            "due_date",
            "estimate_points",
            "position",
            "subtask_count",
            "repository_links",
            "knowledge_links",
            "dependencies",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "reporter_id",
            "created_by",
            "created_at",
            "updated_at",
        ]


class TaskCreateSerializer(serializers.Serializer):
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
    parent_task_id = serializers.UUIDField(
        required=False, allow_null=True, default=None
    )

    def validate_parent_task_id(self, value: str | None) -> str | None:
        if value is None:
            return value

        project_id = self.context.get("project_id")
        if not Task.objects.filter(id=value, project_id=project_id).exists():
            raise serializers.ValidationError("Parent task not found in this project.")
        return value

    def validate_assignee_id(self, value: str | None) -> str | None:
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
    status = serializers.ChoiceField(choices=TaskStatus.choices)
    position = serializers.FloatField(required=False, allow_null=True, default=None)


class TaskDependencySerializer(serializers.Serializer):
    target_task_id = serializers.UUIDField()
    relationship_type = serializers.ChoiceField(choices=TaskLinkType.choices)

    def validate_target_task_id(self, value: str) -> str:
        workspace_id = self.context.get("workspace_id")
        if not Task.objects.filter(
            id=value, project__workspace_id=workspace_id
        ).exists():
            raise serializers.ValidationError(
                "Target task not found in this workspace."
            )
        return value


class TaskRepositoryLinkSerializer(serializers.Serializer):
    repository_id = serializers.UUIDField()


class TaskKnowledgeLinkSerializer(serializers.Serializer):
    knowledge_space_id = serializers.UUIDField()
