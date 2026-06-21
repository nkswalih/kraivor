from collections import deque
from typing import Any

from django.db import transaction
from django.db.models import Count, Max, Q, QuerySet
from django.http import Http404
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from ..constants import (
    MAX_DEPENDENCY_DEPTH,
    POSITION_MULTIPLIER,
    POSITION_REBALANCE_THRESHOLD,
    TaskStatus,
)
from ..events import TaskEventPublisher
from ..models import Project, Task, TaskKnowledgeLink, TaskLink, TaskRepositoryLink

logger = __import__("logging").getLogger(__name__)


class TaskService:
    @staticmethod
    def list_for_project(
        project_id: str,
        status: str | None = None,
        assignee_id: str | None = None,
        priority: str | None = None,
    ) -> QuerySet:
        qs = (
            Task.objects.filter(project_id=project_id, parent_task__isnull=True)
            .prefetch_related(
                "subtasks",
                "repository_links__repository",
                "knowledge_links__knowledge_space",
                "outgoing_links__target_task",
                "incoming_links__source_task",
            )
            .annotate(
                subtask_count=Count(
                    "subtasks",
                    filter=Q(subtasks__deleted_at__isnull=True),
                )
            )
            .order_by("status", "position", "-created_at")
        )
        if status:
            qs = qs.filter(status=status)
        if assignee_id:
            qs = qs.filter(assignee_id=assignee_id)
        if priority:
            qs = qs.filter(priority=priority)
        return qs

    @staticmethod
    def list_for_workspace(workspace_id: str, **filters: Any) -> QuerySet:  # noqa: ANN401
        qs = (
            Task.objects.filter(project__workspace_id=workspace_id)
            .select_related("project")
            .prefetch_related(
                "repository_links__repository",
                "knowledge_links__knowledge_space",
                "outgoing_links__target_task",
                "incoming_links__source_task",
            )
            .order_by("-updated_at")
        )
        if filters.get("status"):
            qs = qs.filter(status=filters["status"])
        if filters.get("assignee_id"):
            qs = qs.filter(assignee_id=filters["assignee_id"])
        if filters.get("priority"):
            qs = qs.filter(priority=filters["priority"])
        if filters.get("project_id"):
            qs = qs.filter(project_id=filters["project_id"])
        return qs

    @staticmethod
    def create(
        project: Project,
        reporter_id: str,
        title: str,
        **validated_data: Any,  # noqa: ANN401
    ) -> Task:
        status = validated_data.get("status", TaskStatus.BACKLOG)
        initial_position = TaskService.calculate_initial_position(
            project_id=str(project.id),
            status=status,
        )
        task = Task.objects.create(
            project=project,
            reporter_id=reporter_id,
            created_by=reporter_id,
            title=title,
            position=initial_position,
            **validated_data,
        )
        TaskEventPublisher.publish_task_created(task, reporter_id)
        if task.assignee_id:
            TaskEventPublisher.publish_task_assigned(task, assigned_by=reporter_id)
        logger.info("Task created: id=%s project=%s", task.id, project.id)
        return task

    @staticmethod
    def get(task_id: str, workspace_id: str) -> Task:
        try:
            return (
                Task.objects.select_related("project", "parent_task")
                .prefetch_related(
                    "subtasks",
                    "repository_links__repository",
                    "knowledge_links__knowledge_space",
                    "outgoing_links__target_task",
                    "incoming_links__source_task",
                )
                .annotate(
                    subtask_count=Count(
                        "subtasks",
                        filter=Q(subtasks__deleted_at__isnull=True),
                    )
                )
                .get(id=task_id, project__workspace_id=workspace_id)
            )
        except Task.DoesNotExist:
            raise Http404(f"Task {task_id} not found.") from None

    @staticmethod
    def update(task: Task, user_id: str, **validated_data: Any) -> Task:  # noqa: ANN401
        old_assignee_id = str(task.assignee_id) if task.assignee_id else None
        old_status = task.status
        for field, value in validated_data.items():
            setattr(task, field, value)
        task.save()
        new_assignee_id = str(task.assignee_id) if task.assignee_id else None
        if new_assignee_id and new_assignee_id != old_assignee_id:
            TaskEventPublisher.publish_task_assigned(task, assigned_by=user_id)
        if task.status != old_status:
            if task.status == TaskStatus.BLOCKED:
                TaskEventPublisher.publish_task_blocked(task, user_id)
            elif task.status == TaskStatus.DONE:
                TaskEventPublisher.publish_task_completed(task, user_id)
        logger.info("Task updated: id=%s", task.id)
        return task

    @staticmethod
    def update_status(
        task: Task,
        new_status: str,
        position: float | None,
        user_id: str,
    ) -> Task:
        old_status = task.status
        task.status = new_status
        if position is not None:
            task.position = position
        else:
            task.position = TaskService.calculate_initial_position(
                project_id=str(task.project_id),
                status=new_status,
            )
        task.save(update_fields=["status", "position", "updated_at"])
        if new_status != old_status:
            if new_status == TaskStatus.BLOCKED:
                TaskEventPublisher.publish_task_blocked(task, user_id)
            elif new_status == TaskStatus.DONE:
                TaskEventPublisher.publish_task_completed(task, user_id)
        return task

    @staticmethod
    def delete(task: Task, user_id: str) -> None:
        with transaction.atomic():
            Task.objects.filter(parent_task_id=task.id).update(
                deleted_at=timezone.now()
            )
            task.soft_delete()
        logger.info("Task soft-deleted: id=%s by user=%s", task.id, user_id)

    @staticmethod
    def add_dependency(
        task: Task,
        target_task_id: str,
        relationship_type: str,
        user_id: str,
    ) -> TaskLink:
        source_id = str(task.id)
        if source_id == target_task_id:
            raise ValidationError("A task cannot depend on itself.")
        if TaskService._has_circular_dependency(source_id, target_task_id):
            raise ValidationError(
                "Adding this dependency would create a circular relationship."
            )
        try:
            link = TaskLink.objects.create(
                source_task_id=task.id,
                target_task_id=target_task_id,
                relationship_type=relationship_type,
                created_by=user_id,
            )
        except Exception:
            raise ValidationError("This dependency already exists.") from None
        return link

    @staticmethod
    def remove_dependency(task: Task, dependency_id: str) -> None:
        deleted_count, _ = TaskLink.objects.filter(
            id=dependency_id,
            source_task_id=task.id,
        ).delete()
        if deleted_count == 0:
            raise Http404(f"Dependency {dependency_id} not found.")

    @staticmethod
    def add_repository(
        task: Task,
        repository_id: str,
        workspace_id: str,
    ) -> TaskRepositoryLink:
        from apps.repositories.models import Repository

        try:
            repository = Repository.objects.get(
                id=repository_id,
                workspace_id=workspace_id,
            )
        except Repository.DoesNotExist:
            raise ValidationError("Repository not found in this workspace.") from None
        link, created = TaskRepositoryLink.objects.get_or_create(
            task=task,
            repository=repository,
        )
        if not created:
            raise ValidationError("This repository is already linked to the task.")
        return link

    @staticmethod
    def remove_repository(task: Task, link_id: str) -> None:
        deleted_count, _ = TaskRepositoryLink.objects.filter(
            id=link_id,
            task=task,
        ).delete()
        if deleted_count == 0:
            raise Http404(f"Repository link {link_id} not found.")

    @staticmethod
    def add_knowledge(
        task: Task,
        knowledge_space_id: str,
        workspace_id: str,
    ) -> TaskKnowledgeLink:
        from apps.knowledge.models import KnowledgeSpace

        try:
            knowledge_space = KnowledgeSpace.objects.get(
                id=knowledge_space_id,
                workspace_id=workspace_id,
            )
        except KnowledgeSpace.DoesNotExist:
            raise ValidationError(
                "Knowledge space not found in this workspace."
            ) from None
        link, created = TaskKnowledgeLink.objects.get_or_create(
            task=task,
            knowledge_space=knowledge_space,
        )
        if not created:
            raise ValidationError("This knowledge space is already linked to the task.")
        return link

    @staticmethod
    def remove_knowledge(task: Task, link_id: str) -> None:
        deleted_count, _ = TaskKnowledgeLink.objects.filter(
            id=link_id,
            task=task,
        ).delete()
        if deleted_count == 0:
            raise Http404(f"Knowledge link {link_id} not found.")

    @staticmethod
    def calculate_initial_position(project_id: str, status: str) -> float:
        result = Task.objects.filter(
            project_id=project_id,
            status=status,
            deleted_at__isnull=True,
        ).aggregate(max_pos=Max("position"))
        max_position = result["max_pos"] or 0.0
        return max_position + POSITION_MULTIPLIER

    @staticmethod
    def calculate_new_position(
        project_id: str,
        status: str,
        above_task_id: str | None = None,
        below_task_id: str | None = None,
    ) -> float:
        above_pos = None
        below_pos = None
        if above_task_id:
            try:
                above = Task.objects.get(
                    id=above_task_id, project_id=project_id, status=status
                )
                above_pos = above.position
            except Task.DoesNotExist:
                pass
        if below_task_id:
            try:
                below = Task.objects.get(
                    id=below_task_id, project_id=project_id, status=status
                )
                below_pos = below.position
            except Task.DoesNotExist:
                pass
        if above_pos is not None and below_pos is not None:
            gap = abs(above_pos - below_pos)
            if gap < POSITION_REBALANCE_THRESHOLD:
                TaskService._rebalance_positions(project_id, status)
                return TaskService.calculate_new_position(
                    project_id, status, above_task_id, below_task_id
                )
            return (above_pos + below_pos) / 2
        if above_pos is not None:
            return above_pos + POSITION_MULTIPLIER
        if below_pos is not None:
            if below_pos > POSITION_REBALANCE_THRESHOLD:
                return below_pos / 2
            return below_pos - POSITION_MULTIPLIER
        return TaskService.calculate_initial_position(project_id, status)

    @staticmethod
    def _rebalance_positions(project_id: str, status: str) -> None:
        tasks = list(
            Task.objects.filter(
                project_id=project_id,
                status=status,
                deleted_at__isnull=True,
            ).order_by("position", "-created_at")
        )
        with transaction.atomic():
            for index, task in enumerate(tasks, start=1):
                Task.objects.filter(id=task.id).update(
                    position=float(index) * POSITION_MULTIPLIER
                )

    @staticmethod
    def _has_circular_dependency(source_task_id: str, target_task_id: str) -> bool:
        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(target_task_id, 0)])
        while queue:
            current_id, depth = queue.popleft()
            if depth > MAX_DEPENDENCY_DEPTH:
                break
            if current_id == source_task_id:
                return True
            if current_id in visited:
                continue
            visited.add(current_id)
            outgoing_ids = TaskLink.objects.filter(
                source_task_id=current_id,
            ).values_list("target_task_id", flat=True)
            for next_id in outgoing_ids:
                queue.append((str(next_id), depth + 1))
        return False
