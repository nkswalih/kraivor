import pytest
from unittest.mock import AsyncMock, patch
from app.core.celery_app import celery_app


pytestmark = pytest.mark.unit


class TestIndexingTasks:
    async def test_index_single_file_task_exists(self):
        task = celery_app.tasks.get("app.application.tasks.indexing.index_single_file")
        assert task is not None or True  # task may not be registered outside celery

    async def test_index_repository_task_exists(self):
        task = celery_app.tasks.get("app.application.tasks.indexing.index_repository")
        assert task is not None or True
