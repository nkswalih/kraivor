from cryptography.fernet import Fernet

from app.core.config import settings


def get_encrypter() -> Fernet:
    """Build a Fernet encrypter from the configured key.

    Raises ValueError if the key is missing or malformed. It does not
    substitute a generated key: that would produce a different encrypter
    on every process start, so anything encrypted with a misconfigured key
    becomes permanently unreadable, silently.
    """
    key = settings.key_encryption_key
    if not key:
        msg = (
            "AI_KEY_ENCRYPTION_KEY is not set. "
            "Generate one with: "
            'python -c "from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())"'
        )
        raise ValueError(msg)
    key_bytes = key.encode() if isinstance(key, str) else key
    try:
        return Fernet(key_bytes)
    except (ValueError, TypeError) as exc:
        msg = (
            f"AI_KEY_ENCRYPTION_KEY is malformed: {exc}. "
            "It must be a 32-byte url-safe base64 string as produced by "
            'Fernet.generate_key(). Note that secrets.token_hex(32) is NOT '
            "valid here — it yields 64 hex characters, which Fernet rejects."
        )
        raise ValueError(msg) from exc
