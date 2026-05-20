"""
authentication/oauth/encryption.py

Symmetric Fernet encryption for OAuth access/refresh tokens stored in the DB.
Key is loaded from OAUTH_TOKEN_ENCRYPTION_KEY env var (path to .key file
OR raw base64 key value).

Shared by all OAuth providers.
"""

from __future__ import annotations

import logging
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

logger = logging.getLogger(__name__)


class TokenEncryptionError(Exception):
    """Custom exception for token encryption and decryption failures."""

    pass


class TokenEncryptionService:
    def __init__(self) -> None:
        self._fernet: Fernet | None = None

    @property
    def fernet(self) -> Fernet:
        """Lazily initializes and caches the Fernet instance."""
        if self._fernet is None:
            self._fernet = Fernet(self._load_key())
        return self._fernet

    def _load_key(self) -> bytes:
        """
        Load the Fernet key.

        OAUTH_TOKEN_ENCRYPTION_KEY may be:
          - A file path  →  read and strip the key from the file
          - A raw base64 URL-safe key  →  use directly
        """
        raw = getattr(settings, "OAUTH_TOKEN_ENCRYPTION_KEY", "")
        if not raw:
            raise TokenEncryptionError("OAUTH_TOKEN_ENCRYPTION_KEY not configured")

        path = Path(str(raw))
        try:
            if path.exists() and path.is_file():
                key = path.read_bytes().strip()
                # If the file itself contains a path (misconfiguration guard)
                if b"/" in key or b"\\" in key:
                    raise TokenEncryptionError(
                        f"OAUTH_TOKEN_ENCRYPTION_KEY file at {path} appears to contain "
                        "a path, not a key. Check your configuration."
                    )
                return key
        except OSError as e:
            raise TokenEncryptionError(f"Failed to read key file at {path}") from e

        # Treat as raw key value
        try:
            # Fernet key must be 32 URL-safe base64-encoded bytes.
            # We convert to bytes to let Fernet handle final structural validation.
            return raw.encode()
        except Exception as exc:
            raise TokenEncryptionError(
                "OAUTH_TOKEN_ENCRYPTION_KEY is neither a valid file path nor a "
                "valid Fernet key. "
                'Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
            ) from exc

    def encrypt(self, plain_token: str) -> str:
        """Alias for encrypt_token."""
        return self.encrypt_token(plain_token)

    def decrypt(self, encrypted_token: str) -> str | None:
        """Alias for decrypt_token. Raises on empty token."""
        if not encrypted_token:
            raise TokenEncryptionError("Cannot decrypt empty token")
        return self.decrypt_token(encrypted_token)

    def encrypt_token(self, plain_token: str) -> str:
        """Encrypt a token string. Returns base64-encoded ciphertext."""
        if not plain_token:
            raise TokenEncryptionError("Cannot encrypt empty token")
        try:
            return self.fernet.encrypt(plain_token.encode()).decode()
        except Exception as e:
            logger.error("token_encryption_failed", extra={"error": str(e)})
            raise TokenEncryptionError("Failed to encrypt token") from e

    def decrypt_token(self, encrypted_token: str) -> str | None:
        """
        Decrypt a token string. Returns None on failure instead of raising,
        so callers can handle gracefully without crashing.
        """
        if not encrypted_token:
            return None
        try:
            return self.fernet.decrypt(encrypted_token.encode()).decode()
        except InvalidToken:
            logger.warning("oauth_token_decryption_failed: InvalidToken")
            return None
        except Exception:
            logger.exception("oauth_token_decryption_failed: unexpected error")
            return None


# Global singleton instance management
_encryption_service: TokenEncryptionService | None = None


def get_encryption_service() -> TokenEncryptionService:
    """Helper function to fetch the single instance of TokenEncryptionService."""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = TokenEncryptionService()
    return _encryption_service


def encrypt_token(plain_token: str) -> str:
    """Convenience wrapper to encrypt a token using the global service."""
    return get_encryption_service().encrypt_token(plain_token)


def decrypt_token(encrypted_token: str) -> str | None:
    """Convenience wrapper to decrypt a token using the global service."""
    return get_encryption_service().decrypt_token(encrypted_token)


def generate_fernet_key() -> str:
    """Helper to generate a fresh key — use during initial setup."""
    return Fernet.generate_key().decode()
