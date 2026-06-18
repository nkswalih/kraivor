"""Pytest fixtures for the projects test suite.

Provides workspace-scoped fixtures (``workspace``, ``user_id``, ``workspace_member``,
``project``, ``task``) and ``auth_headers`` for authenticating API requests via
``HTTP_X_USER_ID`` and ``HTTP_X_WORKSPACE_ID`` headers.
"""
import uuid

import pytest

from apps.workspaces.tests.factories import WorkspaceFactory, WorkspaceMemberFactory

from .factories import ProjectFactory, TaskFactory


@pytest.fixture
def workspace():
    return WorkspaceFactory()


@pytest.fixture
def user_id():
    return str(uuid.uuid4())


@pytest.fixture
def workspace_member(workspace, user_id):
    return WorkspaceMemberFactory(workspace=workspace, user_id=user_id)


@pytest.fixture
def project(workspace, user_id):
    return ProjectFactory(workspace=workspace, owner_id=user_id, created_by=user_id)


@pytest.fixture
def task(project, user_id):
    return TaskFactory(project=project, reporter_id=user_id, created_by=user_id)


@pytest.fixture
def auth_headers(user_id, workspace):
    return {
        "HTTP_X_USER_ID": user_id,
        "HTTP_X_WORKSPACE_ID": str(workspace.id),
    }
