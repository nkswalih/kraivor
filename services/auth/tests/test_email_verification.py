"""
Tests for KRV-010 — Email Verification

Covers:
  - JWT token generation / validation
  - POST /api/auth/verify-email/
  - POST /api/auth/resend-verification/
  - Redis rate limiting (mocked)
  - Integration: signup → token → verify
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import uuid

import jwt
from django.conf import settings
from django.test import TestCase
from rest_framework.test import APIClient
from users.models import User
from users.rate_limiter import RateLimitExceeded, RedisRateLimiter
from users.verification import (
    _ALGORITHM,
    _TOKEN_TYPE,
    decode_verification_token,
    generate_verification_token,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_user(email=None, verified=False, **kwargs) -> User:
    user = User(
        email=email or f"{uuid.uuid4()}@example.com",
        name="Test User",
        email_verified=verified,
        **kwargs,
    )
    user.set_password("testpass123")
    user.save()
    return user


def _expired_token(user: User) -> str:
    """Build a token that has already expired."""
    now = datetime.now(UTC)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "token_type": _TOKEN_TYPE,
        "iat": now - timedelta(hours=25),
        "exp": now - timedelta(hours=1),  # expired 1 hour ago
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=_ALGORITHM)


def _wrong_type_token(user: User) -> str:
    """Build a token with the wrong token_type (e.g. access token reuse)."""
    now = datetime.now(UTC)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "token_type": "access",  # wrong
        "iat": now,
        "exp": now + timedelta(hours=24),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=_ALGORITHM)


# ---------------------------------------------------------------------------
# Unit tests: JWT token utilities
# ---------------------------------------------------------------------------


class TestGenerateVerificationToken(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_generates_valid_jwt_string(self):
        token = generate_verification_token(self.user)
        self.assertIsInstance(token, str)
        # JWT has 3 dot-separated parts
        self.assertEqual(len(token.split(".")), 3)

    def test_token_contains_correct_claims(self):
        token = generate_verification_token(self.user)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[_ALGORITHM])
        self.assertEqual(payload["sub"], str(self.user.id))
        self.assertEqual(payload["email"], self.user.email)
        self.assertEqual(payload["token_type"], "email_verification")

    def test_token_expires_in_24_hours(self):
        before = datetime.now(UTC)
        token = generate_verification_token(self.user)
        after = datetime.now(UTC)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[_ALGORITHM])
        exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
        # exp must be roughly now + 24h (within 5 s of test execution)
        self.assertAlmostEqual((exp - before).total_seconds(), 24 * 3600, delta=5)
        _ = after  # suppress lint

    def test_different_users_get_different_tokens(self):
        user2 = make_user(email="other@example.com")
        t1 = generate_verification_token(self.user)
        t2 = generate_verification_token(user2)
        self.assertNotEqual(t1, t2)


class TestDecodeVerificationToken(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_valid_token_returns_payload(self):
        token = generate_verification_token(self.user)
        payload, err = decode_verification_token(token)
        self.assertIsNone(err)
        self.assertEqual(payload["sub"], str(self.user.id))
        self.assertEqual(payload["email"], self.user.email)

    def test_expired_token_returns_error_code(self):
        token = _expired_token(self.user)
        payload, err = decode_verification_token(token)
        self.assertEqual(err, "token_expired")
        self.assertEqual(payload, {})

    def test_invalid_signature_returns_error_code(self):
        token = generate_verification_token(self.user)
        tampered = token[:-5] + "XXXXX"
        payload, err = decode_verification_token(tampered)
        self.assertEqual(err, "invalid_token")

    def test_wrong_token_type_returns_error_code(self):
        token = _wrong_type_token(self.user)
        _, err = decode_verification_token(token)
        self.assertEqual(err, "invalid_token")

    def test_garbage_string_returns_error_code(self):
        _, err = decode_verification_token("not.a.jwt")
        self.assertEqual(err, "invalid_token")

    def test_empty_string_returns_error_code(self):
        _, err = decode_verification_token("")
        self.assertEqual(err, "invalid_token")


# ---------------------------------------------------------------------------
# Unit tests: Rate limiter
# ---------------------------------------------------------------------------


class TestRedisRateLimiter(TestCase):
    """Tests the rate limiter against a mock Redis client."""

    def _make_limiter(self, counts):
        """
        Build a RedisRateLimiter whose pipeline().execute() returns
        successive (count, True, ttl) triples from *counts*.
        counts: list of (incr_result, ttl_result)
        """
        mock_redis = MagicMock()
        mock_pipe = MagicMock()
        mock_redis.pipeline.return_value.__enter__ = MagicMock(return_value=mock_pipe)
        mock_redis.pipeline.return_value.__exit__ = MagicMock(return_value=False)
        # pipeline() used without context manager in implementation
        mock_redis.pipeline.return_value = mock_pipe

        results_iter = iter(counts)

        def execute():
            count, ttl = next(results_iter)
            return [count, True, ttl]

        mock_pipe.execute.side_effect = execute
        limiter = RedisRateLimiter.__new__(RedisRateLimiter)
        limiter.client = mock_redis
        return limiter

    def test_first_request_is_allowed(self):
        limiter = self._make_limiter([(1, 3600)])
        allowed, remaining, retry_after = limiter.check("key", limit=3, window_seconds=3600)
        self.assertTrue(allowed)
        self.assertEqual(remaining, 2)
        self.assertEqual(retry_after, 0)

    def test_third_request_is_allowed(self):
        limiter = self._make_limiter([(3, 3600)])
        allowed, remaining, _ = limiter.check("key", limit=3, window_seconds=3600)
        self.assertTrue(allowed)
        self.assertEqual(remaining, 0)

    def test_fourth_request_is_blocked(self):
        limiter = self._make_limiter([(4, 2700)])
        allowed, remaining, retry_after = limiter.check("key", limit=3, window_seconds=3600)
        self.assertFalse(allowed)
        self.assertEqual(remaining, 0)
        self.assertEqual(retry_after, 2700)

    def test_is_allowed_raises_on_exceeded(self):
        limiter = self._make_limiter([(4, 2700)])
        with self.assertRaises(RateLimitExceeded) as ctx:
            limiter.is_allowed("key", limit=3, window_seconds=3600)
        self.assertEqual(ctx.exception.retry_after, 2700)


# ---------------------------------------------------------------------------
# API tests: POST /api/auth/verify-email/
# ---------------------------------------------------------------------------


class TestVerifyEmailView(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/auth/verify-email/"

    def test_valid_token_verifies_email(self):
        user = make_user(verified=False)
        token = generate_verification_token(user)
        response = self.client.post(self.url, {"token": token}, format="json")
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.email_verified)
        self.assertEqual(response.data["email_verified"], True)

    def test_already_verified_is_idempotent(self):
        user = make_user(verified=True)
        token = generate_verification_token(user)
        response = self.client.post(self.url, {"token": token}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email_verified"], True)

    def test_expired_token_returns_400_with_error_code(self):
        user = make_user()
        token = _expired_token(user)
        response = self.client.post(self.url, {"token": token}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error_code"], "token_expired")
        # hint for frontend to show resend option
        self.assertIn("hint", response.data)

    def test_invalid_token_returns_400(self):
        response = self.client.post(self.url, {"token": "bad.token.here"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error_code"], "invalid_token")

    def test_missing_token_returns_400(self):
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error_code"], "missing_token")

    def test_wrong_token_type_returns_400(self):
        user = make_user()
        token = _wrong_type_token(user)
        response = self.client.post(self.url, {"token": token}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error_code"], "invalid_token")

    def test_email_mismatch_in_token_returns_400(self):
        """Token sub points to user A but email claim is user B — should reject."""
        user_a = make_user(email="a@example.com")
        make_user(email="b@example.com")
        now = datetime.now(UTC)
        payload = {
            "sub": str(user_a.id),
            "email": "b@example.com",  # mismatch
            "token_type": _TOKEN_TYPE,
            "iat": now,
            "exp": now + timedelta(hours=24),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=_ALGORITHM)
        response = self.client.post(self.url, {"token": token}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error_code"], "invalid_token")


# ---------------------------------------------------------------------------
# API tests: POST /api/auth/resend-verification/
# ---------------------------------------------------------------------------


class TestResendVerificationView(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/auth/resend-verification/"

    @patch("users.views.email_service")
    @patch("users.views.rate_limiter")
    def test_resend_success(self, mock_limiter, mock_email):
        mock_limiter.is_allowed.return_value = True
        user = make_user(email="unverified@example.com", verified=False)
        response = self.client.post(self.url, {"email": user.email}, format="json")
        self.assertEqual(response.status_code, 200)
        mock_email.send_verification_email.assert_called_once()

    @patch("users.views.rate_limiter")
    def test_already_verified_returns_400(self, mock_limiter):
        mock_limiter.is_allowed.return_value = True
        user = make_user(email="verified@example.com", verified=True)
        response = self.client.post(self.url, {"email": user.email}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error_code"], "already_verified")

    @patch("users.views.rate_limiter")
    def test_rate_limit_exceeded_returns_429(self, mock_limiter):
        mock_limiter.is_allowed.side_effect = RateLimitExceeded(retry_after=2700)
        make_user(email="ratelimited@example.com", verified=False)
        response = self.client.post(self.url, {"email": "ratelimited@example.com"}, format="json")
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.data["error_code"], "rate_limit_exceeded")
        self.assertIn("Retry-After", response)

    @patch("users.views.rate_limiter")
    def test_nonexistent_email_returns_200_anti_enumeration(self, mock_limiter):
        """Should return 200 even for unknown emails (prevents enumeration)."""
        mock_limiter.is_allowed.return_value = True
        response = self.client.post(self.url, {"email": "nobody@example.com"}, format="json")
        self.assertEqual(response.status_code, 200)

    def test_missing_email_returns_400(self):
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error_code"], "missing_email")

    @patch("users.views.email_service")
    @patch("users.views.rate_limiter")
    def test_email_send_failure_returns_503(self, mock_limiter, mock_email):
        mock_limiter.is_allowed.return_value = True
        mock_email.send_verification_email.side_effect = Exception("SMTP down")
        user = make_user(email="fail@example.com", verified=False)
        response = self.client.post(self.url, {"email": user.email}, format="json")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["error_code"], "email_send_failed")


# ---------------------------------------------------------------------------
# API tests: POST /api/auth/signup/ — email sent after registration
# ---------------------------------------------------------------------------


class TestSignUpSendsVerificationEmail(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/auth/signup/"

    @patch("users.views.email_service")
    def test_signup_sends_verification_email(self, mock_email):
        data = {
            "email": "newuser@example.com",
            "password": "SecurePass123!",
            "password_confirm": "SecurePass123!",
            "name": "New User",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, 201)
        mock_email.send_verification_email.assert_called_once()
        # user should NOT be verified immediately
        user = User.objects.get(email="newuser@example.com")
        self.assertFalse(user.email_verified)

    @patch("users.views.email_service")
    def test_signup_succeeds_even_if_email_send_fails(self, mock_email):
        """User is created; email failure is non-fatal."""
        mock_email.send_verification_email.side_effect = Exception("SMTP down")
        data = {
            "email": "emailfail@example.com",
            "password": "SecurePass123!",
            "password_confirm": "SecurePass123!",
            "name": "Email Fail",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.data["email_sent"])
        self.assertTrue(User.objects.filter(email="emailfail@example.com").exists())

    @patch("users.views.email_service")
    def test_signup_response_includes_email_verified_false(self, mock_email):
        data = {
            "email": "pendingverify@example.com",
            "password": "SecurePass123!",
            "password_confirm": "SecurePass123!",
            "name": "Pending Verify",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.data["email_verified"])


# ---------------------------------------------------------------------------
# Integration test: full signup → verify flow
# ---------------------------------------------------------------------------


class TestEmailVerificationIntegration(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("users.views.email_service")
    def test_full_signup_to_verify_flow(self, mock_email):
        """
        End-to-end: signup → capture token from mock → verify → confirmed.
        """
        # 1. Sign up
        signup_data = {
            "email": "integration@kraivor.test",
            "password": "IntegrationPass1!",
            "password_confirm": "IntegrationPass1!",
            "name": "Integration User",
        }
        signup_resp = self.client.post("/api/auth/signup/", signup_data, format="json")
        self.assertEqual(signup_resp.status_code, 201)

        # 2. Capture the token passed to email_service
        call_args = mock_email.send_verification_email.call_args
        user_arg, token_arg = call_args[0]
        self.assertIsNotNone(token_arg)

        # 3. Verify email with captured token
        verify_resp = self.client.post(
            "/api/auth/verify-email/", {"token": token_arg}, format="json"
        )
        self.assertEqual(verify_resp.status_code, 200)
        self.assertTrue(verify_resp.data["email_verified"])

        # 4. Confirm DB state
        user = User.objects.get(email="integration@kraivor.test")
        self.assertTrue(user.email_verified)

    @patch("users.views.email_service")
    def test_expired_token_in_integration_flow(self, mock_email):
        """Expired token should prompt the user to resend."""
        # Create an unverified user directly
        user = make_user(email="expiredflow@kraivor.test", verified=False)

        # Build an expired token
        expired_token = _expired_token(user)

        response = self.client.post(
            "/api/auth/verify-email/", {"token": expired_token}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error_code"], "token_expired")
        # hint must be present for frontend to show "Resend email" CTA
        self.assertIn("hint", response.data)
