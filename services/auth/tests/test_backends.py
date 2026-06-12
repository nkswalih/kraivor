"""Tests for custom authentication backends and cookie utils."""

from django.test import override_settings


class TestJWKSTokenBackend:
    """JWKSTokenBackend.encode tested with HS256 (no RSA key needed)."""

    def backend(self, algorithm="HS256", signing_key="test-secret-key-32-bytes-long-!!"):
        from authentication.backends import JWKSTokenBackend

        return JWKSTokenBackend(algorithm=algorithm, signing_key=signing_key)

    def test_encode_with_kid(self):
        backend = self.backend()
        with override_settings(JWT_KEY_ID="test-kid-001"):
            token = backend.encode({"sub": "123"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_encode_without_kid_logs_warning(self):
        backend = self.backend()
        with override_settings(JWT_KEY_ID=None):
            token = backend.encode({"sub": "123"})
        assert isinstance(token, str)

    def test_encode_returns_string(self):
        backend = self.backend()
        token = backend.encode({"sub": "123"})
        assert isinstance(token, str)

    def test_encode_with_bytes_from_jwt(self):
        from unittest.mock import patch
        backend = self.backend()
        with patch("authentication.backends.jwt.encode", return_value=b"bytes-token"):
            token = backend.encode({"sub": "123"})
        assert isinstance(token, str)
        assert token == "bytes-token"


class TestCookieUtils:
    def test_create_refresh_cookie_defaults(self):
        from authentication.cookie_utils import create_refresh_cookie

        result = create_refresh_cookie("test-token")
        assert result["value"] == "test-token"
        assert result["httponly"] is True

    def test_create_refresh_cookie_custom_max_age(self):
        from authentication.cookie_utils import create_refresh_cookie

        result = create_refresh_cookie("test", max_age_days=7)
        assert result["max_age"] == 7 * 24 * 60 * 60

    @override_settings(COOKIE_SECURE=True, COOKIE_SAMESITE="Lax", COOKIE_PATH="/auth")
    def test_create_refresh_cookie_respects_settings(self):
        from authentication.cookie_utils import create_refresh_cookie

        result = create_refresh_cookie("test")
        assert result["secure"] is True
        assert result["samesite"] == "Lax"
        assert result["path"] == "/auth"

    def test_clear_refresh_cookie(self):
        from authentication.cookie_utils import clear_refresh_cookie

        result = clear_refresh_cookie()
        assert result["value"] == ""
        assert result["max_age"] == 0

    @override_settings(COOKIE_DOMAIN="example.com")
    def test_clear_refresh_cookie_with_domain(self):
        from authentication.cookie_utils import clear_refresh_cookie

        result = clear_refresh_cookie()
        assert result["domain"] == "example.com"
