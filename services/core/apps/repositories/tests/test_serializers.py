"""
Repository serializer tests — KRV-021.

Covers:
  RepositoryConnectSerializer — input validation (valid cases + all error paths)
  RepositorySerializer        — output shape and status field
"""

import uuid

import pytest

from apps.repositories.serializers import RepositoryConnectSerializer, RepositorySerializer

# ─── RepositoryConnectSerializer ─────────────────────────────────────────────


class TestRepositoryConnectSerializer:
    def test_valid_owner_slash_repo(self):
        s = RepositoryConnectSerializer(data={"github_repo": "acme/api"})
        assert s.is_valid(), s.errors

    def test_valid_with_hyphens_and_dots(self):
        s = RepositoryConnectSerializer(data={"github_repo": "my-org/my.repo"})
        assert s.is_valid(), s.errors

    def test_valid_with_underscores(self):
        s = RepositoryConnectSerializer(data={"github_repo": "org_name/repo_name"})
        assert s.is_valid(), s.errors

    def test_valid_strips_surrounding_whitespace(self):
        s = RepositoryConnectSerializer(data={"github_repo": "  acme/api  "})
        assert s.is_valid(), s.errors
        assert s.validated_data["github_repo"] == "acme/api"

    def test_invalid_missing_slash(self):
        s = RepositoryConnectSerializer(data={"github_repo": "acme-api"})
        assert not s.is_valid()
        assert "github_repo" in s.errors

    def test_invalid_double_slash(self):
        s = RepositoryConnectSerializer(data={"github_repo": "acme/api/extra"})
        assert not s.is_valid()
        assert "github_repo" in s.errors

    def test_invalid_empty_owner(self):
        s = RepositoryConnectSerializer(data={"github_repo": "/api"})
        assert not s.is_valid()
        assert "github_repo" in s.errors

    def test_invalid_empty_repo(self):
        s = RepositoryConnectSerializer(data={"github_repo": "acme/"})
        assert not s.is_valid()
        assert "github_repo" in s.errors

    def test_invalid_missing_field(self):
        s = RepositoryConnectSerializer(data={})
        assert not s.is_valid()
        assert "github_repo" in s.errors

    def test_invalid_special_characters(self):
        s = RepositoryConnectSerializer(data={"github_repo": "acme/api repo"})
        assert not s.is_valid()
        assert "github_repo" in s.errors

    def test_invalid_exceeds_max_length(self):
        long_name = "a" * 130 + "/" + "b" * 130
        s = RepositoryConnectSerializer(data={"github_repo": long_name})
        assert not s.is_valid()


# ─── RepositorySerializer ─────────────────────────────────────────────────────


@pytest.mark.django_db
class TestRepositorySerializer:
    def test_output_contains_all_expected_fields(self, repository):
        data = RepositorySerializer(repository).data
        expected_fields = {
            "id",
            "workspace_id",
            "github_repo",
            "github_id",
            "default_branch",
            "language",
            "description",
            "is_private",
            "last_analyzed_at",
            "last_analysis_score",
            "indexed",
            "connected_by_id",
            "status",
            "created_at",
            "updated_at",
        }
        assert set(data.keys()) == expected_fields

    def test_status_is_connected_for_active_repo(self, repository):
        data = RepositorySerializer(repository).data
        assert data["status"] == "connected"

    def test_status_is_disconnected_for_soft_deleted_repo(self, repository):
        repository.delete()
        data = RepositorySerializer(repository).data
        assert data["status"] == "disconnected"

    def test_id_is_string_uuid(self, repository):
        data = RepositorySerializer(repository).data
        assert isinstance(data["id"], str)
        uuid.UUID(data["id"])  # must parse without raising

    def test_workspace_id_matches_fixture(self, repository, workspace):
        data = RepositorySerializer(repository).data
        assert data["workspace_id"] == workspace.id

    def test_github_id_is_integer(self, repository):
        data = RepositorySerializer(repository).data
        assert isinstance(data["github_id"], int)

    def test_nullable_fields_can_be_null(self, workspace, owner_id):
        repo = __import__(
            "apps.repositories.models", fromlist=["Repository"]
        ).Repository.objects.create(
            workspace=workspace,
            github_repo="acme/sparse",
            github_id=55555,
            language=None,
            description=None,
            connected_by_id=None,
        )
        data = RepositorySerializer(repo).data
        assert data["language"] is None
        assert data["description"] is None
        assert data["connected_by_id"] is None
