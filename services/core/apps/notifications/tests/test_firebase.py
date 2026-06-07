from unittest.mock import patch

from django.test import override_settings


class TestFirebaseInitialization:
    @override_settings(FIREBASE_CREDENTIALS_PATH=None)
    def test_init_without_credentials_returns_false(self):
        from apps.notifications.firebase import _initialize
        result = _initialize()
        assert result is False

    @override_settings(FIREBASE_CREDENTIALS_PATH="/fake/path.json")
    def test_init_with_invalid_credentials_returns_false(self):
        from apps.notifications.firebase import _initialize
        result = _initialize()
        assert result is False

    @override_settings(FIREBASE_CREDENTIALS_PATH="/fake/path.json")
    def test_init_success(self):
        with (
            patch("firebase_admin.initialize_app") as mock_init,
            patch("firebase_admin.credentials.Certificate") as mock_cert,
        ):
            from apps.notifications.firebase import _initialize
            mock_cert.return_value = "fake-cred"
            result = _initialize()
            assert result is True
            mock_init.assert_called_once()

    @override_settings(FIREBASE_CREDENTIALS_PATH="/fake/path.json")
    def test_init_called_only_once(self):
        with (
            patch("firebase_admin.initialize_app") as mock_init,
            patch("firebase_admin.credentials.Certificate") as mock_cert,
        ):
            mock_cert.return_value = "cred"
            from apps.notifications.firebase import _initialize
            _initialize()
            _initialize()
            assert mock_init.call_count == 1


class TestSendPushNotification:
    def test_send_without_init_falls_back_to_dev(self):
        with patch("apps.notifications.firebase._initialize", return_value=False):
            from apps.notifications.firebase import send_push_notification
            result = send_push_notification(
                token="device-token",
                title="Test",
                body="Body",
            )
            assert result["status"] == "dev_fallback"

    @override_settings(FIREBASE_CREDENTIALS_PATH="/fake/path.json")
    def test_send_success(self):
        with (
            patch("apps.notifications.firebase._initialize", return_value=True),
            patch("firebase_admin.messaging.Message") as mock_msg,
            patch("firebase_admin.messaging.send", return_value="msg-id-1") as mock_send,
        ):
            from apps.notifications.firebase import send_push_notification
            result = send_push_notification(
                token="device-token",
                title="Test Title",
                body="Test Body",
                data={"key": "value"},
            )
            assert result["status"] == "sent"
            mock_msg.assert_called_once()
            mock_send.assert_called_once()

    @override_settings(FIREBASE_CREDENTIALS_PATH="/fake/path.json")
    def test_send_failure_returns_error(self):
        with (
            patch("apps.notifications.firebase._initialize", return_value=True),
            patch("firebase_admin.messaging.send", side_effect=Exception("FCM error")),
        ):
            from apps.notifications.firebase import send_push_notification
            result = send_push_notification(
                token="bad-token",
                title="Fail",
                body="Fail",
            )
            assert result["status"] == "failed"
            assert "error" in result

    def test_send_with_data_converts_to_strings(self):
        with (
            patch("apps.notifications.firebase._initialize", return_value=True),
            patch("firebase_admin.messaging.Message") as mock_msg,
            patch("firebase_admin.messaging.send", return_value="msg-id"),
            patch.object(mock_msg, "return_value", create=True),
        ):
            from apps.notifications.firebase import send_push_notification
            result = send_push_notification(
                token="t",
                title="T",
                body="B",
                data={"count": 42, "flag": True},
            )
            assert result["status"] == "sent"
