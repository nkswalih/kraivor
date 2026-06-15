"""Tests for Kafka event envelope structure and publisher behaviour.

Covers:
  - Envelope required fields, ``source_service``, and ``version``.
  - ProjectEventPublisher publishes correct event types via Kafka.
  - TaskEventPublisher publishes correct event types (created, assigned, completed,
    blocked, overdue) and verifies Kafka topic routing.
  - ``task.overdue`` bypasses ``transaction.on_commit`` (Celery context).
"""
from unittest.mock import patch

import pytest

from ..events import ProjectEventPublisher, TaskEventPublisher, _build_envelope
from .factories import ProjectFactory, TaskFactory


@pytest.mark.django_db
class TestEventEnvelope:
    """Verifies the standard event envelope structure (fields, source, version)."""
    def test_envelope_has_required_fields(self):
        envelope = _build_envelope(
            event_type="test.event",
            workspace_id="ws-123",
            user_id="user-456",
            data={"key": "value"},
        )
        required = ["event_id", "event_type", "source_service", "workspace_id",
                     "user_id", "timestamp", "version", "data"]
        for field in required:
            assert field in envelope, f"Missing field: {field}"

    def test_source_service_is_core(self):
        envelope = _build_envelope("x", "ws", "user", {})
        assert envelope["source_service"] == "core"

    def test_version_is_1_0(self):
        envelope = _build_envelope("x", "ws", "user", {})
        assert envelope["version"] == "1.0"


@pytest.mark.django_db
class TestProjectEventPublisher:
    """Project events: publish_project_created, publish_project_archived call Kafka with correct topic/envelope."""
    def test_publish_project_created_calls_kafka(self, project):
        with patch("apps.projects.events._publish") as mock_publish:
            with patch("django.db.transaction.on_commit", side_effect=lambda fn: fn()):
                ProjectEventPublisher.publish_project_created(project, "user-123")
            mock_publish.assert_called_once()
            topic, payload = mock_publish.call_args[0]
            assert topic == "project.events"
            assert payload["event_type"] == "project.created"
            assert payload["data"]["project_id"] == str(project.id)

    def test_publish_project_archived_calls_kafka(self, project):
        with patch("apps.projects.events._publish") as mock_publish:
            with patch("django.db.transaction.on_commit", side_effect=lambda fn: fn()):
                ProjectEventPublisher.publish_project_archived(project, "user-123")
            mock_publish.assert_called_once()
            _, payload = mock_publish.call_args[0]
            assert payload["event_type"] == "project.archived"


@pytest.mark.django_db
class TestTaskEventPublisher:
    """Task events: assigned, created, completed, blocked (on_commit) and overdue (no on_commit)."""
    def test_publish_task_assigned_includes_assignee_id(self, task):
        import uuid
        task.assignee_id = uuid.uuid4()
        task.save()
        with patch("apps.projects.events._publish") as mock_publish:
            with patch("django.db.transaction.on_commit", side_effect=lambda fn: fn()):
                TaskEventPublisher.publish_task_assigned(task, assigned_by="user-123")
            _, payload = mock_publish.call_args[0]
            assert payload["event_type"] == "task.assigned"
            assert payload["data"]["assignee_id"] == str(task.assignee_id)

    def test_publish_task_created_calls_kafka(self, task):
        with patch("apps.projects.events._publish") as mock_publish:
            with patch("django.db.transaction.on_commit", side_effect=lambda fn: fn()):
                TaskEventPublisher.publish_task_created(task, "user-123")
            mock_publish.assert_called_once()
            _, payload = mock_publish.call_args[0]
            assert payload["event_type"] == "task.created"

    def test_publish_task_completed_calls_kafka(self, task):
        with patch("apps.projects.events._publish") as mock_publish:
            with patch("django.db.transaction.on_commit", side_effect=lambda fn: fn()):
                TaskEventPublisher.publish_task_completed(task, "user-123")
            mock_publish.assert_called_once()
            _, payload = mock_publish.call_args[0]
            assert payload["event_type"] == "task.completed"

    def test_publish_task_blocked_calls_kafka(self, task):
        with patch("apps.projects.events._publish") as mock_publish:
            with patch("django.db.transaction.on_commit", side_effect=lambda fn: fn()):
                TaskEventPublisher.publish_task_blocked(task, "user-123")
            mock_publish.assert_called_once()
            _, payload = mock_publish.call_args[0]
            assert payload["event_type"] == "task.blocked"

    def test_publish_task_overdue_no_on_commit(self, task):
        """task.overdue is published from Celery, not inside a transaction."""
        with patch("apps.projects.events._publish") as mock_publish:
            TaskEventPublisher.publish_task_overdue(task)
            mock_publish.assert_called_once()
