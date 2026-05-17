"""
Pytest configuration and fixtures for Identity Service.

Modern production-grade testing architecture with reusable fixtures.
"""
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import django
import pytest
from authentication.security import reset_lockout_manager
from django.conf import settings
from rest_framework.test import APIClient
from users.models import User

BASE_DIR = Path(__file__).resolve().parent
APPS_DIR = BASE_DIR / "apps"
PROJECT_ROOT = BASE_DIR.parent

for p in [str(PROJECT_ROOT), str(BASE_DIR), str(APPS_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "auth.settings.test")
os.environ.setdefault("DATABASE_URL", "sqlite://:memory:")

django.setup()

@pytest.fixture(autouse=True)
def clean_lockout_manager():
    """Reset lockout manager before each test for isolation."""
    reset_lockout_manager()
    yield
    reset_lockout_manager()


@pytest.fixture
def api_client():
    """Return a fresh DRF APIClient."""
    return APIClient()


@pytest.fixture
def unverified_user(db):
    """Create an unverified user for testing."""
    user = User.objects.create_user(
        email="unverified@test.com",
        password="testpass123",
        name="Unverified Test",
        email_verified=False,
    )
    return user


@pytest.fixture
def verified_user(db):
    """Create a verified user for testing."""
    user = User.objects.create_user(
        email="verified@test.com",
        password="testpass123",
        name="Verified Test",
        email_verified=True,
    )
    return user


@pytest.fixture
def locked_user(db):
    """Create a user that has been locked out."""
    user = User.objects.create_user(
        email="locked@test.com",
        password="testpass123",
        name="Locked Test",
        email_verified=True,
    )
    return user


@pytest.fixture
def user_factory(db):
    """
    Factory fixture for creating users with various configurations.

    Usage:
        user = user_factory(email="custom@test.com", email_verified=True)
        admin = user_factory(is_staff=True, is_superuser=True)
    """
    def _create_user(
        email="test@example.com",
        password="testpass123",
        name="Test User",
        email_verified=False,
        is_active=True,
        is_staff=False,
        is_superuser=False,
        **kwargs
    ):
        user = User.objects.create_user(
            email=email,
            password=password,
            name=name,
            email_verified=email_verified,
            is_active=is_active,
            is_staff=is_staff,
            is_superuser=is_superuser,
            **kwargs
        )
        return user
    return _create_user


@pytest.fixture
def token_service():
    """Get the token service for generating test tokens."""
    from authentication.tokens import get_token_service
    return get_token_service()


@pytest.fixture
def user_tokens(user_factory, token_service):
    """
    Create a user with valid access and refresh tokens.

    Returns dict with user, access_token, refresh_token.
    """
    user = user_factory(email_verified=True)
    tokens = token_service.generate_tokens(
        user=user,
        device_id="test-device",
        ip_address="127.0.0.1",
        user_agent="pytest-agent",
    )
    return {
        "user": user,
        "access_token": tokens.access_token,
        "refresh_token": tokens.refresh_token,
        "tokens": tokens,
    }


@pytest.fixture
def authenticated_client(user_tokens):
    """Return APIClient with authentication headers set."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_tokens['access_token']}")
    client.user = user_tokens["user"]
    return client


@pytest.fixture
def refresh_token_client(user_tokens, api_client):
    """Return APIClient with refresh token cookie set."""
    api_client.cookies["refresh_token"] = user_tokens["refresh_token"]
    return api_client


@pytest.fixture
def mock_redis():
    """Mock Redis client for rate limiting tests."""
    mock = MagicMock()
    mock_pipe = MagicMock()
    mock.pipeline.return_value = mock_pipe
    mock_pipe.execute.return_value = [1, True, 3600]
    return mock


@pytest.fixture
def mock_email_service():
    """Mock email service for testing email flows."""
    with patch("users.views.email_service") as mock:
        mock.send_verification_email.return_value = None
        yield mock


@pytest.fixture
def mock_rate_limiter():
    """Mock rate limiter for testing rate limit logic."""
    with patch("users.views.rate_limiter") as mock:
        mock.is_allowed.return_value = True
        yield mock


@pytest.fixture
def jwt_payload_builder():
    """
    Builder for constructing JWT payloads for testing.

    Usage:
        payload = jwt_payload_builder(sub="123", email="test@test.com")
    """
    def _build_payload(
        sub="test-user-id",
        email="test@example.com",
        token_type="access",
        minutes_until_expiry=15,
        **extra_claims
    ):
        now = datetime.now(UTC)
        payload = {
            "sub": sub,
            "email": email,
            "token_type": token_type,
            "iat": now,
            "exp": now + timedelta(minutes=minutes_until_expiry),
            **extra_claims
        }
        return payload
    return _build_payload


@pytest.fixture
def verification_token(verified_user):
    """Generate a valid email verification token."""
    from users.verification import generate_verification_token
    return generate_verification_token(verified_user)


@pytest.fixture
def expired_verification_token(verified_user):
    """Generate an expired email verification token."""
    import jwt
    from users.verification import _ALGORITHM, _TOKEN_TYPE

    now = datetime.now(UTC)
    payload = {
        "sub": str(verified_user.id),
        "email": verified_user.email,
        "token_type": _TOKEN_TYPE,
        "iat": now - timedelta(hours=25),
        "exp": now - timedelta(hours=1),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=_ALGORITHM)


@pytest.fixture
def mock_lockout_manager():
    """Mock lockout manager for testing locked account flows."""
    mock = MagicMock()
    mock.check_lockout.return_value = (False, 0)
    return mock


@pytest.fixture
def locked_account_manager():
    """Mock that simulates a locked account."""
    mock = MagicMock()
    mock.check_lockout.return_value = (True, 300)
    return mock


@pytest.fixture
def otp_mock_service():
    """Mock OTP service for testing OTP flows."""
    import authentication.otp as otp_module

    mock = MagicMock()
    mock.verify_otp.return_value = True
    otp_module._otp_service = mock
    yield mock
    otp_module._otp_service = None


@pytest.fixture
def test_rsa_keys():
    """Generate test RSA keypair for JWKS tests."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    return {
        "private_pem": private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ),
        "public_pem": public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ),
    }


@pytest.fixture
def temp_jwks_keys(test_rsa_keys, tmp_path):
    """Create temporary JWKS keys for testing."""
    keys_dir = tmp_path / ".keys"
    keys_dir.mkdir(exist_ok=True)

    public_path = keys_dir / "jwt-public.pem"
    private_path = keys_dir / "jwt-private.pem"

    public_path.write_bytes(test_rsa_keys["public_pem"])
    private_path.write_bytes(test_rsa_keys["private_pem"])

    return {
        "public_path": public_path,
        "private_path": private_path,
        "dir": keys_dir,
    }


@pytest.fixture(scope="session")
def django_db_setup(django_db_blocker):
    """Create database tables before running tests."""
    from django.core.management import call_command
    with django_db_blocker.unblock():
        call_command("migrate", "--run-syncdb", verbosity=0)


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated)")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "security: Security tests")
    config.addinivalue_line("markers", "auth: Authentication flow tests")
    config.addinivalue_line("markers", "token: Token lifecycle tests")


def pytest_collection_modifyitems(config, items):
    """Auto-mark tests based on their location and naming."""
    security_nodes = (
        "test_refresh_token.py",
        "test_jwks.py",
        "test_identify_locked_account",
        "test_locked_account",
        "test_wrong_password",
        "rate_limit",
    )

    for item in items:
        if "test_signup" in item.nodeid or "test_signin" in item.nodeid:
            item.add_marker(pytest.mark.auth)
        elif "test_refresh" in item.nodeid:
            item.add_marker(pytest.mark.token)
        elif "test_email_verification" in item.nodeid:
            item.add_marker(pytest.mark.auth)
        elif "test_jwks" in item.nodeid:
            item.add_marker(pytest.mark.integration)

        if any(node in item.nodeid for node in security_nodes):
            item.add_marker(pytest.mark.security)
