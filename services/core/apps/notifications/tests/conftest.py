import os
import sys
import uuid
from pathlib import Path

import django
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.test")
os.environ.setdefault("DATABASE_URL", "sqlite://:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

django.setup()


@pytest.fixture
def user_id():
    return uuid.uuid4()


@pytest.fixture
def other_user_id():
    return uuid.uuid4()


@pytest.fixture
def notification(user_id, db):
    from apps.notifications.models import Notification

    return Notification.objects.create(
        user_id=user_id,
        notification_type="workspace.invitation",
        title="Test Notification",
        body="This is a test notification body",
        link="http://example.com",
    )


@pytest.fixture
def fcm_token(user_id, db):
    from apps.notifications.models import FCMToken

    return FCMToken.objects.create(
        user_id=user_id, token="test-fcm-token-12345", platform="web"
    )


@pytest.fixture
def api_request_factory():
    from rest_framework.test import APIRequestFactory

    return APIRequestFactory()


@pytest.fixture
def workspace(db):
    import uuid

    from apps.workspaces.models import Workspace

    return Workspace.objects.create(
        owner_id=uuid.uuid4(), name="Test Workspace", slug="test-workspace"
    )
