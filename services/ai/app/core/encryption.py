from cryptography.fernet import Fernet

from app.core.config import settings


def get_encrypter() -> Fernet:
    key = settings.key_encryption_key
    if not key:
        msg = "AI_KEY_ENCRYPTION_KEY is not set"
        raise ValueError(msg)
    key_bytes = key.encode() if isinstance(key, str) else key
    if len(key_bytes) not in (32, 44):
        key_bytes = Fernet.generate_key()
    return Fernet(key_bytes)
