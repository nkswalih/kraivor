import json
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

# ── Maps provider name → custom URL column on ai.api_keys ────
PROVIDER_URL_FIELD_MAP = {
    "openrouter": "openrouter_custom_url",
    "groq": "groq_custom_url",
    "google": "google_custom_url",
    "anthropic": "anthropic_custom_url",
    "openai": "openai_custom_url",
    "deepseek": "deepseek_custom_url",
    "xai": "xai_custom_url",
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


async def _get_user_byok_preference(user_id: str, model_id: str) -> str | None:
    """Get user's BYOK provider preference for a model from Redis."""
    try:
        from app.infrastructure.cache.redis_client import get_redis
        r = await get_redis()
        val = await r.get(f"byok:pref:{user_id}:{model_id}")
        return val.decode() if val else None
    except Exception:
        return None


async def resolve_provider_key(
    db_session, encrypter: Fernet, user_id: str, preferred_model: str | None = None
) -> tuple[str, str, str | None]:
    """Resolve API key, provider, and optional custom URL for a model.

    Returns (api_key, provider, custom_url).
    """
    from sqlalchemy import select

    from app.application.provisioning.provider_models import (
        BYOK_MODEL_PROVIDERS,
        PROVIDER_KEY_COLUMN,
        PROVIDER_URL_COLUMN,
    )
    from app.infrastructure.db.models.api_key import ApiKey

    result = await db_session.execute(
        select(ApiKey).where(ApiKey.user_id == user_id, ApiKey.revoked.is_(False))
    )
    key_record = result.scalar_one_or_none()

    # ── BYOK model with user-assigned provider ──
    if preferred_model and preferred_model in BYOK_MODEL_PROVIDERS:
        pref_provider = await _get_user_byok_preference(user_id, preferred_model)
        if pref_provider and key_record:
            key_col = PROVIDER_KEY_COLUMN.get(pref_provider)
            url_col = PROVIDER_URL_COLUMN.get(pref_provider)
            encrypted = getattr(key_record, key_col, None) if key_col else None
            custom_url = getattr(key_record, url_col, None) if url_col else None
            if encrypted:
                try:
                    decrypted = encrypter.decrypt(encrypted.encode())
                    logger.info(
                        "using_byok_key user=%s provider=%s model=%s",
                        user_id, pref_provider, preferred_model,
                    )
                    return decrypted.decode(), pref_provider, custom_url
                except Exception:
                    logger.warning(
                        "key_decryption_failed user=%s provider=%s",
                        user_id, pref_provider,
                    )

    # ── Standard provider resolution ──
    provider = _model_to_provider(preferred_model or "openrouter")

    if key_record:
        field_name = PROVIDER_FIELD_MAP.get(provider)
        url_field = PROVIDER_URL_FIELD_MAP.get(provider)
        encrypted_key = getattr(key_record, field_name, None) if field_name else None
        custom_url = getattr(key_record, url_field, None) if url_field else None
        if encrypted_key:
            try:
                decrypted = encrypter.decrypt(encrypted_key.encode())
                logger.info("using_byok_key user=%s provider=%s", user_id, provider)
                return decrypted.decode(), provider, custom_url
            except Exception:
                logger.warning("key_decryption_failed", user_id=user_id, provider=provider)

    # System Groq key for Groq models — only if user doesn't have their own
    if provider == "groq" and settings.groq_api_key:
        logger.info("using_system_groq_key user=%s", user_id)
        return settings.groq_api_key, "groq", None

    if not key_record:
        logger.warning(
            "no provisioned key for user %s, falling back to master key", user_id
        )
        return settings.openrouter__master__key, "openrouter", None

    # Walk fallback chain — always try OpenRouter first since it can proxy any model
    for fallback_provider in _FALLBACK_ORDER:
        fb_field = PROVIDER_FIELD_MAP.get(fallback_provider)
        fb_url_field = PROVIDER_URL_FIELD_MAP.get(fallback_provider)
        encrypted = getattr(key_record, fb_field, None) if fb_field else None
        custom_url = getattr(key_record, fb_url_field, None) if fb_url_field else None
        if encrypted:
            try:
                decrypted = encrypter.decrypt(encrypted.encode())
                return decrypted.decode(), fallback_provider, custom_url
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
    ) -> tuple[str, str, str | None]:
        """Resolve API key, provider, and optional custom URL.

        Returns (api_key, provider, custom_url).
        """
        cache_key = _key_cache_key(user_id, preferred_model)

        try:
            from app.infrastructure.cache.redis_client import get_redis
            r = await get_redis()
            cached = await r.get(cache_key)
            if cached:
                data = json.loads(cached)
                encrypted_key = data.get("encrypted_key", "")
                provider = data.get("provider", "openrouter")
                custom_url = data.get("custom_url")
                decrypted = self.encrypter.decrypt(encrypted_key.encode()).decode()
                return decrypted, provider, custom_url
        except Exception:
            pass

        from app.infrastructure.db.database import async_session_factory

        async with async_session_factory() as session:
            api_key, provider, custom_url = await resolve_provider_key(
                db_session=session,
                encrypter=self.encrypter,
                user_id=user_id,
                preferred_model=preferred_model,
            )

        try:
            from app.infrastructure.cache.redis_client import get_redis
            r = await get_redis()
            encrypted = self.encrypter.encrypt(api_key.encode()).decode()
            await r.setex(cache_key, KEY_CACHE_TTL, json.dumps({
                "encrypted_key": encrypted,
                "provider": provider,
                "custom_url": custom_url,
            }))
        except Exception:
            pass

        return api_key, provider, custom_url

    async def invalidate(self, user_id: str, preferred_model: str | None = None) -> None:
        try:
            from app.infrastructure.cache.redis_client import get_redis
            r = await get_redis()
            await r.delete(_key_cache_key(user_id, preferred_model))
        except Exception:
            pass
