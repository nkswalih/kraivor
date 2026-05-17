"""
Test factories for creating objects with consistent, realistic data.

Usage:
    from tests.factories import UserFactory, TokenFactory

    user = UserFactory.create()
    tokens = TokenFactory.create_for_user(user)
"""

from dataclasses import dataclass


@dataclass
class TokenData:
    """Container for token data."""

    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user_id: int
    email: str


class UserFactory:
    """Factory for creating User instances with sensible defaults."""

    _counter = 0

    @classmethod
    def _next_email(cls):
        cls._counter += 1
        return f"test{cls._counter}@example.com"

    @classmethod
    def create(
        cls,
        email: str | None = None,
        name: str = "Test User",
        password: str = "testpass123",
        email_verified: bool = False,
        is_active: bool = True,
        is_staff: bool = False,
        is_superuser: bool = False,
        **kwargs,
    ):
        """Create a new user with the given attributes."""
        from users.models import User

        if email is None:
            email = cls._next_email()

        user = User.objects.create_user(
            email=email,
            password=password,
            name=name,
            email_verified=email_verified,
            is_active=is_active,
            is_staff=is_staff,
            is_superuser=is_superuser,
            **kwargs,
        )
        return user

    @classmethod
    def verified(cls, **kwargs):
        """Create a verified user."""
        return cls.create(email_verified=True, **kwargs)

    @classmethod
    def staff(cls, **kwargs):
        """Create a staff user."""
        return cls.create(is_staff=True, email_verified=True, **kwargs)

    @classmethod
    def admin(cls, **kwargs):
        """Create an admin user."""
        return cls.create(is_staff=True, is_superuser=True, email_verified=True, **kwargs)

    @classmethod
    def unverified(cls, **kwargs):
        """Create an unverified user."""
        return cls.create(email_verified=False, **kwargs)


class TokenFactory:
    """Factory for creating JWT tokens."""

    @classmethod
    def create_for_user(cls, user, **overrides):
        """Create tokens for an existing user."""
        from authentication.tokens import get_token_service

        token_service = get_token_service()
        tokens = token_service.generate_tokens(
            user=user,
            device_id=overrides.get("device_id", "test-device"),
            ip_address=overrides.get("ip_address", "127.0.0.1"),
            user_agent=overrides.get("user_agent", "test-agent"),
        )
        return tokens

    @classmethod
    def create_access_token(cls, user, **overrides):
        """Create only an access token."""
        from authentication.tokens import get_token_service

        token_service = get_token_service()
        tokens = token_service.generate_tokens(
            user=user,
            device_id=overrides.get("device_id", "test-device"),
            ip_address=overrides.get("ip_address", "127.0.0.1"),
            user_agent=overrides.get("user_agent", "test-agent"),
        )
        return tokens.access_token

    @classmethod
    def create_refresh_token(cls, user, **overrides):
        """Create only a refresh token."""
        from authentication.tokens import get_token_service

        token_service = get_token_service()
        tokens = token_service.generate_tokens(
            user=user,
            device_id=overrides.get("device_id", "test-device"),
            ip_address=overrides.get("ip_address", "127.0.0.1"),
            user_agent=overrides.get("user_agent", "test-agent"),
        )
        return tokens.refresh_token


class JWKSFactory:
    """Factory for creating test JWKS keys."""

    @staticmethod
    def generate_keypair():
        """Generate a new RSA keypair."""
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = private_key.public_key()

        return {
            "private_pem": private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            ),
            "public_pem": public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            ),
        }

    @staticmethod
    def save_keys_to_dir(keys: dict, directory):
        """Save generated keys to directory."""
        from pathlib import Path

        keys_dir = Path(directory)
        keys_dir.mkdir(exist_ok=True)

        public_path = keys_dir / "jwt-public.pem"
        private_path = keys_dir / "jwt-private.pem"

        public_path.write_bytes(keys["public_pem"])
        private_path.write_bytes(keys["private_pem"])

        return {"public_path": public_path, "private_path": private_path}
