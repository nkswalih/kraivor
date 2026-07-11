import json

from django.test import override_settings
from unittest.mock import MagicMock, patch

from apps.notifications.management.commands.consume_events import (
    DISPATCH_TABLE,
    TOPICS,
    _build_body,
    _build_title,
    _dispatch_task,
)


class TestDispatchTable:
    def test_has_expected_entries(self):
        assert "analysis.completed" in DISPATCH_TABLE
        assert "analysis.failed" in DISPATCH_TABLE
        assert "ai.index.completed" in DISPATCH_TABLE
        assert "ai.analysis.completed" in DISPATCH_TABLE
        assert len(DISPATCH_TABLE) == 4

    def test_all_map_to_dispatch_notification(self):
        for task_name in DISPATCH_TABLE.values():
            assert task_name == "notifications.tasks.dispatch_notification"


class TestBuildTitle:
    def test_known_event_types(self):
        assert _build_title("analysis.completed", {}) == "Analysis Complete"
        assert _build_title("analysis.failed", {}) == "Analysis Failed"
        assert _build_title("ai.index.completed", {}) == "Indexing Complete"
        assert _build_title("ai.analysis.completed", {}) == "AI Analysis Complete"

    def test_unknown_event_type(self):
        result = _build_title("unknown.event", {})
        assert result == "Event: unknown.event"


class TestBuildBody:
    def test_analysis_completed(self):
        body = _build_body("analysis.completed", {"github_repo": "owner/repo"})
        assert "owner/repo" in body
        assert "analysis is complete" in body

    def test_analysis_failed(self):
        body = _build_body("analysis.failed", {"error": "timeout"})
        assert "timeout" in body

    def test_ai_index_completed(self):
        body = _build_body("ai.index.completed", {"github_repo": "org/proj"})
        assert "org/proj" in body
        assert "indexed" in body

    def test_ai_analysis_completed(self):
        body = _build_body("ai.analysis.completed", {"github_repo": "org/proj"})
        assert "org/proj" in body

    def test_unknown_event(self):
        body = _build_body("unknown.event", {"foo": "bar"})
        assert "foo" in body
        assert "bar" in body


class TestDispatchTask:
    def test_dispatches_known_event_with_user_id(self):
        mock_task = MagicMock()
        with patch(
            "celery.current_app.tasks",
            {"notifications.tasks.dispatch_notification": mock_task},
        ):
            _dispatch_task(
                "analysis.completed", {"user_id": "user-123", "github_repo": "repo"}
            )
            mock_task.delay.assert_called_once()

    def test_dispatches_known_event_with_workspace_id_fallback(self):
        mock_task = MagicMock()
        with patch(
            "celery.current_app.tasks",
            {"notifications.tasks.dispatch_notification": mock_task},
        ):
            _dispatch_task(
                "ai.index.completed", {"workspace_id": "ws-456", "github_repo": "repo"}
            )
            mock_task.delay.assert_called_once()

    def test_skips_unknown_event_type(self):
        mock_task = MagicMock()
        with patch(
            "celery.current_app.tasks",
            return_value={"notifications.tasks.dispatch_notification": mock_task},
        ):
            _dispatch_task("unknown.event", {"user_id": "u-1"})
            mock_task.delay.assert_not_called()

    def test_skips_event_without_recipient(self):
        mock_task = MagicMock()
        with patch(
            "celery.current_app.tasks",
            {"notifications.tasks.dispatch_notification": mock_task},
        ):
            _dispatch_task("analysis.completed", {})
            mock_task.delay.assert_not_called()

    def test_logs_warning_for_missing_task(self):
        with patch(
            "apps.notifications.management.commands.consume_events.logger"
        ) as mock_logger:
            _dispatch_task("analysis.completed", {"user_id": "u-1"})
            mock_logger.error.assert_called_once()


class TestCommand:
    def test_topics_constant(self):
        assert TOPICS == ["analysis.events", "ai.events", "workspace.events"]

    @override_settings(KAFKA_BOOTSTRAP_SERVERS="localhost:9092")
    def test_create_consumer_with_kafka_settings(self):
        mock_consumer = MagicMock()
        mock_consumer.poll.side_effect = [None, KeyboardInterrupt]
        with patch("confluent_kafka.Consumer", return_value=mock_consumer):
            from django.core.management import call_command

            call_command("consume_events", "--poll-timeout", "0.1")
            mock_consumer.subscribe.assert_called_once()
            mock_consumer.close.assert_called_once()

    def test_handle_missing_kafka_library(self):
        import contextlib
        import sys
        from django.core.management import call_command
        from io import StringIO

        with patch.dict("sys.modules", {"confluent_kafka": None}):
            err = StringIO()
            sys.stderr = err
            with contextlib.suppress(SystemExit):
                call_command("consume_events", "--poll-timeout", "0.1")
            sys.stderr = sys.__stderr__
            output = err.getvalue()
            assert "confluent-kafka is not installed" in output

    @override_settings(KAFKA_BOOTSTRAP_SERVERS="localhost:9092")
    def test_process_message_dispatches_event(self):
        from apps.notifications.management.commands.consume_events import Command

        cmd = Command()
        mock_msg = MagicMock()
        mock_msg.value.return_value = json.dumps(
            {
                "event_type": "analysis.completed",
                "data": {"user_id": "u-1", "github_repo": "repo"},
            }
        ).encode()
        mock_msg.topic.return_value = "analysis.events"
        with patch(
            "apps.notifications.management.commands.consume_events._dispatch_task"
        ) as mock_dispatch:
            cmd._process_message(mock_msg)
            mock_dispatch.assert_called_once()

    def test_process_message_with_null_value(self):
        from apps.notifications.management.commands.consume_events import Command

        cmd = Command()
        mock_msg = MagicMock()
        mock_msg.value.return_value = None
        with patch(
            "apps.notifications.management.commands.consume_events._dispatch_task"
        ) as mock_dispatch:
            cmd._process_message(mock_msg)
            mock_dispatch.assert_not_called()

    def test_process_message_with_invalid_json(self):
        from apps.notifications.management.commands.consume_events import Command

        cmd = Command()
        mock_msg = MagicMock()
        mock_msg.value.return_value = b"not-json"
        with patch(
            "apps.notifications.management.commands.consume_events.logger"
        ) as mock_logger:
            cmd._process_message(mock_msg)
            mock_logger.error.assert_called_once()

    def test_process_message_without_event_type(self):
        from apps.notifications.management.commands.consume_events import Command

        cmd = Command()
        mock_msg = MagicMock()
        mock_msg.value.return_value = json.dumps({"data": {}}).encode()
        with patch(
            "apps.notifications.management.commands.consume_events.logger"
        ) as mock_logger:
            cmd._process_message(mock_msg)
            mock_logger.warning.assert_called_once()

    def test_close_consumer(self):
        from apps.notifications.management.commands.consume_events import Command

        cmd = Command()
        mock_consumer = MagicMock()
        cmd._close(mock_consumer)
        mock_consumer.close.assert_called_once()

    def test_close_none_consumer(self):
        from apps.notifications.management.commands.consume_events import Command

        cmd = Command()
        cmd._close(None)
