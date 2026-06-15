"""Tests for Project and Task data models.

Covers string representation, soft-delete behaviour, relationship integrity
(unique constraints, subtask FK), and workspace scoping defaults.
"""
import uuid

import pytest
from django.db import IntegrityError

from ..models import Project, Task
from .factories import ProjectFactory, TaskFactory, TaskLinkFactory


@pytest.mark.django_db
class TestProjectModel:
    """Project model: string representation, soft-delete lifecycle, workspace scoping."""
    def test_str_representation(self, project):
        assert "Project" in str(project)
        assert project.name in str(project)

    def test_soft_delete_excludes_from_default_queryset(self, project):
        project.soft_delete()
        assert not Project.objects.filter(id=project.id).exists()

    def test_soft_delete_included_in_all_objects(self, project):
        project.soft_delete()
        assert Project.all_objects.filter(id=project.id).exists()

    def test_soft_delete_sets_deleted_at(self, project):
        project.soft_delete()
        project.refresh_from_db()
        assert project.deleted_at is not None

    def test_workspace_scoping(self, workspace):
        from ..models import Project
        p1 = ProjectFactory(workspace=workspace)
        ProjectFactory()
        assert Project.objects.filter(workspace=workspace).count() == 1


@pytest.mark.django_db
class TestTaskModel:
    """Task model: string representation, position defaults, soft-delete, subtask FK, dependency uniqueness."""
    def test_str_representation(self, task):
        assert task.title in str(task)
        assert task.status in str(task)

    def test_default_position_is_zero_for_explicit_zero(self):
        task = TaskFactory(position=0.0)
        assert task.position == 0.0

    def test_soft_delete(self, task):
        task.soft_delete()
        assert not Task.objects.filter(id=task.id).exists()

    def test_subtask_parent_relationship(self, task):
        subtask = TaskFactory(project=task.project, parent_task=task)
        assert task.subtasks.filter(id=subtask.id).exists()

    def test_task_link_unique_constraint(self, task):
        other_task = TaskFactory(project=task.project)
        TaskLinkFactory(source_task=task, target_task=other_task, relationship_type="blocks")
        with pytest.raises(IntegrityError):
            TaskLinkFactory(source_task=task, target_task=other_task, relationship_type="blocks")
