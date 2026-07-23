"""
Repository model tests — KRV-021.

Covers:
  - Field defaults
  - Soft delete lifecycle (is_deleted, delete(), hard_delete())
  - SoftDeleteManager filters (objects vs all_objects)
  - __str__ representation
  - unique_together enforcement
"""

import pytest
import uuid
from django.db import IntegrityError

from apps.repositories.models import Repository
from apps.workspaces.models import Workspace


@pytest.mark.django_db
class TestRepositoryModel:
    # ── Creation defaults ─────────────────────────────────────────────────────

    def test_creates_with_uuid_pk(self, repository):
        assert isinstance(repository.id, uuid.UUID)

    def test_default_branch_is_main(self, workspace, owner_id):
        repo = Repository.objects.create(
            workspace=workspace,
            github_repo="acme/defaults",
            github_id=111,
            connected_by_id=owner_id,
        )
        assert repo.default_branch == "main"

    def test_indexed_defaults_to_false(self, repository):
        assert repository.indexed is False

    def test_is_private_defaults_to_false(self, repository):
        assert repository.is_private is False

    def test_analysis_fields_default_to_null(self, repository):
        assert repository.last_analyzed_at is None
        assert repository.last_analysis_score is None

    def test_created_at_and_updated_at_set_on_creation(self, repository):
        assert repository.created_at is not None
        assert repository.updated_at is not None

    # ── __str__ ───────────────────────────────────────────────────────────────

    def test_str_representation(self, repository, workspace):
        assert str(repository) == f"Repository(acme/api@{workspace.slug})"

    # ── Soft delete lifecycle ─────────────────────────────────────────────────

    def test_is_deleted_false_for_active_repo(self, repository):
        assert repository.is_deleted is False

    def test_delete_sets_deleted_at(self, repository):
        repository.delete()
        assert repository.deleted_at is not None
        assert repository.is_deleted is True

    def test_soft_deleted_repo_excluded_from_default_manager(self, repository):
        repo_id = repository.id
        repository.delete()
        assert not Repository.objects.filter(id=repo_id).exists()

    def test_soft_deleted_repo_visible_via_all_objects(self, repository):
        repo_id = repository.id
        repository.delete()
        assert Repository.all_objects.filter(id=repo_id).exists()

    def test_hard_delete_removes_row_permanently(self, repository):
        repo_id = repository.id
        repository.hard_delete()
        assert not Repository.all_objects.filter(id=repo_id).exists()

    # ── unique_together enforcement ───────────────────────────────────────────

    def test_duplicate_github_id_in_same_workspace_raises_integrity_error(
        self, workspace, owner_id, repository
    ):
        with pytest.raises(IntegrityError):
            Repository.objects.create(
                workspace=workspace,
                github_repo="acme/api-fork",  # different name, same github_id
                github_id=repository.github_id,
                connected_by_id=owner_id,
            )

    def test_same_github_id_allowed_in_different_workspaces(self, workspace, owner_id):
        other_workspace = Workspace.objects.create(
            owner_id=owner_id, name="Other Workspace", slug="other-workspace"
        )
        repo1 = Repository.objects.create(
            workspace=workspace,
            github_repo="acme/shared",
            github_id=999,
            connected_by_id=owner_id,
        )
        repo2 = Repository.objects.create(
            workspace=other_workspace,
            github_repo="acme/shared",
            github_id=999,
            connected_by_id=owner_id,
        )
        assert repo1.id != repo2.id

    # ── SoftDeleteManager queryset methods ────────────────────────────────────

    def test_alive_queryset_excludes_deleted(self, workspace, owner_id, repository):
        Repository.objects.create(
            workspace=workspace,
            github_repo="acme/another",
            github_id=222,
            connected_by_id=owner_id,
        )
        repository.delete()

        alive = Repository.objects.filter(workspace=workspace)
        assert alive.count() == 1
        assert alive.first().github_id == 222

    def test_all_objects_includes_deleted(self, workspace, owner_id, repository):
        Repository.objects.create(
            workspace=workspace,
            github_repo="acme/another",
            github_id=222,
            connected_by_id=owner_id,
        )
        repository.delete()

        all_repos = Repository.all_objects.filter(workspace=workspace)
        assert all_repos.count() == 2
