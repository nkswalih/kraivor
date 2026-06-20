"""Tests for project and task serializers.

Covers serialization output (annotated fields present) and write-serializer
validation (required fields, custom validators).
"""
import pytest

from ..serializers import (
    ProjectCreateSerializer,
    ProjectSerializer,
    TaskCreateSerializer,
    TaskSerializer,
)


@pytest.mark.django_db
class TestProjectSerializer:
    """ProjectSerializer: serialized output includes annotations; ProjectCreateSerializer validates required fields."""
    def test_serializes_project(self, project):
        serializer = ProjectSerializer(project)
        assert serializer.data["name"] == project.name
        assert "task_count" in serializer.data
        assert "done_task_count" in serializer.data

    def test_create_serializer_valid(self, workspace, user_id):
        data = {"name": "New Project"}
        serializer = ProjectCreateSerializer(
            data=data,
            context={"workspace_id": str(workspace.id)},
        )
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["name"] == "New Project"

    def test_create_serializer_missing_name(self, workspace):
        serializer = ProjectCreateSerializer(
            data={},
            context={"workspace_id": str(workspace.id)},
        )
        assert not serializer.is_valid()
        assert "name" in serializer.errors


@pytest.mark.django_db
class TestTaskSerializer:
    """TaskSerializer: serialized output includes links/dependencies/subtask_count; TaskCreateSerializer validates required fields."""
    def test_serializes_task(self, task):
        serializer = TaskSerializer(task)
        assert serializer.data["title"] == task.title
        assert "subtask_count" in serializer.data
        assert "dependencies" in serializer.data

    def test_create_serializer_valid(self, project, workspace, user_id, workspace_member):
        data = {
            "title": "Test Task",
            "project_id": str(project.id),
            "assignee_id": user_id,
        }
        serializer = TaskCreateSerializer(
            data=data,
            context={
                "workspace_id": str(workspace.id),
                "project_id": str(project.id),
            },
        )
        assert serializer.is_valid(), serializer.errors

    def test_create_serializer_missing_title(self, project, workspace):
        serializer = TaskCreateSerializer(
            data={},
            context={
                "workspace_id": str(workspace.id),
                "project_id": str(project.id),
            },
        )
        assert not serializer.is_valid()
        assert "title" in serializer.errors
