import os
import sys
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import django
import pytest
from django.test import RequestFactory
from django.utils import timezone

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.test")
os.environ.setdefault("DATABASE_URL", "sqlite://:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

django.setup()


@pytest.fixture
def workspace(db):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(
        owner_id=uuid.uuid4(),
        name="Test Workspace",
        slug="test-workspace",
    )


@pytest.fixture
def owner_member(workspace, db):
    from apps.workspaces.constants import WorkspaceRole
    from apps.workspaces.models import WorkspaceMember

    return WorkspaceMember.objects.create(
        workspace=workspace,
        user_id=workspace.owner_id,
        role=WorkspaceRole.OWNER,
        joined_at=timezone.now(),
    )


@pytest.fixture
def admin_member(workspace, db):
    from apps.workspaces.constants import WorkspaceRole
    from apps.workspaces.models import WorkspaceMember

    return WorkspaceMember.objects.create(
        workspace=workspace,
        user_id=uuid.uuid4(),
        role=WorkspaceRole.ADMIN,
        joined_at=timezone.now(),
    )


@pytest.fixture
def regular_member(workspace, db):
    from apps.workspaces.constants import WorkspaceRole
    from apps.workspaces.models import WorkspaceMember

    return WorkspaceMember.objects.create(
        workspace=workspace,
        user_id=uuid.uuid4(),
        role=WorkspaceRole.MEMBER,
        joined_at=timezone.now(),
    )


@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.fixture
def mock_event_publisher():
    return MagicMock()
