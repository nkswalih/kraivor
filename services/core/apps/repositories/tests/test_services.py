"""
Repository service tests — KRV-021.

Tests are grouped by service method. All GitHub I/O is mocked via the
mock_github_token and mock_github_api fixtures defined in conftest.py.

Note on soft-delete checks:
  TimestampedModel.delete() sets deleted_at on the in-memory Python instance
  AND persists it via save(). After calling service.disconnect_repository(),
  the `repository` fixture variable already has deleted_at set — no
  refresh_from_db() is needed (and it would fail anyway because
  SoftDeleteManager filters deleted rows out of the default queryset).

Covers:
  connect_repository  — happy path (new + restore), permission, duplicate,
                         GitHub auth error, GitHub API error
  list_repositories   — returns active repos only, ordered newest-first
  disconnect_repository — happy path, permission, not found
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from apps.repositories.models import Repository
from apps.repositories.services import (
    GitHubAPIError,
    GitHubAuthError,
    RepositoryAlreadyConnectedError,
    RepositoryNotFoundError,
    RepositoryPermissionError,
    RepositoryService,
)

# ─── connect_repository ───────────────────────────────────────────────────────


@pytest.mark.django_db(transaction=True)
class TestConnectRepository:
    def _service(self, mock_events=None):
        """Return a RepositoryService with a mocked event publisher."""
        publisher = mock_events or MagicMock()
        return RepositoryService(event_publisher=publisher)

    # ── Happy path — new repository ───────────────────────────────────────────

    def test_creates_repository_row(
        self,
        workspace,
        owner_member,
        owner_id,
        mock_github_token,
        mock_github_api,
        github_repo_payload,
    ):
        repo = self._service().connect_repository(
            workspace=workspace,
            actor_id=owner_id,
            github_repo="acme/new-service",
        )
        assert repo.pk is not None
        assert repo.github_repo == github_repo_payload["full_name"]
        assert repo.github_id == github_repo_payload["id"]

    def test_stores_metadata_from_github(
        self,
        workspace,
        owner_member,
        owner_id,
        mock_github_token,
        mock_github_api,
        github_repo_payload,
    ):
        repo = self._service().connect_repository(
            workspace=workspace,
            actor_id=owner_id,
            github_repo="acme/new-service",
        )
        assert repo.default_branch == github_repo_payload["default_branch"]
        assert repo.language == github_repo_payload["language"]
        assert repo.description == github_repo_payload["description"]
        assert repo.is_private == github_repo_payload["private"]

    def test_sets_connected_by_id(
        self,
        workspace,
        owner_member,
        owner_id,
        mock_github_token,
        mock_github_api,
    ):
        repo = self._service().connect_repository(
            workspace=workspace,
            actor_id=owner_id,
            github_repo="acme/new-service",
        )
        assert repo.connected_by_id == owner_id

    def test_new_repo_not_indexed(
        self,
        workspace,
        owner_member,
        owner_id,
        mock_github_token,
        mock_github_api,
    ):
        repo = self._service().connect_repository(
            workspace=workspace,
            actor_id=owner_id,
            github_repo="acme/new-service",
        )
        assert repo.indexed is False

    def test_admin_can_connect(
        self,
        workspace,
        admin_member,
        admin_id,
        mock_github_token,
        mock_github_api,
    ):
        repo = self._service().connect_repository(
            workspace=workspace,
            actor_id=admin_id,
            github_repo="acme/new-service",
        )
        assert repo.pk is not None

    def test_event_scheduled_after_commit(
        self,
        workspace,
        owner_member,
        owner_id,
        mock_github_token,
        mock_github_api,
    ):
        # transaction.on_commit fires immediately in tests (no real transaction
        # wrapping the test body), so the publisher is called synchronously.
        publisher = MagicMock()
        self._service(publisher).connect_repository(
            workspace=workspace,
            actor_id=owner_id,
            github_repo="acme/new-service",
        )
        publisher.repository_connected.assert_called_once()
        call_kwargs = publisher.repository_connected.call_args.kwargs
        assert call_kwargs["actor_id"] == owner_id
        assert call_kwargs["repository"].github_id == 987654321

    # ── Happy path — restore soft-deleted repository ──────────────────────────

    def test_restores_soft_deleted_repo(
        self,
        workspace,
        owner_member,
        owner_id,
        repository,
        mock_github_token,
    ):
        """
        Connecting a previously disconnected repo should restore the existing
        row (same PK) rather than creating a new one, so that historical
        analysis data retains its foreign key reference.
        """
        original_id = repository.id
        repository.delete()
        # TimestampedModel.delete() sets deleted_at on the in-memory instance
        assert repository.is_deleted

        restored_payload = {
            "id": repository.github_id,
            "full_name": "acme/api",
            "default_branch": "develop",  # metadata may have changed on GitHub
            "language": "Go",
            "description": "Updated description",
            "private": True,
        }
        with patch(
            "apps.repositories.services.GitHubAPIClient.get_repository",
            return_value=restored_payload,
        ):
            repo = self._service().connect_repository(
                workspace=workspace,
                actor_id=owner_id,
                github_repo="acme/api",
            )

        assert repo.id == original_id  # same primary key preserved
        assert repo.deleted_at is None  # soft-delete cleared
        assert repo.default_branch == "develop"  # metadata refreshed
        assert repo.language == "Go"
        assert repo.indexed is False  # re-indexing required
        assert repo.last_analyzed_at is None  # analysis reset

    # ── Permission errors ─────────────────────────────────────────────────────

    def test_member_cannot_connect(
        self,
        workspace,
        regular_member,
        member_id,
        mock_github_token,
        mock_github_api,
    ):
        with pytest.raises(RepositoryPermissionError):
            self._service().connect_repository(
                workspace=workspace,
                actor_id=member_id,
                github_repo="acme/new-service",
            )

    def test_viewer_cannot_connect(
        self,
        workspace,
        viewer_member,
        viewer_id,
        mock_github_token,
        mock_github_api,
    ):
        with pytest.raises(RepositoryPermissionError):
            self._service().connect_repository(
                workspace=workspace,
                actor_id=viewer_id,
                github_repo="acme/new-service",
            )

    def test_non_member_cannot_connect(
        self,
        workspace,
        owner_member,
        outsider_id,
        mock_github_token,
        mock_github_api,
    ):
        with pytest.raises(RepositoryPermissionError):
            self._service().connect_repository(
                workspace=workspace,
                actor_id=outsider_id,
                github_repo="acme/new-service",
            )

    # ── Duplicate error ───────────────────────────────────────────────────────

    def test_raises_already_connected_if_active_repo_exists(
        self,
        workspace,
        owner_member,
        owner_id,
        repository,
        mock_github_token,
    ):
        # repository fixture uses github_id=123456789; mock GitHub to return same ID
        existing_payload = {
            "id": repository.github_id,
            "full_name": "acme/api",
            "default_branch": "main",
            "language": "Python",
            "description": None,
            "private": False,
        }
        with (
            patch(
                "apps.repositories.services.GitHubAPIClient.get_repository",
                return_value=existing_payload,
            ),
            pytest.raises(RepositoryAlreadyConnectedError),
        ):
            self._service().connect_repository(
                workspace=workspace,
                actor_id=owner_id,
                github_repo="acme/api",
            )

    # ── GitHub integration errors ─────────────────────────────────────────────

    def test_raises_github_auth_error_when_no_token(
        self,
        workspace,
        owner_member,
        owner_id,
    ):
        with (
            patch(
                "apps.repositories.services.GitHubTokenClient.get_token",
                side_effect=GitHubAuthError("No GitHub account connected."),
            ),
            pytest.raises(GitHubAuthError),
        ):
            self._service().connect_repository(
                workspace=workspace,
                actor_id=owner_id,
                github_repo="acme/new-service",
            )

    def test_raises_github_api_error_when_repo_not_found(
        self,
        workspace,
        owner_member,
        owner_id,
        mock_github_token,
    ):
        with (
            patch(
                "apps.repositories.services.GitHubAPIClient.get_repository",
                side_effect=GitHubAPIError("Repository not found."),
            ),
            pytest.raises(GitHubAPIError),
        ):
            self._service().connect_repository(
                workspace=workspace,
                actor_id=owner_id,
                github_repo="acme/nonexistent",
            )

    def test_no_db_row_created_when_github_api_fails(
        self,
        workspace,
        owner_member,
        owner_id,
        mock_github_token,
    ):
        """GitHub errors before the DB write must leave the DB unchanged."""
        count_before = Repository.objects.filter(workspace=workspace).count()
        with (
            patch(
                "apps.repositories.services.GitHubAPIClient.get_repository",
                side_effect=GitHubAPIError("GitHub error"),
            ),
            pytest.raises(GitHubAPIError),
        ):
            self._service().connect_repository(
                workspace=workspace,
                actor_id=owner_id,
                github_repo="acme/fail",
            )
        assert Repository.objects.filter(workspace=workspace).count() == count_before


# ─── list_repositories ────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestListRepositories:
    def test_returns_active_repos_for_workspace(self, workspace, owner_member, repository):
        repos = list(RepositoryService().list_repositories(workspace=workspace))
        assert len(repos) == 1
        assert repos[0].id == repository.id

    def test_excludes_soft_deleted_repos(self, workspace, owner_member, repository):
        repository.delete()
        repos = list(RepositoryService().list_repositories(workspace=workspace))
        assert len(repos) == 0

    def test_excludes_repos_from_other_workspaces(
        self,
        workspace,
        owner_member,
        owner_id,
        repository,
    ):
        from apps.workspaces.models import Workspace

        other_workspace = Workspace.objects.create(
            owner_id=owner_id,
            name="Other",
            slug="other-ws",
        )
        Repository.objects.create(
            workspace=other_workspace,
            github_repo="acme/api",
            github_id=999,
            connected_by_id=owner_id,
        )
        repos = list(RepositoryService().list_repositories(workspace=workspace))
        assert len(repos) == 1
        assert repos[0].id == repository.id

    def test_ordered_newest_first(self, workspace, owner_member, owner_id, repository):
        newer = Repository.objects.create(
            workspace=workspace,
            github_repo="acme/newer",
            github_id=222,
            connected_by_id=owner_id,
        )
        repos = list(RepositoryService().list_repositories(workspace=workspace))
        assert repos[0].id == newer.id
        assert repos[1].id == repository.id

    def test_returns_empty_queryset_for_workspace_with_no_repos(
        self,
        workspace,
        owner_member,
    ):
        repos = list(RepositoryService().list_repositories(workspace=workspace))
        assert repos == []


# ─── disconnect_repository ────────────────────────────────────────────────────


@pytest.mark.django_db(transaction=True)
class TestDisconnectRepository:
    def _service(self, mock_events=None):
        publisher = mock_events or MagicMock()
        return RepositoryService(event_publisher=publisher)

    # ── Happy path ────────────────────────────────────────────────────────────

    def test_soft_deletes_repository(self, workspace, owner_member, owner_id, repository):
        # TimestampedModel.delete() mutates the in-memory instance, so we can
        # check is_deleted directly without re-fetching from the DB.
        self._service().disconnect_repository(
            workspace=workspace,
            actor_id=owner_id,
            repository_id=repository.id,
        )
        repo = Repository.all_objects.get(id=repository.id)
        assert repo.is_deleted

    def test_admin_can_disconnect(self, workspace, admin_member, admin_id, repository):
        self._service().disconnect_repository(
            workspace=workspace,
            actor_id=admin_id,
            repository_id=repository.id,
        )
        repo = Repository.all_objects.get(id=repository.id)
        assert repo.is_deleted

    def test_disconnected_repo_absent_from_active_queryset(
        self,
        workspace,
        owner_member,
        owner_id,
        repository,
    ):
        repo_id = repository.id
        self._service().disconnect_repository(
            workspace=workspace,
            actor_id=owner_id,
            repository_id=repository.id,
        )
        assert not Repository.objects.filter(id=repo_id).exists()

    def test_disconnected_repo_visible_via_all_objects(
        self,
        workspace,
        owner_member,
        owner_id,
        repository,
    ):
        repo_id = repository.id
        self._service().disconnect_repository(
            workspace=workspace,
            actor_id=owner_id,
            repository_id=repository.id,
        )
        assert Repository.all_objects.filter(id=repo_id).exists()

    def test_event_scheduled_after_commit(
        self,
        workspace,
        owner_member,
        owner_id,
        repository,
    ):
        publisher = MagicMock()
        self._service(publisher).disconnect_repository(
            workspace=workspace,
            actor_id=owner_id,
            repository_id=repository.id,
        )
        publisher.repository_disconnected.assert_called_once()
        call_kwargs = publisher.repository_disconnected.call_args.kwargs
        assert call_kwargs["actor_id"] == owner_id
        assert call_kwargs["repository"].id == repository.id

    # ── Permission errors ─────────────────────────────────────────────────────

    def test_member_cannot_disconnect(
        self,
        workspace,
        regular_member,
        member_id,
        repository,
    ):
        with pytest.raises(RepositoryPermissionError):
            self._service().disconnect_repository(
                workspace=workspace,
                actor_id=member_id,
                repository_id=repository.id,
            )

    def test_viewer_cannot_disconnect(
        self,
        workspace,
        viewer_member,
        viewer_id,
        repository,
    ):
        with pytest.raises(RepositoryPermissionError):
            self._service().disconnect_repository(
                workspace=workspace,
                actor_id=viewer_id,
                repository_id=repository.id,
            )

    def test_outsider_cannot_disconnect(
        self,
        workspace,
        owner_member,
        outsider_id,
        repository,
    ):
        with pytest.raises(RepositoryPermissionError):
            self._service().disconnect_repository(
                workspace=workspace,
                actor_id=outsider_id,
                repository_id=repository.id,
            )

    # ── Not-found errors ──────────────────────────────────────────────────────

    def test_raises_not_found_for_nonexistent_repo(
        self,
        workspace,
        owner_member,
        owner_id,
    ):
        with pytest.raises(RepositoryNotFoundError):
            self._service().disconnect_repository(
                workspace=workspace,
                actor_id=owner_id,
                repository_id=uuid.uuid4(),
            )

    def test_raises_not_found_for_already_disconnected_repo(
        self,
        workspace,
        owner_member,
        owner_id,
        repository,
    ):
        repository.delete()  # soft-delete sets deleted_at on in-memory instance
        with pytest.raises(RepositoryNotFoundError):
            self._service().disconnect_repository(
                workspace=workspace,
                actor_id=owner_id,
                repository_id=repository.id,
            )

    def test_raises_not_found_for_repo_in_different_workspace(
        self,
        workspace,
        owner_member,
        owner_id,
        repository,
    ):
        from apps.workspaces.constants import WorkspaceRole
        from apps.workspaces.models import Workspace, WorkspaceMember

        other_workspace = Workspace.objects.create(
            owner_id=owner_id,
            name="Other",
            slug="other-ws2",
        )
        WorkspaceMember.objects.create(
            workspace=other_workspace,
            user_id=owner_id,
            role=WorkspaceRole.OWNER,
        )
        with pytest.raises(RepositoryNotFoundError):
            self._service().disconnect_repository(
                workspace=other_workspace,
                actor_id=owner_id,
                repository_id=repository.id,
            )
