"""
Repository view tests — KRV-021.

Strategy: use APIRequestFactory to build requests with request.user_id set
directly, bypassing JWTAuthenticationMiddleware. The service layer is mocked
where needed so view tests remain fast and free of GitHub I/O.

Note on soft-delete checks:
  TimestampedModel.delete() mutates the in-memory Python instance, setting
  deleted_at immediately. Tests that check disconnection use the in-memory
  instance directly; no refresh_from_db() is required (and it would raise
  DoesNotExist since SoftDeleteManager excludes deleted rows).

Views under test:
  RepositoryView       — GET list, POST connect
  RepositoryDetailView — DELETE disconnect

Scenarios covered:
  - Authentication (missing user_id → 403)
  - Workspace membership (non-member → 404)
  - Role-based access (member cannot write → 403)
  - Success responses (correct status codes + shapes)
  - Input validation (invalid github_repo → 400)
  - Service error translation (PermissionError → 403, NotFoundError → 404, etc.)
"""

import uuid
from unittest.mock import patch

import pytest
from rest_framework import status

from apps.repositories.models import Repository
from apps.repositories.views import RepositoryDetailView, RepositoryView

from .conftest import make_request

# ─── GET /workspaces/{workspace_pk}/repos/ ────────────────────────────────────


@pytest.mark.django_db
class TestRepositoryListView:
    def _call(self, workspace, user_id):
        request = make_request("get", "/api/workspaces/x/repos/", user_id)
        return RepositoryView.as_view()(request, workspace_pk=workspace.id)

    def test_returns_200_for_active_member(
        self, workspace, regular_member, member_id, repository
    ):
        response = self._call(workspace, member_id)
        assert response.status_code == status.HTTP_200_OK

    def test_returns_repository_list(
        self, workspace, owner_member, owner_id, repository
    ):
        response = self._call(workspace, owner_id)
        assert len(response.data) == 1
        assert response.data[0]["github_repo"] == repository.github_repo

    def test_returns_empty_list_when_no_repos(self, workspace, owner_member, owner_id):
        response = self._call(workspace, owner_id)
        assert response.status_code == status.HTTP_200_OK
        assert response.data == []

    def test_excludes_disconnected_repos(
        self, workspace, owner_member, owner_id, repository
    ):
        repository.delete()
        response = self._call(workspace, owner_id)
        assert response.data == []

    def test_returns_404_for_non_member(self, workspace, outsider_id):
        response = self._call(workspace, outsider_id)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_returns_403_when_no_user_id(self, workspace):
        from rest_framework.test import APIRequestFactory

        raw = APIRequestFactory().get("/api/workspaces/x/repos/", format="json")
        # Deliberately do NOT set raw.user_id
        response = RepositoryView.as_view()(raw, workspace_pk=workspace.id)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_viewer_can_list(self, workspace, viewer_member, viewer_id, repository):
        response = self._call(workspace, viewer_id)
        assert response.status_code == status.HTTP_200_OK


# ─── POST /workspaces/{workspace_pk}/repos/ ───────────────────────────────────


@pytest.mark.django_db
class TestRepositoryConnectView:
    _PAYLOAD = {"github_repo": "acme/new-service"}

    def _call(self, workspace, user_id, data=None):
        request = make_request(
            "post", "/api/workspaces/x/repos/", user_id, data=data or self._PAYLOAD
        )
        return RepositoryView.as_view()(request, workspace_pk=workspace.id)

    def test_returns_201_for_owner(
        self,
        workspace,
        owner_member,
        owner_id,
        mock_github_token,
        mock_github_api,
        github_app_installation_repo,
        mock_github_app_client,
    ):
        response = self._call(workspace, owner_id)
        assert response.status_code == status.HTTP_201_CREATED

    def test_returns_201_for_admin(
        self,
        workspace,
        admin_member,
        admin_id,
        mock_github_token,
        mock_github_api,
        github_app_installation_repo,
        mock_github_app_client,
    ):
        response = self._call(workspace, admin_id)
        assert response.status_code == status.HTTP_201_CREATED

    def test_response_contains_github_repo(
        self,
        workspace,
        owner_member,
        owner_id,
        mock_github_token,
        mock_github_api,
        github_repo_payload,
        github_app_installation_repo,
        mock_github_app_client,
    ):
        response = self._call(workspace, owner_id)
        assert response.data["github_repo"] == github_repo_payload["full_name"]

    def test_response_status_is_connected(
        self,
        workspace,
        owner_member,
        owner_id,
        mock_github_token,
        mock_github_api,
        github_app_installation_repo,
        mock_github_app_client,
    ):
        response = self._call(workspace, owner_id)
        assert response.data["status"] == "connected"

    def test_response_contains_workspace_id(
        self,
        workspace,
        owner_member,
        owner_id,
        mock_github_token,
        mock_github_api,
        github_app_installation_repo,
        mock_github_app_client,
    ):
        response = self._call(workspace, owner_id)
        assert response.data["workspace_id"] == workspace.id

    def test_returns_403_for_member_role(
        self, workspace, regular_member, member_id, mock_github_token, mock_github_api
    ):
        response = self._call(workspace, member_id)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_returns_403_for_viewer_role(
        self, workspace, viewer_member, viewer_id, mock_github_token, mock_github_api
    ):
        response = self._call(workspace, viewer_id)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_returns_404_for_non_member(self, workspace, outsider_id):
        response = self._call(workspace, outsider_id)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_returns_400_for_invalid_github_repo_format(
        self, workspace, owner_member, owner_id
    ):
        response = self._call(workspace, owner_id, data={"github_repo": "not-valid"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "github_repo" in response.data

    def test_returns_400_for_missing_github_repo(
        self, workspace, owner_member, owner_id
    ):
        response = self._call(workspace, owner_id, data={})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_returns_400_when_already_connected(
        self, workspace, owner_member, owner_id, mock_github_token
    ):
        from apps.repositories.services import RepositoryAlreadyConnectedError

        with patch(
            "apps.repositories.views.RepositoryService.connect_repository",
            side_effect=RepositoryAlreadyConnectedError("Already connected."),
        ):
            response = self._call(workspace, owner_id)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Already connected." in str(response.data)

    def test_returns_400_for_github_auth_error(self, workspace, owner_member, owner_id):
        from apps.repositories.services import GitHubAuthError

        with patch(
            "apps.repositories.views.RepositoryService.connect_repository",
            side_effect=GitHubAuthError("No GitHub account connected."),
        ):
            response = self._call(workspace, owner_id)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_returns_400_for_github_api_error(self, workspace, owner_member, owner_id):
        from apps.repositories.services import GitHubAPIError

        with patch(
            "apps.repositories.views.RepositoryService.connect_repository",
            side_effect=GitHubAPIError("Repository not found."),
        ):
            response = self._call(workspace, owner_id)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ─── DELETE /workspaces/{workspace_pk}/repos/{repo_id}/ ──────────────────────


@pytest.mark.django_db
class TestRepositoryDisconnectView:
    def _call(self, workspace, user_id, repo_id):
        request = make_request("delete", f"/api/workspaces/x/repos/{repo_id}/", user_id)
        return RepositoryDetailView.as_view()(
            request, workspace_pk=workspace.id, repo_id=repo_id
        )

    def test_returns_204_for_owner(self, workspace, owner_member, owner_id, repository):
        response = self._call(workspace, owner_id, repository.id)
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_returns_204_for_admin(self, workspace, admin_member, admin_id, repository):
        response = self._call(workspace, admin_id, repository.id)
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_repo_is_soft_deleted_after_disconnect(
        self, workspace, owner_member, owner_id, repository
    ):
        # TimestampedModel.delete() sets deleted_at on the in-memory instance.
        # No refresh_from_db() required (it would raise DoesNotExist because
        # SoftDeleteManager excludes deleted rows from the default queryset).
        self._call(workspace, owner_id, repository.id)
        assert Repository.all_objects.get(id=repository.id).is_deleted

    def test_returns_403_for_member_role(
        self, workspace, regular_member, member_id, repository
    ):
        response = self._call(workspace, member_id, repository.id)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_returns_403_for_viewer_role(
        self, workspace, viewer_member, viewer_id, repository
    ):
        response = self._call(workspace, viewer_id, repository.id)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_returns_404_for_nonexistent_repo(self, workspace, owner_member, owner_id):
        response = self._call(workspace, owner_id, uuid.uuid4())
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_returns_404_for_already_disconnected_repo(
        self, workspace, owner_member, owner_id, repository
    ):
        repository.delete()
        response = self._call(workspace, owner_id, repository.id)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_returns_404_for_non_member(self, workspace, outsider_id, repository):
        # Non-members see 404 (workspace not found) before the repo lookup —
        # avoids leaking whether a workspace exists.
        response = self._call(workspace, outsider_id, repository.id)
        assert response.status_code == status.HTTP_404_NOT_FOUND
