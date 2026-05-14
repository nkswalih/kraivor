"""
Tests for KRV-012 — Analysis Service JWT Dependency
"""

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException


def generate_test_jwt(private_key_pem: bytes, payload: dict, algorithm: str = "RS256") -> str:
    return jwt.encode(payload, private_key_pem, algorithm=algorithm)


def generate_test_rsa_keypair():
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return private_pem, public_pem


@pytest.fixture
def keypair():
    return generate_test_rsa_keypair()


@pytest.fixture
def private_key(keypair):
    return keypair[0]


@pytest.fixture
def public_key(keypair):
    return keypair[1]


@pytest.fixture
def mock_jwks(public_key):
    from cryptography.hazmat.primitives import serialization

    public_key_obj = serialization.load_pem_public_key(public_key)
    public_numbers = public_key_obj.public_numbers()
    n_bytes = public_numbers.n.to_bytes(256, "big")
    e_bytes = public_numbers.e.to_bytes(4, "big")

    def b64url_encode(data: bytes) -> str:
        import base64
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    return {
        "keys": [{
            "kty": "RSA",
            "use": "sig",
            "alg": "RS256",
            "kid": "kraivor-key-1",
            "n": b64url_encode(n_bytes),
            "e": b64url_encode(e_bytes),
        }]
    }


@pytest.fixture
def mock_settings():
    with patch("app.dependencies.auth.settings") as mock:
        mock.identity_jwks_url = "http://localhost/.well-known/jwks.json"
        mock.jwt_algorithm = "RS256"
        mock.jwt_audience = "kraivor"
        mock.jwt_issuer = "kraivor-identity"
        mock.jwt_verify_expiration = True
        mock.jwt_jwks_cache_ttl = 3600
        mock.internal_request_header = "X-Internal-Request"
        yield mock


class TestGetCurrentUser:
    def test_valid_token_returns_payload(self, private_key, mock_settings, mock_jwks):
        from app.dependencies.auth import get_current_user

        # Set up cache
        import app.dependencies.auth as auth_module
        auth_module._jwks_cache = mock_jwks
        auth_module._jwks_cache_time = time.time()

        payload = {
            "sub": "user-123",
            "email": "test@example.com",
            "workspace_ids": ["ws-1", "ws-2"],
            "roles": {"ws-1": "owner"},
            "token_type": "access",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "aud": "kraivor",
            "iss": "kraivor-identity",
        }

        token = generate_test_jwt(private_key, payload)

        mock_request = MagicMock()
        mock_request.headers = {"Authorization": f"Bearer {token}"}
        mock_request.headers.get = lambda k, d=None: {"Authorization": f"Bearer {token}"}.get(k, d)
        mock_request.headers.get.side_effect = lambda k, d=None: {"Authorization": f"Bearer {token}"}.get(k, d)

        user = get_current_user(mock_request)

        assert user.sub == "user-123"
        assert user.email == "test@example.com"
        assert user.workspace_ids == ["ws-1", "ws-2"]

    def test_missing_token_raises_401(self, mock_settings):
        from app.dependencies.auth import get_current_user

        mock_request = MagicMock()
        mock_request.headers = {}

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(mock_request)

        assert exc_info.value.status_code == 401

    def test_invalid_token_raises_401(self, mock_settings):
        from app.dependencies.auth import get_current_user

        mock_request = MagicMock()
        mock_request.headers = {"Authorization": "Bearer invalid.token.here"}

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(mock_request)

        assert exc_info.value.status_code == 401

    def test_expired_token_raises_401(self, private_key, mock_settings, mock_jwks):
        from app.dependencies.auth import get_current_user

        import app.dependencies.auth as auth_module
        auth_module._jwks_cache = mock_jwks
        auth_module._jwks_cache_time = time.time()

        payload = {
            "sub": "user-123",
            "email": "test@example.com",
            "token_type": "access",
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "aud": "kraivor",
            "iss": "kraivor-identity",
        }

        token = generate_test_jwt(private_key, payload)

        mock_request = MagicMock()
        mock_request.headers = {"Authorization": f"Bearer {token}"}

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(mock_request)

        assert exc_info.value.status_code == 401
        assert "token_expired" in exc_info.value.detail["error"]

    def test_internal_request_bypasses_verification(self, mock_settings):
        from app.dependencies.auth import get_current_user

        mock_request = MagicMock()
        mock_request.headers = {
            "X-Internal-Request": "true",
            "X-User-ID": "user-456",
            "X-Email": "internal@example.com"
        }

        user = get_current_user(mock_request)

        assert user.sub == "user-456"
        assert user.email == "internal@example.com"


class TestCacheInvalidation:
    def test_cache_can_be_invalidated(self, mock_settings):
        from app.dependencies.auth import invalidate_jwks_cache

        import app.dependencies.auth as auth_module
        auth_module._jwks_cache = {"test": "data"}
        auth_module._jwks_cache_time = time.time()

        invalidate_jwks_cache()

        assert auth_module._jwks_cache is None