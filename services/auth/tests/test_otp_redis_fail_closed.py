"""OTP verification must fail closed when Redis is unreachable.

``OTPService.verify_otp`` previously caught ``redis.ConnectionError`` and
``redis.TimeoutError`` and returned ``True`` -- "Allow verification if Redis is
down". Redis holds the only copy of the code, so an unreachable Redis means the
``hmac.compare_digest`` never ran. Any six-digit string was therefore a valid
code for any address for as long as the outage lasted, and the endpoint issued
a real access + refresh token pair on top of it.

The three tests named ``test_accepts_*`` below are the regression: each one
asserts the bypass is gone and would pass trivially against the old code.
"""

import pytest
import redis
from authentication.otp import OTPService, OTPServiceUnavailableError
from authentication.security import reset_lockout_manager
from rest_framework.test import APIClient
from unittest.mock import MagicMock, patch

from tests.factories import UserFactory


def _service_with_broken_redis(exc: Exception) -> OTPService:
    """An OTPService whose every Redis call raises ``exc``.

    ``from_url`` does not connect, so constructing against a dummy URL is safe;
    only the client is replaced.
    """
    service = OTPService(redis_url="redis://localhost:6379/15")
    service.client = MagicMock()
    service.client.get.side_effect = exc
    service.client.pipeline.side_effect = exc
    service.client.ttl.side_effect = exc
    service.client.delete.side_effect = exc
    return service


@pytest.mark.security
class TestVerifyOTPDoesNotAcceptWhenRedisIsDown:
    def test_accepts_nothing_when_redis_connection_dies(self):
        service = _service_with_broken_redis(
            redis.exceptions.ConnectionError("connection refused")
        )

        with pytest.raises(OTPServiceUnavailableError):
            service.verify_otp("user@example.com", "000000")

    def test_accepts_nothing_when_redis_times_out(self):
        service = _service_with_broken_redis(redis.exceptions.TimeoutError("timed out"))

        with pytest.raises(OTPServiceUnavailableError):
            service.verify_otp("user@example.com", "000000")

    def test_raises_rather_than_returning_a_verdict(self):
        """The old contract was ``return True``. A bool cannot express this."""
        service = _service_with_broken_redis(redis.exceptions.ConnectionError())

        result = None
        with pytest.raises(OTPServiceUnavailableError):
            result = service.verify_otp("user@example.com", "123456")

        assert result is None

    def test_does_not_leak_the_redis_error_to_the_caller(self):
        """The message names the failure mode, not the backend."""
        service = _service_with_broken_redis(
            redis.exceptions.ConnectionError("redis://user:pw@10.0.0.5:6379 refused")
        )

        with pytest.raises(OTPServiceUnavailableError) as excinfo:
            service.verify_otp("user@example.com", "000000")

        assert "10.0.0.5" not in str(excinfo.value)
        assert "pw" not in str(excinfo.value)


@pytest.mark.security
class TestStoreAndRateLimitFailClosed:
    def test_store_raises_rather_than_reporting_success(self):
        service = _service_with_broken_redis(redis.exceptions.ConnectionError())

        with pytest.raises(OTPServiceUnavailableError):
            service.store_otp("user@example.com", "123456")

    def test_resend_check_raises_rather_than_allowing_resend(self):
        service = _service_with_broken_redis(redis.exceptions.TimeoutError())

        with pytest.raises(OTPServiceUnavailableError):
            service.check_resend_rate_limit("user@example.com")

    def test_create_and_send_does_not_return_an_unsendable_code(self):
        """A code that was never stored must not be handed to the mailer."""
        service = _service_with_broken_redis(redis.exceptions.ConnectionError())

        with pytest.raises(OTPServiceUnavailableError):
            service.create_and_send("user@example.com")


@pytest.mark.unit
class TestVerifyOTPStillWorksWhenRedisIsHealthy:
    """Guards against 'fixing' this by breaking the happy path."""

    def test_valid_code_verifies(self):
        service = OTPService(redis_url="redis://localhost:6379/15")
        client = MagicMock()
        client.get.side_effect = lambda key: (
            "123456" if key.endswith(":user@example.com") else "0"
        )
        service.client = client

        assert service.verify_otp("user@example.com", "123456") is True

    def test_missing_code_still_raises_expired(self):
        service = OTPService(redis_url="redis://localhost:6379/15")
        client = MagicMock()
        client.get.return_value = None
        service.client = client

        from authentication.otp import OTPExpiredError

        with pytest.raises(OTPExpiredError):
            service.verify_otp("user@example.com", "123456")


@pytest.mark.auth
@pytest.mark.security
class TestVerifyEndpointFailsClosed:
    def setup_method(self):
        reset_lockout_manager()

    def _post_verify(self, user, mock_svc, mock_mgr):
        with (
            patch("authentication.views.get_lockout_manager", return_value=mock_mgr),
            patch("authentication.views.get_otp_service", return_value=mock_svc),
        ):
            return APIClient().post(
                "/api/auth/signin/otp/verify/",
                {"email": user.email, "otp_code": "000000"},
                format="json",
            )

    def test_returns_503_instead_of_a_token_pair(self, db):
        user = UserFactory.verified()

        mock_svc = MagicMock()
        mock_svc.verify_otp.side_effect = OTPServiceUnavailableError("nope")

        mock_mgr = MagicMock()
        mock_mgr.check_lockout.return_value = (False, 0)

        response = self._post_verify(user, mock_svc, mock_mgr)

        assert response.status_code == 503
        assert response.json()["error_code"] == "otp_service_unavailable"

    def test_issues_no_token_material(self, db):
        """The bypass handed out a working session. Prove nothing is issued."""
        user = UserFactory.verified()

        mock_svc = MagicMock()
        mock_svc.verify_otp.side_effect = OTPServiceUnavailableError("nope")

        mock_mgr = MagicMock()
        mock_mgr.check_lockout.return_value = (False, 0)

        body = self._post_verify(user, mock_svc, mock_mgr).json()

        assert "access_token" not in body
        assert "refresh_token" not in body
        assert "user" not in body

    def test_does_not_count_the_outage_as_a_failed_attempt(self, db):
        """A Redis blip must not lock every legitimate user out."""
        user = UserFactory.verified()

        mock_svc = MagicMock()
        mock_svc.verify_otp.side_effect = OTPServiceUnavailableError("nope")

        mock_mgr = MagicMock()
        mock_mgr.check_lockout.return_value = (False, 0)

        self._post_verify(user, mock_svc, mock_mgr)

        mock_mgr.record_failure.assert_not_called()
        mock_mgr.clear_attempts.assert_not_called()

    def test_still_returns_401_for_a_genuinely_wrong_code(self, db):
        """The outage path must not swallow real OTP failures."""
        from authentication.otp import OTPInvalidError

        user = UserFactory.verified()

        mock_svc = MagicMock()
        mock_svc.verify_otp.side_effect = OTPInvalidError("Invalid OTP code.")

        mock_mgr = MagicMock()
        mock_mgr.check_lockout.return_value = (False, 0)

        response = self._post_verify(user, mock_svc, mock_mgr)

        assert response.status_code == 401
        assert response.json()["error_code"] == "invalid_otp"
        mock_mgr.record_failure.assert_called_once()


@pytest.mark.auth
@pytest.mark.security
class TestSendEndpointFailsClosed:
    def setup_method(self):
        reset_lockout_manager()

    def test_returns_503_when_the_code_cannot_be_stored(self, db):
        user = UserFactory.verified()

        mock_svc = MagicMock()
        mock_svc.create_and_send.side_effect = OTPServiceUnavailableError("nope")

        mock_mgr = MagicMock()
        mock_mgr.check_lockout.return_value = (False, 0)

        with (
            patch("authentication.views.get_lockout_manager", return_value=mock_mgr),
            patch("authentication.views.get_otp_service", return_value=mock_svc),
            patch("authentication.views.get_otp_sender") as mock_sender,
        ):
            response = APIClient().post(
                "/api/auth/signin/otp/send/", {"email": user.email}, format="json"
            )

        assert response.status_code == 503
        assert response.json()["error_code"] == "otp_service_unavailable"
        mock_sender.return_value.send.assert_not_called()

    def test_keeps_the_rate_limit_distinct_from_the_outage(self, db):
        """429 is a user problem; 503 is ours. They must not be conflated."""
        from authentication.otp import OTPRateLimitError

        user = UserFactory.verified()

        mock_svc = MagicMock()
        mock_svc.create_and_send.side_effect = OTPRateLimitError(retry_after=42)

        mock_mgr = MagicMock()
        mock_mgr.check_lockout.return_value = (False, 0)

        with (
            patch("authentication.views.get_lockout_manager", return_value=mock_mgr),
            patch("authentication.views.get_otp_service", return_value=mock_svc),
            patch("authentication.views.get_otp_sender"),
        ):
            response = APIClient().post(
                "/api/auth/signin/otp/send/", {"email": user.email}, format="json"
            )

        assert response.status_code == 429
        assert response.json()["error_code"] == "rate_limit_exceeded"
        assert response.json()["retry_after"] == 42
