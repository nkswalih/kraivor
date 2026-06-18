"""
Shared pytest fixtures for the knowledge app test suite — KRV-022.

Fixture hierarchy:
  user IDs         — plain UUIDs (no DB row; identity is a separate service)
  workspace        — Workspace DB row
  member rows      — WorkspaceMember rows for each role
  knowledge_space  — a KnowledgeSpace DB row for use in update/delete/retrieve tests

make_request():
  Builds a DRF-compatible request with request.user_id set directly on the
  underlying WSGIRequest, bypassing JWTAuthenticationMiddleware.
  DRF's Request.__getattr__ delegates unknown attribute lookups to _request,
  so drf_request.user_id resolves to raw_request.user_id transparently.
"""

import uuid

import pytest
from rest_framework.test import APIRequestFactory

from apps.knowledge.models import KnowledgeSpace
from apps.workspaces.constants import WorkspacePlan, WorkspaceRole
from apps.workspaces.models import Workspace, WorkspaceMember

# ─── Request factory helper ───────────────────────────────────────────────────

_factory = APIRequestFactory()


def make_request(method: str, path: str, user_id: uuid.UUID, data=None):
    """
    Build a raw DRF request with user_id pre-set on the underlying WSGIRequest,
    bypassing the JWT authentication middleware entirely.

    For GET requests, passing data= sets query parameters.
    For POST/PUT requests, data= is the request body (JSON-encoded via format="json").
    """
    req_fn = getattr(_factory, method)
    kwargs = {"format": "json"}
    if data is not None:
        kwargs["data"] = data
    raw = req_fn(path, **kwargs)
    raw.user_id = user_id
    return raw


# ─── User IDs ─────────────────────────────────────────────────────────────────


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
    """A UUID with no WorkspaceMember row — not in the workspace."""
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
        workspace=workspace, user_id=owner_id, role=WorkspaceRole.OWNER
    )


@pytest.fixture
def admin_member(workspace, admin_id) -> WorkspaceMember:
    return WorkspaceMember.objects.create(
        workspace=workspace, user_id=admin_id, role=WorkspaceRole.ADMIN
    )


@pytest.fixture
def regular_member(workspace, member_id) -> WorkspaceMember:
    return WorkspaceMember.objects.create(
        workspace=workspace, user_id=member_id, role=WorkspaceRole.MEMBER
    )


@pytest.fixture
def viewer_member(workspace, viewer_id) -> WorkspaceMember:
    return WorkspaceMember.objects.create(
        workspace=workspace, user_id=viewer_id, role=WorkspaceRole.VIEWER
    )


# ─── KnowledgeSpace ───────────────────────────────────────────────────────────


@pytest.fixture
def knowledge_space(workspace, owner_id) -> KnowledgeSpace:
    """An active knowledge space owned by owner_id for use in all tests."""
    return KnowledgeSpace.objects.create(
        workspace=workspace,
        name="Authentication System",
        description="Diagrams and notes about the auth flow.",
        canvas_data={"nodes": [], "edges": []},
        created_by=owner_id,
        updated_by=None,
    )
