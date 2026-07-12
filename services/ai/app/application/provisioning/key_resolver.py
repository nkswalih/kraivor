import base64
import logging
import os
from cryptography.fernet import Fernet

from app.core.config import settings
from app.core.exceptions import InsufficientQuotaError

logger = logging.getLogger(__name__)

PROVIDER_FIELD_MAP = {
    "openrouter": "openrouter_subkey_encrypted",
    "groq": "groq_key_encrypted",
    "google": "google_key_encrypted",
}


def _model_to_provider(model: str) -> str:
    model_lower = model.lower()
    if "groq" in model_lower or "llama" in model_lower or "mixtral" in model_lower:
        return "groq"
    if "gemini" in model_lower:
        return "google"
    if "anthropic" in model_lower or "claude" in model_lower:
        return "anthropic"
    if (
        "openai" in model_lower
        or "gpt" in model_lower
        or "text-embedding" in model_lower
    ):
        return "openai"
    if "deepseek" in model_lower:
        return "openrouter"
    return "openrouter"


async def resolve_provider_key(
    db_session, encrypter: Fernet, user_id: str, preferred_model: str | None = None
) -> tuple[str, str]:
    from sqlalchemy import select

    from app.infrastructure.db.models.api_key import ApiKey

    result = await db_session.execute(
        select(ApiKey).where(ApiKey.user_id == user_id, not ApiKey.revoked)
    )
    key_record = result.scalar_one_or_none()
    if not key_record:
        logger.warning(
            "no provisioned key for user %s, falling back to master key", user_id
        )
        return settings.openrouter__master__key, "openrouter"

    provider = _model_to_provider(preferred_model or "openrouter")
    field_name = PROVIDER_FIELD_MAP.get(provider)
    encrypted_key = getattr(key_record, field_name, None) if field_name else None

    if encrypted_key:
        try:
            decrypted = encrypter.decrypt(encrypted_key.encode())
            return decrypted.decode(), provider
        except Exception:
            logger.warning("key_decryption_failed", user_id=user_id, provider=provider)

    for fallback_provider in ["openrouter", "groq", "google"]:
        fb_field = PROVIDER_FIELD_MAP.get(fallback_provider)
        encrypted = getattr(key_record, fb_field, None) if fb_field else None
        if encrypted:
            decrypted = encrypter.decrypt(encrypted.encode())
            return decrypted.decode(), fallback_provider

    raise InsufficientQuotaError("No usable provider keys available")


_key = settings.key_encryption_key or base64.urlsafe_b64encode(os.urandom(32)).decode()
_default_encrypter = Fernet(_key.encode() if isinstance(_key, str) else _key)


class KeyResolver:
    def __init__(self, encrypter: Fernet | None = None):
        self.encrypter = encrypter or _default_encrypter

    async def resolve(
        self, user_id: str, preferred_model: str | None = None
    ) -> tuple[str, str]:
        from app.infrastructure.db.database import async_session_factory

        async with async_session_factory() as session:
            return await resolve_provider_key(
                db_session=session,
                encrypter=self.encrypter,
                user_id=user_id,
                preferred_model=preferred_model,
            )
