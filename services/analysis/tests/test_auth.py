"""
Tests for KRV-012 — Analysis Service JWT Dependency
"""

import time
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException


def generate_test_jwt(
    private_key_pem: bytes, payload: dict[str, object], algorithm: str = "RS256"
) -> str:
    return jwt.encode(payload, private_key_pem, algorithm=algorithm)


@pytest.fixture
def mock_settings() -> Generator[MagicMock, None, None]:
    with patch("app.dependencies.auth.settings") as mock:
        mock.jwt.jwks_url = "http://localhost/.well-known/jwks.json"
        mock.jwt.algorithm = "RS256"
        mock.jwt.audience = "kraivor"
        mock.jwt.issuer = "kraivor-identity"
        mock.jwt.verify_expiration = True
        mock.jwt.jwks_cache_ttl = 3600
        mock.jwt.internal_request_header = "X-Internal-Request"
        mock.jwt.internal_request_secret = "test-secret"
        yield mock


class TestGetCurrentUser:
    def test_valid_token_returns_payload(self, mock_settings: None) -> None:
        from app.dependencies.auth import get_current_user

        payload = {
            "sub": "user-123",
            "email": "test@example.com",
            "workspace_ids": ["ws-1", "ws-2"],
            "roles": {"ws-1": "owner"},
            "token_type": "access",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(hours=1),
            "aud": "kraivor",
            "iss": "kraivor-identity",
        }

        mock_request = MagicMock(spec=object)
        mock_request.headers = {"Authorization": "Bearer some.valid.token"}

        with patch("app.dependencies.auth._verify_token", return_value=payload):
            user = get_current_user(mock_request)

        assert user.sub == "user-123"
        assert user.email == "test@example.com"
        assert user.workspace_ids == ["ws-1", "ws-2"]

    def test_missing_token_raises_401(self, mock_settings: None) -> None:
        from app.dependencies.auth import get_current_user

        mock_request = MagicMock()
        mock_request.headers = {}

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(mock_request)

        assert exc_info.value.status_code == 401

    def test_invalid_token_raises_401(self, mock_settings: None) -> None:
        from app.dependencies.auth import get_current_user

        mock_request = MagicMock()
        mock_request.headers = {"Authorization": "Bearer invalid.token.here"}

        with (
            patch(
                "app.dependencies.auth._verify_token",
                side_effect=jwt.InvalidTokenError("bad token"),
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            get_current_user(mock_request)

        assert exc_info.value.status_code == 401

    def test_expired_token_raises_401(self, mock_settings: None) -> None:
        from app.dependencies.auth import get_current_user

        mock_request = MagicMock()
        mock_request.headers = {"Authorization": "Bearer expired.token.here"}

        with (
            patch(
                "app.dependencies.auth._verify_token",
                side_effect=jwt.ExpiredSignatureError("expired"),
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            get_current_user(mock_request)

        assert exc_info.value.status_code == 401

    def test_internal_request_bypasses_verification(self, mock_settings: None) -> None:
        from app.dependencies.auth import get_current_user

        mock_request = MagicMock()
        mock_request.headers = {
            "X-Internal-Request": "test-secret",
            "X-User-ID": "user-456",
            "X-Email": "internal@example.com",
        }

        user = get_current_user(mock_request)

        assert user.sub == "user-456"
        assert user.email == "internal@example.com"


class TestVerifyToken:
    """Integration-style tests that exercise _verify_token with real keys."""

    def test_verify_valid_token(self, mock_settings: None) -> None:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        import app.dependencies.auth as auth_module

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = private_key.public_key()
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        payload = {
            "sub": "user-123",
            "email": "test@example.com",
            "token_type": "access",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(hours=1),
            "aud": "kraivor",
            "iss": "kraivor-identity",
        }

        token = generate_test_jwt(private_pem, payload)

        with patch.object(auth_module, "_get_jwks_client") as mock_get_client:
            mock_client = MagicMock()
            mock_signing_key = MagicMock()
            mock_signing_key.key = public_pem.decode("utf-8")
            mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
            mock_get_client.return_value = mock_client

            result = auth_module._verify_token(token)

        assert result["sub"] == "user-123"
        assert result["email"] == "test@example.com"

    def test_expired_token_raises(self, mock_settings: None) -> None:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        import app.dependencies.auth as auth_module

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = private_key.public_key()
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        payload = {
            "sub": "user-123",
            "email": "test@example.com",
            "token_type": "access",
            "iat": datetime.now(UTC) - timedelta(hours=2),
            "exp": datetime.now(UTC) - timedelta(hours=1),
            "aud": "kraivor",
            "iss": "kraivor-identity",
        }

        token = generate_test_jwt(private_pem, payload)

        mock_client = MagicMock()
        mock_signing_key = MagicMock()
        mock_signing_key.key = public_pem.decode("utf-8")
        mock_client.get_signing_key_from_jwt.return_value = mock_signing_key

        with (
            patch.object(auth_module, "_get_jwks_client", return_value=mock_client),
            pytest.raises(jwt.ExpiredSignatureError),
        ):
            auth_module._verify_token(token)

    def test_invalid_token_raises(self, mock_settings: None) -> None:
        import app.dependencies.auth as auth_module

        mock_client = MagicMock()
        mock_client.get_signing_key_from_jwt.side_effect = jwt.InvalidTokenError(
            "bad kid"
        )

        with (
            patch.object(auth_module, "_get_jwks_client", return_value=mock_client),
            pytest.raises(jwt.InvalidTokenError),
        ):
            auth_module._verify_token("bad.token.here")


class TestGetJwksClient:
    def test_client_created_and_cached(self, mock_settings: None) -> None:
        import app.dependencies.auth as auth_module

        auth_module._jwks_client = None
        auth_module._jwks_client_ttl = 0

        with patch("app.dependencies.auth.PyJWKClient") as mock_pyjwk:
            mock_instance = MagicMock()
            mock_pyjwk.return_value = mock_instance

            client1 = auth_module._get_jwks_client()
            client2 = auth_module._get_jwks_client()

            assert client1 is client2
            mock_pyjwk.assert_called_once()
            mock_instance.fetch_data.assert_called_once()

    def test_invalidate_cache(self, mock_settings: None) -> None:
        import app.dependencies.auth as auth_module

        auth_module._jwks_client = MagicMock()
        auth_module._jwks_client_ttl = time.time()

        auth_module.invalidate_jwks_cache()

        assert auth_module._jwks_client is None
        assert auth_module._jwks_client_ttl == 0
