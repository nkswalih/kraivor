import logging
from cryptography.fernet import Fernet

from app.core.config import settings
from app.core.exceptions import InsufficientQuotaError

logger = logging.getLogger(__name__)

KEY_CACHE_TTL = 600  # 10 minutes


def _key_cache_key(user_id: str, preferred_model: str | None) -> str:
    return f"apikey:{user_id}:{preferred_model or 'default'}"

if not settings.key_encryption_key:
    logger.critical(
        "AI_KEY_ENCRYPTION_KEY is not set. "
        "All BYOK encryption will fail. Set this in your .env file."
    )

# ── Maps provider name → column on ai.api_keys ──────────────
PROVIDER_FIELD_MAP = {
    "openrouter": "openrouter_subkey_encrypted",
    "groq": "groq_key_encrypted",
    "google": "google_key_encrypted",
    "anthropic": "anthropic_key_encrypted",
    "openai": "openai_key_encrypted",
    "deepseek": "deepseek_key_encrypted",
    "xai": "xai_key_encrypted",
}

# ── Smart key detection: prefix → provider ──────────────────
_KEY_PREFIX_MAP = [
    ("sk-or-v1-", "openrouter"),
    ("sk-ant-", "anthropic"),
    ("sk-", "openai"),
    ("AIza", "google"),
    ("gsk_", "groq"),
    ("sk-", "deepseek"),   # deepseek also uses sk- prefix but different base
    ("xai-", "xai"),
]


def detect_provider_from_key(api_key: str) -> str | None:
    """Detect which provider an API key belongs to based on its prefix."""
    for prefix, provider in _KEY_PREFIX_MAP:
        if api_key.startswith(prefix):
            return provider
    return None


def _model_to_provider(model: str) -> str:
    model_lower = model.lower()
    if "groq" in model_lower or "llama" in model_lower or "mixtral" in model_lower or "qwen" in model_lower:
        return "groq"
    if "gemini" in model_lower or "gemma" in model_lower:
        return "google"
    if "anthropic" in model_lower or "claude" in model_lower:
        return "anthropic"
    if "openai" in model_lower or "gpt" in model_lower or "text-embedding" in model_lower:
        return "openai"
    if "deepseek" in model_lower:
        return "deepseek"
    if "xai" in model_lower or "grok" in model_lower:
        return "xai"
    if "nvidia" in model_lower or "nemotron" in model_lower:
        return "openrouter"
    if "tencent" in model_lower or "hy3" in model_lower:
        return "openrouter"
    if "poolside" in model_lower or "laguna" in model_lower:
        return "openrouter"
    if "cohere" in model_lower or "north" in model_lower:
        return "openrouter"
    return "openrouter"


# ── Fallback order when the preferred provider has no key ────
_FALLBACK_ORDER = ["openrouter", "groq", "google", "anthropic", "openai", "deepseek", "xai"]


async def resolve_provider_key(
    db_session, encrypter: Fernet, user_id: str, preferred_model: str | None = None
) -> tuple[str, str]:
    from sqlalchemy import select

    from app.infrastructure.db.models.api_key import ApiKey

    provider = _model_to_provider(preferred_model or "openrouter")

    result = await db_session.execute(
        select(ApiKey).where(ApiKey.user_id == user_id, ApiKey.revoked.is_(False))
    )
    key_record = result.scalar_one_or_none()

    # If user has a BYOK key for the requested provider, use it
    if key_record:
        field_name = PROVIDER_FIELD_MAP.get(provider)
        encrypted_key = getattr(key_record, field_name, None) if field_name else None
        if encrypted_key:
            try:
                decrypted = encrypter.decrypt(encrypted_key.encode())
                logger.info("using_byok_key user=%s provider=%s", user_id, provider)
                return decrypted.decode(), provider
            except Exception:
                logger.warning("key_decryption_failed", user_id=user_id, provider=provider)

    # System Groq key for Groq models — only if user doesn't have their own
    if provider == "groq" and settings.groq_api_key:
        logger.info("using_system_groq_key user=%s", user_id)
        return settings.groq_api_key, "groq"

    if not key_record:
        logger.warning(
            "no provisioned key for user %s, falling back to master key", user_id
        )
        return settings.openrouter__master__key, "openrouter"

    # Walk fallback chain — always try OpenRouter first since it can proxy any model
    for fallback_provider in _FALLBACK_ORDER:
        fb_field = PROVIDER_FIELD_MAP.get(fallback_provider)
        encrypted = getattr(key_record, fb_field, None) if fb_field else None
        if encrypted:
            try:
                decrypted = encrypter.decrypt(encrypted.encode())
                return decrypted.decode(), fallback_provider
            except Exception:
                continue

    raise InsufficientQuotaError("No usable provider keys available")


_key = settings.key_encryption_key
if not _key:
    raise RuntimeError(
        "AI_KEY_ENCRYPTION_KEY must be set. "
        "Generate with: python -c \"import secrets; print(secrets.token_hex(32))\""
    )
_default_encrypter = Fernet(_key.encode() if isinstance(_key, str) else _key)


class KeyResolver:
    def __init__(self, encrypter: Fernet | None = None):
        self.encrypter = encrypter or _default_encrypter

    async def resolve(
        self, user_id: str, preferred_model: str | None = None
    ) -> tuple[str, str]:
        cache_key = _key_cache_key(user_id, preferred_model)

        try:
            from app.infrastructure.cache.redis_client import get_redis
            r = await get_redis()
            cached = await r.get(cache_key)
            if cached:
                import json
                data = json.loads(cached)
                encrypted_key = data.get("encrypted_key", "")
                provider = data.get("provider", "openrouter")
                decrypted = self.encrypter.decrypt(encrypted_key.encode()).decode()
                return decrypted, provider
        except Exception:
            pass

        from app.infrastructure.db.database import async_session_factory

        async with async_session_factory() as session:
            api_key, provider = await resolve_provider_key(
                db_session=session,
                encrypter=self.encrypter,
                user_id=user_id,
                preferred_model=preferred_model,
            )

        try:
            from app.infrastructure.cache.redis_client import get_redis
            import json
            r = await get_redis()
            encrypted = self.encrypter.encrypt(api_key.encode()).decode()
            await r.setex(cache_key, KEY_CACHE_TTL, json.dumps({
                "encrypted_key": encrypted,
                "provider": provider,
            }))
        except Exception:
            pass

        return api_key, provider

    async def invalidate(self, user_id: str, preferred_model: str | None = None) -> None:
        try:
            from app.infrastructure.cache.redis_client import get_redis
            r = await get_redis()
            await r.delete(_key_cache_key(user_id, preferred_model))
        except Exception:
            pass
