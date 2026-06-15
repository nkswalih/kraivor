"""Tests for ProjectService and TaskService business logic.

Covers:
  - ProjectService: creation defaults, status filtering, cross-workspace isolation,
    soft-delete cascade, event publishing.
  - TaskService: creation, initial position calculation, status transition events
    (blocked, done), self-reference and circular-dependency validation.
  - Overdue task detection: background Celery task correctly identifies and
    publishes overdue events, skips terminal-status tasks.
"""
import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from ..constants import ProjectStatus, TaskStatus
from ..services import ProjectService, TaskService
from .factories import ProjectFactory, TaskFactory


@pytest.mark.django_db
class TestProjectService:
    """ProjectService: create, list, filter by status, soft-delete, cross-workspace isolation, events."""
    def test_create_sets_created_by(self, workspace, user_id):
        project = ProjectService.create(
            workspace_id=str(workspace.id), user_id=user_id, name="Test"
        )
        assert str(project.created_by) == user_id

    def test_create_defaults_owner_to_creator(self, workspace, user_id):
        project = ProjectService.create(
            workspace_id=str(workspace.id), user_id=user_id, name="Test"
        )
        assert str(project.owner_id) == user_id

    def test_list_filters_by_status(self, workspace, user_id):
        ProjectFactory(workspace=workspace, status=ProjectStatus.ACTIVE)
        ProjectFactory(workspace=workspace, status=ProjectStatus.PLANNING)
        active = ProjectService.list_for_workspace(
            workspace_id=str(workspace.id), status=ProjectStatus.ACTIVE
        )
        assert active.count() == 1

    def test_list_excludes_deleted(self, workspace, project):
        project.soft_delete()
        qs = ProjectService.list_for_workspace(workspace_id=str(workspace.id))
        assert qs.count() == 0

    def test_get_wrong_workspace_raises_404(self, project):
        from django.http import Http404
        with pytest.raises(Http404):
            ProjectService.get(project_id=str(project.id), workspace_id=str(uuid.uuid4()))

    def test_delete_soft_deletes_project_and_tasks(self, project, user_id):
        TaskFactory(project=project)
        TaskFactory(project=project)
        ProjectService.delete(project=project, user_id=user_id)
        from ..models import Project, Task
        assert not Project.objects.filter(id=project.id).exists()
        assert Task.objects.filter(project=project).count() == 0

    def test_create_publishes_event(self, workspace, user_id):
        with patch("apps.projects.services.ProjectEventPublisher.publish_project_created") as mock:
            ProjectService.create(
                workspace_id=str(workspace.id), user_id=user_id, name="Test"
            )
            mock.assert_called_once()


@pytest.mark.django_db
class TestTaskService:
    """TaskService: create, initial position, status transition events, dependency validation (self/circular)."""
    def test_create_task(self, project, user_id):
        task = TaskService.create(project=project, reporter_id=user_id, title="My Task")
        assert task.title == "My Task"
        assert str(task.reporter_id) == user_id

    def test_create_sets_initial_position(self, project, user_id):
        task = TaskService.create(project=project, reporter_id=user_id, title="Task A")
        assert task.position > 0

    def test_update_status_publishes_blocked_event(self, task, user_id):
        with patch("apps.projects.services.TaskEventPublisher.publish_task_blocked") as mock:
            TaskService.update_status(
                task=task, new_status=TaskStatus.BLOCKED, position=None, user_id=user_id
            )
            mock.assert_called_once()

    def test_update_status_publishes_done_event(self, task, user_id):
        with patch("apps.projects.services.TaskEventPublisher.publish_task_completed") as mock:
            TaskService.update_status(
                task=task, new_status=TaskStatus.DONE, position=None, user_id=user_id
            )
            mock.assert_called_once()

    def test_add_dependency_self_reference_raises(self, task, user_id):
        from rest_framework.exceptions import ValidationError
        with pytest.raises(ValidationError, match="itself"):
            TaskService.add_dependency(
                task=task,
                target_task_id=str(task.id),
                relationship_type="blocks",
                user_id=user_id,
            )

    def test_add_dependency_circular_raises(self, project, user_id):
        from rest_framework.exceptions import ValidationError
        task_a = TaskFactory(project=project)
        task_b = TaskFactory(project=project)
        TaskService.add_dependency(task_a, str(task_b.id), "blocks", user_id)
        with pytest.raises(ValidationError, match="circular"):
            TaskService.add_dependency(task_b, str(task_a.id), "blocks", user_id)

    def test_calculate_initial_position_starts_at_1000(self, project):
        pos = TaskService.calculate_initial_position(
            project_id=str(project.id), status=TaskStatus.BACKLOG
        )
        assert pos == 1000.0

    def test_calculate_initial_position_increments(self, project):
        TaskFactory(project=project, status=TaskStatus.TODO, position=1000.0)
        pos = TaskService.calculate_initial_position(
            project_id=str(project.id), status=TaskStatus.TODO
        )
        assert pos == 2000.0


@pytest.mark.django_db
class TestCheckOverdueTasks:
    """Overdue detection: publishes events for overdue tasks, skips done/cancelled tasks."""
    def test_publishes_event_for_overdue_task(self, project):
        from ..tasks import check_overdue_tasks
        TaskFactory(
            project=project,
            status=TaskStatus.IN_PROGRESS,
            due_date=timezone.localdate() - timedelta(days=1),
        )
        with patch("apps.projects.events.TaskEventPublisher.publish_task_overdue") as mock:
            check_overdue_tasks()
            mock.assert_called_once()

    def test_skips_done_tasks(self, project):
        from ..tasks import check_overdue_tasks
        TaskFactory(
            project=project,
            status=TaskStatus.DONE,
            due_date=timezone.localdate() - timedelta(days=1),
        )
        with patch("apps.projects.events.TaskEventPublisher.publish_task_overdue") as mock:
            check_overdue_tasks()
            mock.assert_not_called()
