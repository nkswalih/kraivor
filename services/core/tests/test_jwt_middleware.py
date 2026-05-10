"""
Tests for KRV-012 — Core Service JWT Middleware

Covers:
  - Valid JWT tokens are accepted and payload added to request
  - Missing/Invalid/Expired tokens return 401
  - Internal requests bypass JWT verification
"""

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import jwt
import pytest
from django.test import RequestFactory, override_settings


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
    from cryptography.hazmat.primitives.asymmetric import rsa

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
def middleware(mock_jwks):
    from core.middleware.jwt_auth import JWTAuthenticationMiddleware

    def get_response(request):
        return MagicMock()

    with patch.object(JWTAuthenticationMiddleware, '_get_jwks', return_value=mock_jwks):
        mw = JWTAuthenticationMiddleware(get_response)
        mw._jwks_cache = mock_jwks
        mw._jwks_cache_time = time.time()
        return mw


class TestJWTAuthenticationMiddleware:
    def test_valid_token_is_accepted(self, middleware, private_key):
        from django.test import RequestFactory
        factory = RequestFactory()

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
        request = factory.get('/api/test/', HTTP_AUTHORIZATION=f'Bearer {token}')

        response = middleware(request)

        assert request.user_id == "user-123"
        assert request.email == "test@example.com"
        assert request.workspace_ids == ["ws-1", "ws-2"]

    def test_missing_token_returns_401(self, middleware):
        from django.test import RequestFactory
        factory = RequestFactory()

        request = factory.get('/api/test/')
        response = middleware(request)

        assert response.status_code == 401
        assert b"missing_authorization" in response.content

    def test_invalid_token_returns_401(self, middleware):
        from django.test import RequestFactory
        factory = RequestFactory()

        request = factory.get('/api/test/', HTTP_AUTHORIZATION='Bearer invalid.token.here')
        response = middleware(request)

        assert response.status_code == 401
        assert b"invalid_token" in response.content

    def test_expired_token_returns_401(self, middleware, private_key):
        from django.test import RequestFactory
        factory = RequestFactory()

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
        request = factory.get('/api/test/', HTTP_AUTHORIZATION=f'Bearer {token}')
        response = middleware(request)

        assert response.status_code == 401
        assert b"token_expired" in response.content

    def test_internal_request_bypasses_verification(self, middleware):
        from django.test import RequestFactory
        factory = RequestFactory()

        request = factory.get('/api/test/', HTTP_X_INTERNAL_REQUEST='true')
        response = middleware(request)

        assert response is not None

    def test_admin_path_bypasses_verification(self, middleware):
        from django.test import RequestFactory
        factory = RequestFactory()

        request = factory.get('/admin/')
        response = middleware(request)

        assert response is not None


class TestJWTCacheInvalidation:
    def test_cache_can_be_invalidated(self):
        from core.middleware.jwt_auth import JWTAuthenticationMiddleware

        JWTAuthenticationMiddleware._jwks_cache = {"test": "data"}
        JWTAuthenticationMiddleware._jwks_cache_time = time.time()

        JWTAuthenticationMiddleware.invalidate_cache()

        assert JWTAuthenticationMiddleware._jwks_cache is None