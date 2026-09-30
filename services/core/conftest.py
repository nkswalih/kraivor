"""
Service-wide test isolation.

This file sits at the service root so its fixtures apply to every test
pytest collects, under both `tests/` and `apps/`.

That placement is the point. Both fixtures below used to live in
`tests/conftest.py`, which pytest only applies to the `tests/` tree. When
`testpaths` was corrected to also collect `apps/`, the newly-collected tests
ran with no DynamoDB and no broker guard — and `apps/knowledge` failed in CI
with `NoCredentialsError` purely because a developer machine happened to have
AWS credentials in its environment.

A guard that only covers part of the suite is not a guard. If you add a new
top-level test directory, this file keeps covering it.
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_chat_provisioner():
    """
    Mock the chat provisioning service so tests never hit DynamoDB.

    Workspace.post_save and WorkspaceMember.post_delete signals call
    get_provisioner(), which seeds a sequence counter in DynamoDB. Without
    this, every Workspace.objects.create() needs real AWS credentials.
    """
    mock_provisioner = MagicMock()
    with patch(
        "apps.chat.services.provisioning.get_provisioner",
        return_value=mock_provisioner,
    ):
        yield mock_provisioner


@pytest.fixture(autouse=True)
def celery_task_always_eager(settings):
    """
    Force Celery to be synchronous and keep it off any real broker.

    CELERY_TASK_ALWAYS_EAGER makes tasks execute inline without a broker.
    CELERY_TASK_EAGER_PROPAGATES stays False so a failing task surfaces in the
    task's own result rather than breaking an unrelated test.
    """
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = False
    settings.CELERY_BROKER_URL = "memory://"
    settings.CELERY_RESULT_BACKEND = "cache+memory://"
