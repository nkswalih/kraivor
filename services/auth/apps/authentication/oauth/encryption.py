"""
OAuth Token Encryption Service
"""

import logging

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

logger = logging.getLogger(__name__)


class TokenEncryptionError(Exception):
    pass


class TokenEncryptionService:
    def __init__(self):
        self._fernet = None

    @property
    def fernet(self) -> Fernet:
        if self._fernet is None:
            key_path = getattr(settings, "OAUTH_TOKEN_ENCRYPTION_KEY", None)
            if not key_path:
                raise TokenEncryptionError("OAUTH_TOKEN_ENCRYPTION_KEY not configured")
            try:
                with open(key_path, "rb") as f:
                    key = f.read()
                if len(key) != 32:
                    key = Fernet.generate_key()
                    with open(key_path, "wb") as f:
                        f.write(key)
                self._fernet = Fernet(key)
            except FileNotFoundError:
                key = Fernet.generate_key()
                self._fernet = Fernet(key)
                with open(key_path, "wb") as f:
                    f.write(key)
        return self._fernet

    def encrypt(self, token: str) -> str:
        if not token:
            raise TokenEncryptionError("Cannot encrypt empty token")
        try:
            return self.fernet.encrypt(token.encode()).decode()
        except Exception as e:
            logger.error("token_encryption_failed", extra={"error": str(e)})
            raise TokenEncryptionError("Failed to encrypt token") from e

    def decrypt(self, encrypted_token: str) -> str:
        if not encrypted_token:
            raise TokenEncryptionError("Cannot decrypt empty token")
        try:
            return self.fernet.decrypt(encrypted_token.encode()).decode()
        except InvalidToken:
            raise TokenEncryptionError("Invalid encrypted token") from None
        except Exception as e:
            logger.error("token_decryption_failed", extra={"error": str(e)})
            raise TokenEncryptionError("Failed to decrypt token") from e


_encryption_service = None


def get_encryption_service() -> TokenEncryptionService:
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = TokenEncryptionService()
    return _encryption_service