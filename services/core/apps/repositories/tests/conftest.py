"""
Shared pytest fixtures for the repositories app test suite — KRV-021.

Fixture hierarchy:
  user IDs          — plain UUIDs (no DB row; identity is a separate service)
  workspace         — Workspace DB row + owner WorkspaceMember
  member rows       — additional WorkspaceMember rows per role
  repository        — a connected Repository row for use in disconnect / list tests

GitHub mock helpers:
  github_repo_payload   — raw dict matching GitHub API /repos/{owner}/{repo} shape
  mock_github_token     — patches GitHubTokenClient.get_token
  mock_github_api       — patches GitHubAPIClient.get_repository

Request factory helper:
  make_request()        — builds a DRF-compatible request with request.user_id set,
                          bypassing middleware (no JWT verification in unit tests).
                          DRF's Request.__getattr__ delegates to _request so attributes
                          set on the raw WSGIRequest are accessible on the wrapper.
"""

import uuid
from unittest.mock import patch

import pytest
from rest_framework.test import APIRequestFactory

from apps.repositories.models import Repository
from apps.workspaces.constants import WorkspacePlan, WorkspaceRole
from apps.workspaces.models import Workspace, WorkspaceMember

# ─── API request factory ──────────────────────────────────────────────────────

_factory = APIRequestFactory()


def make_request(method: str, path: str, user_id: uuid.UUID, data=None):
    """
    Build a raw DRF request with user_id set directly on the underlying
    WSGIRequest, bypassing JWTAuthenticationMiddleware.

    DRF wraps the raw request in Request(raw_request) inside APIView.dispatch().
    Request.__getattr__ delegates unknown attribute lookups to _request, so
    `drf_request.user_id` resolves to `raw_request.user_id` correctly.
    """
    req_fn = getattr(_factory, method)
    kwargs = {"format": "json"}
    if data is not None:
        kwargs["data"] = data
    raw = req_fn(path, **kwargs)
    raw.user_id = user_id
    return raw


# ─── User IDs (no DB rows — identity is a separate service) ──────────────────


@pytest.fixture
def owner_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def admin_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def member_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def viewer_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def outsider_id() -> uuid.UUID:
    """A user UUID that has no WorkspaceMember row — not in the workspace."""
    return uuid.uuid4()


# ─── Workspace + members ──────────────────────────────────────────────────────


@pytest.fixture
def workspace(owner_id) -> Workspace:
    return Workspace.objects.create(
        owner_id=owner_id,
        name="Test Workspace",
        slug="test-workspace",
        plan=WorkspacePlan.FREE,
    )


@pytest.fixture
def owner_member(workspace, owner_id) -> WorkspaceMember:
    return WorkspaceMember.objects.create(
        workspace=workspace,
        user_id=owner_id,
        role=WorkspaceRole.OWNER,
    )


@pytest.fixture
def admin_member(workspace, admin_id) -> WorkspaceMember:
    return WorkspaceMember.objects.create(
        workspace=workspace,
        user_id=admin_id,
        role=WorkspaceRole.ADMIN,
    )


@pytest.fixture
def regular_member(workspace, member_id) -> WorkspaceMember:
    return WorkspaceMember.objects.create(
        workspace=workspace,
        user_id=member_id,
        role=WorkspaceRole.MEMBER,
    )


@pytest.fixture
def viewer_member(workspace, viewer_id) -> WorkspaceMember:
    return WorkspaceMember.objects.create(
        workspace=workspace,
        user_id=viewer_id,
        role=WorkspaceRole.VIEWER,
    )


# ─── Repository ───────────────────────────────────────────────────────────────


@pytest.fixture
def repository(workspace, owner_id) -> Repository:
    """A connected (active) repository in the test workspace."""
    return Repository.objects.create(
        workspace=workspace,
        github_repo="acme/api",
        github_id=123456789,
        default_branch="main",
        language="Python",
        description="Test repository",
        is_private=False,
        connected_by_id=owner_id,
    )


# ─── GitHub API mock helpers ──────────────────────────────────────────────────


@pytest.fixture
def github_repo_payload() -> dict:
    """
    A minimal but realistic GitHub REST API /repos/{owner}/{repo} response.
    Covers all fields that GitHubAPIClient.extract_metadata() reads.
    """
    return {
        "id": 987654321,
        "full_name": "acme/new-service",
        "default_branch": "main",
        "language": "Python",
        "description": "A brand new service",
        "private": False,
    }


@pytest.fixture
def mock_github_token():
    """
    Patch GitHubTokenClient.get_token to return a fake token without making
    any HTTP call to the auth service.
    """
    with patch(
        "apps.repositories.services.GitHubTokenClient.get_token",
        return_value="ghp_fake_token_for_tests",
    ) as mock:
        yield mock


@pytest.fixture
def mock_github_api(github_repo_payload):
    """
    Patch GitHubAPIClient.get_repository to return the github_repo_payload
    fixture without making any HTTP call to api.github.com.
    """
    with patch(
        "apps.repositories.services.GitHubAPIClient.get_repository",
        return_value=github_repo_payload,
    ) as mock:
        yield mock


# ─── GitHub App installation fixtures ──────────────────────────────────────────


@pytest.fixture
def github_app_installation(workspace, owner_id):
    """Create a GitHubAppInstallation row in the test workspace."""
    from apps.repositories.github_app.models import GitHubAppInstallation

    return GitHubAppInstallation.objects.create(
        workspace=workspace,
        installation_id=12345678,
        github_account_id=87654321,
        github_account_login="test-org",
        github_account_type="Organization",
        installed_by_id=owner_id,
    )


@pytest.fixture
def github_app_installation_repo(github_app_installation, github_repo_payload):
    """Create a GitHubAppInstallationRepo row linking the installation to the test repo."""
    from apps.repositories.github_app.models import GitHubAppInstallationRepo

    return GitHubAppInstallationRepo.objects.create(
        installation=github_app_installation,
        github_id=github_repo_payload["id"],
        github_repo=github_repo_payload["full_name"],
        default_branch=github_repo_payload.get("default_branch", "main"),
        is_private=github_repo_payload.get("private", False),
    )


@pytest.fixture
def mock_github_app_client(github_repo_payload):
    """
    Patch GitHubAppClient.get_repository to return the github_repo_payload
    fixture without making any HTTP call to api.github.com.
    """
    with patch(
        "apps.repositories.services.GitHubAppClient.get_repository",
        return_value=github_repo_payload,
    ) as mock:
        yield mock
