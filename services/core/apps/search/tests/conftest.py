"""
Fixtures for the search app test suite.

The search app had no tests at all, which is why the cross-workspace IDOR in
SearchView (and the broken chat search) went unnoticed. These fixtures are
deliberately minimal — the point is to prove the authorization boundary, not
to re-test the models.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import django
import os
import pytest
import sys
import uuid

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.test")
os.environ.setdefault("DATABASE_URL", "sqlite://:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

django.setup()


@pytest.fixture(autouse=True)
def mock_chat_provisioner():
    """
    Workspace creation fires signals that write to DynamoDB. Without this,
    creating a Workspace in tests fails for lack of AWS credentials.
    """
    with patch(
        "apps.chat.services.provisioning.get_provisioner",
        return_value=MagicMock(),
    ):
        yield


@pytest.fixture
def workspace(db):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(
        owner_id=uuid.uuid4(), name="Victim Workspace", slug="victim-ws"
    )


@pytest.fixture
def member(workspace, db):
    from apps.workspaces.constants import WorkspaceRole
    from apps.workspaces.models import WorkspaceMember

    return WorkspaceMember.objects.create(
        workspace=workspace,
        user_id=uuid.uuid4(),
        role=WorkspaceRole.MEMBER,
    )


@pytest.fixture
def outsider(db):
    """An authenticated user with zero relationship to `workspace`."""
    return uuid.uuid4()


@pytest.fixture
def request_factory():
    from django.test import RequestFactory

    return RequestFactory()
