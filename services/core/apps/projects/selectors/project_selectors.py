import uuid
from django.db.models import QuerySet

from apps.projects.models import Project, Task
from core.cache import CacheService


class ProjectSelector:
    @staticmethod
    def list_for_workspace(workspace_id: uuid.UUID) -> QuerySet[Project]:
        return (
            Project.objects.filter(
                workspace_id=workspace_id, deleted_at__isnull=True
            )
            .select_related("workspace", "repository", "knowledge_space")
            .order_by("-updated_at")
        )

    @staticmethod
    def get_detail(project_id: uuid.UUID, workspace_id: uuid.UUID) -> Project | None:
        return (
            Project.objects.select_related(
                "workspace", "repository", "knowledge_space"
            )
            .filter(id=project_id, workspace_id=workspace_id, deleted_at__isnull=True)
            .first()
        )

    @staticmethod
    def get_task_count(project_id: uuid.UUID) -> int:
        key = f"proj:task_count:{project_id}"
        return CacheService.get_or_set(
            key=key,
            timeout=60,
            fallback=lambda: Task.objects.filter(
                project_id=project_id, deleted_at__isnull=True
            ).count(),
        )


class TaskSelector:
    @staticmethod
    def list_for_project(project_id: uuid.UUID, status_filter: str | None = None) -> QuerySet[Task]:
        qs = Task.objects.filter(project_id=project_id, deleted_at__isnull=True)
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs.select_related("project").order_by("created_at")

    @staticmethod
    def get_detail(task_id: uuid.UUID, project_id: uuid.UUID) -> Task | None:
        return (
            Task.objects.select_related("project")
            .filter(id=task_id, project_id=project_id, deleted_at__isnull=True)
            .first()
        )
