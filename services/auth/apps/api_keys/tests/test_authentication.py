"""Unit tests for the DRF APIKeyAuthentication backend."""

from unittest.mock import MagicMock, patch

import pytest
from api_keys.authentication.backend import APIKeyAuthentication
from api_keys.services.key_service import APIKeyExpiredError, APIKeyNotFoundError
from rest_framework.exceptions import AuthenticationFailed


@pytest.fixture
def backend():
    return APIKeyAuthentication()


def make_request(auth_header: str = ""):
    request = MagicMock()
    request.META = {"HTTP_AUTHORIZATION": auth_header}
    return request


class TestAPIKeyAuthentication:
    def test_no_header_returns_none(self, backend):
        assert backend.authenticate(make_request("")) is None

    def test_jwt_token_returns_none(self, backend):
        jwt = "Bearer eyJhbGciOiJSUzI1NiJ9.payload.sig"
        assert backend.authenticate(make_request(jwt)) is None

    def test_malformed_header_returns_none(self, backend):
        assert backend.authenticate(make_request("Basic dXNlcjpwYXNz")) is None

    @patch("api_keys.authentication.backend.authenticate_api_key")
    @patch("api_keys.authentication.backend.is_api_key_format", return_value=True)
    def test_valid_key_returns_user_and_key(self, mock_fmt, mock_auth, backend):
        mock_key = MagicMock()
        mock_key.user = MagicMock()
        mock_auth.return_value = mock_key
        result = backend.authenticate(make_request("Bearer krv_live_" + "a" * 64))
        assert result == (mock_key.user, mock_key)

    @patch("api_keys.authentication.backend.authenticate_api_key")
    @patch("api_keys.authentication.backend.is_api_key_format", return_value=True)
    def test_not_found_raises_auth_failed(self, mock_fmt, mock_auth, backend):
        mock_auth.side_effect = APIKeyNotFoundError("not found")
        with pytest.raises(AuthenticationFailed, match="Invalid API key"):
            backend.authenticate(make_request("Bearer krv_live_" + "a" * 64))

    @patch("api_keys.authentication.backend.authenticate_api_key")
    @patch("api_keys.authentication.backend.is_api_key_format", return_value=True)
    def test_expired_raises_auth_failed(self, mock_fmt, mock_auth, backend):
        mock_auth.side_effect = APIKeyExpiredError("expired")
        with pytest.raises(AuthenticationFailed, match="expired"):
            backend.authenticate(make_request("Bearer krv_live_" + "a" * 64))

    @patch("api_keys.authentication.backend.is_api_key_format", return_value=True)
    def test_unexpected_error_raises_auth_failed(self, mock_fmt, backend):
        with patch(
            "api_keys.authentication.backend.authenticate_api_key",
            side_effect=ValueError("surprise"),
        ), pytest.raises(AuthenticationFailed, match="Authentication error"):
            backend.authenticate(make_request("Bearer krv_live_" + "a" * 64))

    def test_authenticate_header_returns_bearer_realm(self, backend):
        header = backend.authenticate_header(MagicMock())
        assert "Bearer" in header
        assert "realm" in header