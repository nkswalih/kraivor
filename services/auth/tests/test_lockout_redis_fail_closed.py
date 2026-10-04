"""Login lockout must fail closed when Redis is unreachable.

`LoginLockoutManager.check_lockout` caught `redis.ConnectionError` and
`redis.TimeoutError` and returned `(False, 0)` -- "not locked". Redis holds the
only record of failed attempts, so an unreachable Redis means the lockout state
was never read. Returning "not locked" is not a degraded answer, it is an
explicit clearance: unlimited password guessing against every account for as
long as the outage lasted.

`record_failure` had the matching shape, returning 0 so the counter never
advanced past the threshold.

Verified against the pre-fix code: with `client.ttl` raising
`ConnectionError`, `check_lockout("user@example.com", "1.2.3.4")` returned
`(False, 0)`.

`clear_attempts` is deliberately still best-effort. It runs after the
credentials have already been accepted, so raising there would reject a login
that genuinely succeeded. `TestClearAttemptsStaysBestEffort` pins that
asymmetry so it is not "fixed" by a later reader who misses the reasoning.
"""

import pytest
import redis
from authentication.security import (
    LoginLockoutManager,
    LoginLockoutUnavailableError,
    reset_lockout_manager,
)
from rest_framework.test import APIClient
from unittest.mock import MagicMock, patch

from tests.factories import UserFactory


def _manager_with_broken_redis(exc: Exception) -> LoginLockoutManager:
    """A LoginLockoutManager whose every Redis call raises ``exc``.

    ``from_url`` does not connect, so constructing against a dummy URL is safe;
    only the client is replaced.
    """
    mgr = LoginLockoutManager(redis_url="redis://localhost:6379/15")
    mgr.client = MagicMock()
    mgr.client.ttl.side_effect = exc
    mgr.client.pipeline.side_effect = exc
    return mgr


@pytest.mark.security
class TestCheckLockoutDoesNotClearWhenRedisIsDown:
    def test_raises_instead_of_reporting_not_locked(self):
        mgr = _manager_with_broken_redis(redis.exceptions.ConnectionError("refused"))

        with pytest.raises(LoginLockoutUnavailableError):
            mgr.check_lockout("user@example.com", "1.2.3.4")

    def test_raises_on_timeout_too(self):
        mgr = _manager_with_broken_redis(redis.exceptions.TimeoutError("timed out"))

        with pytest.raises(LoginLockoutUnavailableError):
            mgr.check_lockout("user@example.com", "1.2.3.4")

    def test_never_returns_the_not_locked_tuple(self):
        """The old contract was `(False, 0)`. A tuple cannot express this."""
        mgr = _manager_with_broken_redis(redis.exceptions.ConnectionError())

        result = ("unset", "unset")
        with pytest.raises(LoginLockoutUnavailableError):
            result = mgr.check_lockout("user@example.com", "1.2.3.4")

        assert result == ("unset", "unset")

    def test_does_not_leak_the_redis_error_to_the_caller(self):
        mgr = _manager_with_broken_redis(
            redis.exceptions.ConnectionError("redis://user:pw@10.0.0.5:6379 refused")
        )

        with pytest.raises(LoginLockoutUnavailableError) as excinfo:
            mgr.check_lockout("user@example.com", "1.2.3.4")

        assert "10.0.0.5" not in str(excinfo.value)
        assert "pw" not in str(excinfo.value)

    def test_is_allowed_does_not_grant_access_on_outage(self):
        """`is_allowed` inverts check_lockout, so it inherited the bypass."""
        mgr = _manager_with_broken_redis(redis.exceptions.ConnectionError())

        with pytest.raises(LoginLockoutUnavailableError):
            mgr.is_allowed("user@example.com", "1.2.3.4")


@pytest.mark.security
class TestRecordFailureDoesNotLoseTheCount:
    def test_raises_instead_of_returning_zero(self):
        mgr = _manager_with_broken_redis(redis.exceptions.ConnectionError("refused"))

        with pytest.raises(LoginLockoutUnavailableError):
            mgr.record_failure("user@example.com", "1.2.3.4")

    def test_a_silently_frozen_counter_would_never_lock_anyone_out(self):
        """Documents the arithmetic the old `return 0` broke."""
        counter = 0
        threshold = 5

        # What the old code did on every unreachable-Redis failure:
        for _ in range(50):
            counter = 0

        assert counter < threshold, "counter never advances -> lockout unreachable"


@pytest.mark.unit
class TestClearAttemptsStaysBestEffort:
    """The one method that must NOT raise. See the module docstring."""

    def test_does_not_raise_when_redis_is_down(self):
        mgr = _manager_with_broken_redis(redis.exceptions.ConnectionError("refused"))

        mgr.clear_attempts("user@example.com", "1.2.3.4")


@pytest.mark.unit
class TestLockoutStillWorksWhenRedisIsHealthy:
    """Guards against 'fixing' this by breaking the happy path."""

    def test_reports_locked_when_ttl_is_positive(self):
        mgr = LoginLockoutManager(redis_url="redis://localhost:6379/15")
        client = MagicMock()
        client.ttl.return_value = 300
        mgr.client = client

        assert mgr.check_lockout("user@example.com", "1.2.3.4") == (True, 300)

    def test_reports_unlocked_when_ttl_is_expired(self):
        mgr = LoginLockoutManager(redis_url="redis://localhost:6379/15")
        client = MagicMock()
        client.ttl.return_value = -1
        mgr.client = client

        assert mgr.check_lockout("user@example.com", "1.2.3.4") == (False, 0)

    def test_counts_failures_toward_the_threshold(self):
        mgr = LoginLockoutManager(redis_url="redis://localhost:6379/15")
        pipe = MagicMock()
        pipe.execute.side_effect = [[1], [1]]
        client = MagicMock()
        client.pipeline.return_value = pipe
        mgr.client = client

        assert mgr.record_failure("user@example.com", "1.2.3.4") == 1


@pytest.mark.auth
@pytest.mark.security
class TestSignInEndpointsFailClosedOnLockoutOutage:
    def setup_method(self):
        reset_lockout_manager()

    def _outage_manager(self):
        mgr = MagicMock()
        mgr.check_lockout.side_effect = LoginLockoutUnavailableError("down")
        return mgr

    def _post(self, path, payload):
        with patch(
            "authentication.views.get_lockout_manager",
            return_value=self._outage_manager(),
        ):
            return APIClient().post(path, payload, format="json")

    @pytest.mark.parametrize(
        "path,payload",
        [
            ("/api/auth/signin/identify/", {"email": "user@example.com"}),
            ("/api/auth/signin/password/", {"email": "user@example.com", "password": "x"}),
            ("/api/auth/signin/otp/send/", {"email": "user@example.com"}),
            ("/api/auth/signin/otp/verify/", {"email": "user@example.com", "otp_code": "000000"}),
        ],
    )
    def test_every_signin_endpoint_returns_503(self, db, path, payload):
        assert self._post(path, payload).status_code == 503

    @pytest.mark.parametrize(
        "path,payload",
        [
            ("/api/auth/signin/identify/", {"email": "user@example.com"}),
            ("/api/auth/signin/password/", {"email": "user@example.com", "password": "x"}),
            ("/api/auth/signin/otp/send/", {"email": "user@example.com"}),
            ("/api/auth/signin/otp/verify/", {"email": "user@example.com", "otp_code": "000000"}),
        ],
    )
    def test_no_endpoint_leaks_a_token(self, db, path, payload):
        body = self._post(path, payload).json()

        assert "access_token" not in body
        assert "refresh_token" not in body

    def test_identify_does_not_confirm_an_account_exists(self, db):
        """A 503 must not become an enumeration oracle."""
        UserFactory.verified()

        body = self._post(
            "/api/auth/signin/identify/", {"email": "user@example.com"}
        ).json()

        assert "next_step" not in body
        assert "user_exists" not in body

    def test_outage_is_distinct_from_account_locked(self, db):
        """429 means 'you are locked out'; 503 means 'we cannot tell'."""
        body = self._post(
            "/api/auth/signin/identify/", {"email": "user@example.com"}
        ).json()

        assert body["error_code"] != "account_locked"
        assert body["error_code"] == "auth_service_unavailable"

    def test_wrong_password_does_not_report_credentials_when_unmetered(self, db):
        """record_failure failing means the guess went uncounted."""
        user = UserFactory.verified()

        mgr = MagicMock()
        mgr.check_lockout.return_value = (False, 0)
        mgr.record_failure.side_effect = LoginLockoutUnavailableError("down")

        with patch("authentication.views.get_lockout_manager", return_value=mgr):
            response = APIClient().post(
                "/api/auth/signin/password/",
                {"email": user.email, "password": "wrongpass"},
                format="json",
            )

        assert response.status_code == 503
        assert response.json()["error_code"] != "invalid_credentials"

    def test_real_lockout_still_returns_429(self, db):
        """The outage path must not swallow a genuine lockout."""
        mgr = MagicMock()
        mgr.check_lockout.return_value = (True, 300)

        with patch("authentication.views.get_lockout_manager", return_value=mgr):
            response = APIClient().post(
                "/api/auth/signin/identify/", {"email": "user@example.com"}, format="json"
            )

        assert response.status_code == 429
        assert response.json()["error_code"] == "account_locked"
        assert response.json()["retry_after"] == 300