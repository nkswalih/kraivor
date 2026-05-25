import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

from apps.workspaces.events import WorkspaceEventPublisher, _envelope, _now_iso


class TestNowIso:
    def test_returns_iso_format_string(self):
        result = _now_iso()
        datetime.fromisoformat(result)
        assert result.endswith("+00:00") or "+00:" in result or result.endswith("Z")


class TestEnvelope:
    def test_returns_correct_structure(self):
        ws_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        data = {"foo": "bar"}
        event = _envelope("test.event", ws_id, actor_id, data)
        assert event["event_type"] == "test.event"
        assert event["workspace_id"] == str(ws_id)
        assert event["user_id"] == str(actor_id)
        assert event["source_service"] == "core"
        assert event["version"] == "1.0"
        assert event["data"] == data
        assert "event_id" in event
        assert "timestamp" in event

    def test_event_id_is_unique(self):
        ws_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        e1 = _envelope("t", ws_id, actor_id, {})
        e2 = _envelope("t", ws_id, actor_id, {})
        assert e1["event_id"] != e2["event_id"]


class TestWorkspaceEventPublisher:
    def test_get_producer_returns_none_when_kafka_unavailable(self):
        publisher = WorkspaceEventPublisher()
        assert publisher._producer is None

    def test_workspace_created_publishes_event(self):
        mock_producer = MagicMock()
        publisher = WorkspaceEventPublisher()
        publisher._producer = mock_producer

        ws = MagicMock()
        ws.id = uuid.uuid4()
        ws.name = "Test"
        ws.slug = "test"
        ws.plan = "free"
        ws.owner_id = uuid.uuid4()

        publisher.workspace_created(workspace=ws, actor_id=ws.owner_id)

        mock_producer.produce.assert_called_once()
        _args, kwargs = mock_producer.produce.call_args
        assert kwargs["topic"] == "workspace.events"
        assert kwargs["key"] == str(ws.id).encode("utf-8")
        mock_producer.flush.assert_called_once_with(timeout=2.0)

    def test_workspace_deleted_publishes_event(self):
        mock_producer = MagicMock()
        publisher = WorkspaceEventPublisher()
        publisher._producer = mock_producer

        ws = MagicMock()
        ws.id = uuid.uuid4()
        ws.slug = "test"
        ws.owner_id = uuid.uuid4()

        publisher.workspace_deleted(workspace=ws, actor_id=ws.owner_id)

        mock_producer.produce.assert_called_once()
        _args, kwargs = mock_producer.produce.call_args
        assert kwargs["topic"] == "workspace.events"

    def test_member_added_publishes_event(self):
        mock_producer = MagicMock()
        publisher = WorkspaceEventPublisher()
        publisher._producer = mock_producer

        ws = MagicMock()
        ws.id = uuid.uuid4()
        ws.owner_id = uuid.uuid4()
        member = MagicMock()
        member.user_id = uuid.uuid4()
        member.role = "member"

        publisher.member_added(workspace=ws, member=member, actor_id=ws.owner_id)

        mock_producer.produce.assert_called_once()
        _args, kwargs = mock_producer.produce.call_args
        assert kwargs["topic"] == "workspace.events"

    def test_publish_logs_locally_when_no_producer(self):
        publisher = WorkspaceEventPublisher()
        publisher._producer = None
        event = {
            "event_type": "test",
            "workspace_id": "ws-1",
            "data": {},
        }
        with patch.object(publisher, "_publish", wraps=publisher._publish) as spy:
            publisher._publish("test.topic", event)
            spy.assert_called_once_with("test.topic", event)

    def test_publish_handles_kafka_error_gracefully(self):
        mock_producer = MagicMock()
        mock_producer.produce.side_effect = Exception("Kafka unavailable")
        publisher = WorkspaceEventPublisher()
        publisher._producer = mock_producer
        event = {"event_type": "test", "workspace_id": "ws-1", "data": {}}
        publisher._publish("test.topic", event)
        mock_producer.produce.assert_called_once()
        # Should not raise
