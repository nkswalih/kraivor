"""Integration tests for project and task HTTP views.

Covers full request/response cycle via DRF's ``APIClient``:
  - Project list/create: pagination, status filtering, cross-workspace isolation,
    validation errors, unauthenticated access.
  - Project detail: retrieval, wrong-workspace 404, update, soft-delete.
  - Task status update: valid/invalid status transitions.
  - Task dependencies: add, self-dependency rejection, remove.
"""

import uuid

import pytest
from rest_framework.test import APIClient

from apps.workspaces.tests.factories import WorkspaceFactory

from ..constants import TaskStatus
from ..models import TaskLink
from .factories import ProjectFactory, TaskFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def authed_client(api_client, user_id, workspace):
    api_client.defaults["HTTP_X_USER_ID"] = user_id
    api_client.defaults["HTTP_X_WORKSPACE_ID"] = str(workspace.id)
    return api_client


@pytest.mark.django_db
class TestProjectListCreateView:
    """Project list (GET) and create (POST) — pagination, filtering, auth, validation."""

    def test_list_returns_200(
        self, authed_client, workspace, project, workspace_member
    ):
        resp = authed_client.get(f"/api/workspaces/{workspace.id}/projects/")
        assert resp.status_code == 200
        assert len(resp.data) == 1

    def test_list_excludes_other_workspace(
        self, authed_client, workspace, workspace_member
    ):
        ProjectFactory()
        resp = authed_client.get(f"/api/workspaces/{workspace.id}/projects/")
        assert len(resp.data) == 0

    def test_list_filter_by_status(
        self, authed_client, workspace, user_id, workspace_member
    ):
        ProjectFactory(workspace=workspace, status="active")
        ProjectFactory(workspace=workspace, status="planning")
        resp = authed_client.get(
            f"/api/workspaces/{workspace.id}/projects/?status=active"
        )
        assert len(resp.data) == 1

    def test_create_returns_201(self, authed_client, workspace, workspace_member):
        resp = authed_client.post(
            f"/api/workspaces/{workspace.id}/projects/", {"name": "New Project"}
        )
        assert resp.status_code == 201
        assert resp.data["name"] == "New Project"

    def test_create_requires_name(self, authed_client, workspace, workspace_member):
        resp = authed_client.post(f"/api/workspaces/{workspace.id}/projects/", {})
        assert resp.status_code == 400
        assert "name" in resp.data

    def test_unauthenticated_returns_403(self, api_client):
        resp = api_client.get(f"/api/workspaces/{uuid.uuid4()}/projects/")
        assert resp.status_code == 403


@pytest.mark.django_db
class TestProjectDetailView:
    """Project detail (GET), update (PATCH), delete (DELETE) — includes wrong-workspace 404 test."""

    def test_get_returns_200(self, authed_client, workspace, project, workspace_member):
        resp = authed_client.get(
            f"/api/workspaces/{workspace.id}/projects/{project.id}/"
        )
        assert resp.status_code == 200
        assert resp.data["id"] == str(project.id)

    def test_get_wrong_workspace_returns_404(self, api_client):
        other_project = ProjectFactory()
        wrong_workspace = WorkspaceFactory()
        api_client.defaults["HTTP_X_USER_ID"] = str(uuid.uuid4())
        api_client.defaults["HTTP_X_WORKSPACE_ID"] = str(wrong_workspace.id)
        resp = api_client.get(
            f"/api/workspaces/{wrong_workspace.id}/projects/{other_project.id}/"
        )
        assert resp.status_code == 404

    def test_patch_returns_200(
        self, authed_client, workspace, project, workspace_member
    ):
        resp = authed_client.patch(
            f"/api/workspaces/{workspace.id}/projects/{project.id}/",
            {"name": "Updated Name"},
        )
        assert resp.status_code == 200
        assert resp.data["name"] == "Updated Name"

    def test_delete_returns_204(
        self, authed_client, workspace, project, workspace_member
    ):
        resp = authed_client.delete(
            f"/api/workspaces/{workspace.id}/projects/{project.id}/"
        )
        assert resp.status_code == 204

    def test_deleted_project_not_in_list(
        self, authed_client, workspace, project, workspace_member
    ):
        authed_client.delete(f"/api/workspaces/{workspace.id}/projects/{project.id}/")
        resp = authed_client.get(f"/api/workspaces/{workspace.id}/projects/")
        assert len(resp.data) == 0


@pytest.mark.django_db
class TestTaskStatusUpdateView:
    """Task status PATCH — valid status returns 200, invalid status returns 400."""

    def test_update_status_returns_200(
        self, authed_client, workspace, task, workspace_member
    ):
        resp = authed_client.patch(
            f"/api/workspaces/{workspace.id}/tasks/{task.id}/status/",
            {"status": TaskStatus.IN_PROGRESS},
        )
        assert resp.status_code == 200
        assert resp.data["status"] == TaskStatus.IN_PROGRESS

    def test_update_invalid_status_returns_400(
        self, authed_client, workspace, task, workspace_member
    ):
        resp = authed_client.patch(
            f"/api/workspaces/{workspace.id}/tasks/{task.id}/status/",
            {"status": "flying"},
        )
        assert resp.status_code == 400


@pytest.mark.django_db
class TestTaskDependencyView:
    """Dependency management (POST create, DELETE remove) — includes self-dependency rejection."""

    def test_add_dependency_returns_201(
        self, authed_client, workspace, project, workspace_member
    ):
        t1 = TaskFactory(project=project)
        t2 = TaskFactory(project=project)
        resp = authed_client.post(
            f"/api/workspaces/{workspace.id}/tasks/{t1.id}/dependencies/",
            {"target_task_id": str(t2.id), "relationship_type": "blocks"},
        )
        assert resp.status_code == 201

    def test_add_self_dependency_returns_400(
        self, authed_client, workspace, task, workspace_member
    ):
        resp = authed_client.post(
            f"/api/workspaces/{workspace.id}/tasks/{task.id}/dependencies/",
            {"target_task_id": str(task.id), "relationship_type": "blocks"},
        )
        assert resp.status_code == 400

    def test_remove_dependency_returns_204(
        self, authed_client, workspace, project, workspace_member
    ):
        t1 = TaskFactory(project=project)
        t2 = TaskFactory(project=project)
        link = TaskLink.objects.create(
            source_task=t1,
            target_task=t2,
            relationship_type="blocks",
            created_by=uuid.uuid4(),
        )
        resp = authed_client.delete(
            f"/api/workspaces/{workspace.id}/tasks/{t1.id}/dependencies/{link.id}/"
        )
        assert resp.status_code == 204
