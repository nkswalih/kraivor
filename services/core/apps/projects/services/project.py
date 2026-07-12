from typing import Any

from django.db import transaction
from django.db.models import Count, Q, QuerySet
from django.http import Http404
from django.utils import timezone

from apps.notifications.utils import fanout_to_workspace_members

from ..constants import TaskStatus
from ..events import ProjectEventPublisher
from ..models import Project, Task

logger = __import__("logging").getLogger(__name__)


class ProjectService:
    @staticmethod
    def list_for_workspace(
        workspace_id: str, status: str | None = None, user_id: str | None = None
    ) -> QuerySet:
        qs = (
            Project.objects.filter(workspace_id=workspace_id)
            .select_related("repository", "knowledge_space")
            .annotate(
                task_count=Count("tasks", filter=Q(tasks__deleted_at__isnull=True)),
                blocked_task_count=Count(
                    "tasks",
                    filter=Q(
                        tasks__deleted_at__isnull=True, tasks__status=TaskStatus.BLOCKED
                    ),
                ),
                done_task_count=Count(
                    "tasks",
                    filter=Q(
                        tasks__deleted_at__isnull=True, tasks__status=TaskStatus.DONE
                    ),
                ),
            )
            .order_by("-updated_at")
        )
        if status:
            qs = qs.filter(status=status)
        return qs

    @staticmethod
    def create(
        workspace_id: str,
        user_id: str,
        name: str,
        description: str = "",
        icon: str = "",
        color: str = "",
        status: str = "planning",
        visibility: str = "workspace",
        repository_id: str | None = None,
        knowledge_space_id: str | None = None,
        owner_id: str | None = None,
    ) -> Project:
        project = Project.objects.create(
            workspace_id=workspace_id,
            name=name,
            description=description,
            icon=icon,
            color=color,
            status=status,
            visibility=visibility,
            repository_id=repository_id,
            knowledge_space_id=knowledge_space_id,
            owner_id=owner_id or user_id,
            created_by=user_id,
        )
        ProjectEventPublisher.publish_project_created(project, user_id)

        fanout_to_workspace_members(
            workspace_id=workspace_id,
            notification_type="project.created",
            title=f"New Project: {name}",
            body=f"Project '{name}' was created in your workspace.",
            link=f"/workspaces/{workspace_id}/projects/{project.id}",
            metadata={"project_name": name, "project_status": status},
            actor_id=user_id,
            exclude_user_id=user_id,
        )

        logger.info("Project created: id=%s workspace=%s", project.id, workspace_id)
        return project

    @staticmethod
    def get(project_id: str, workspace_id: str) -> Project:
        try:
            return (
                Project.objects.select_related("repository", "knowledge_space")
                .annotate(
                    task_count=Count("tasks", filter=Q(tasks__deleted_at__isnull=True)),
                    blocked_task_count=Count(
                        "tasks",
                        filter=Q(
                            tasks__deleted_at__isnull=True,
                            tasks__status=TaskStatus.BLOCKED,
                        ),
                    ),
                    done_task_count=Count(
                        "tasks",
                        filter=Q(
                            tasks__deleted_at__isnull=True,
                            tasks__status=TaskStatus.DONE,
                        ),
                    ),
                )
                .get(id=project_id, workspace_id=workspace_id)
            )
        except Project.DoesNotExist:
            raise Http404(f"Project {project_id} not found.") from None

    @staticmethod
    def update(
        project: Project, user_id: str, **validated_data: Any
    ) -> Project:  # noqa: ANN401
        for field, value in validated_data.items():
            setattr(project, field, value)
        project.save()
        ProjectEventPublisher.publish_project_updated(project, user_id)
        logger.info("Project updated: id=%s", project.id)
        return project

    @staticmethod
    def archive(project: Project, user_id: str) -> Project:
        project.status = "archived"
        project.save(update_fields=["status", "updated_at"])
        ProjectEventPublisher.publish_project_archived(project, user_id)
        logger.info("Project archived: id=%s by user=%s", project.id, user_id)
        return project

    @staticmethod
    def delete(project: Project, user_id: str) -> None:
        with transaction.atomic():
            Task.objects.filter(project_id=project.id, deleted_at__isnull=True).update(
                deleted_at=timezone.now()
            )
            project.soft_delete()
        logger.info("Project soft-deleted: id=%s by user=%s", project.id, user_id)
