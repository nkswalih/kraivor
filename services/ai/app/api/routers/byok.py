"""Dedicated BYOK router — provider key management and model-provider assignment."""

import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies.auth import JWTPayload, get_current_user
from app.api.schemas.byok import (
    ByokModelConfig,
    ModelProviderOption,
    ModelProviderUpdate,
    ProviderKeyUpdate,
    ProviderStatus,
    ValidateResult,
)
from app.application.provisioning.key_validator import validate_key
from app.application.provisioning.provider_models import (
    BYOK_MODEL_INFO,
    BYOK_MODEL_PROVIDERS,
    PROVIDER_DISPLAY_NAMES,
    PROVIDER_KEY_COLUMN,
    PROVIDER_VALIDATED_COLUMN,
    PROVIDER_URL_COLUMN,
    get_models_for_provider,
)
from app.infrastructure.cache.redis_client import get_redis
from app.infrastructure.db.database import async_session_factory
from app.infrastructure.db.models.api_key import ApiKey

logger = logging.getLogger(__name__)

CurrentUser = Annotated[JWTPayload, Depends(get_current_user)]

router = APIRouter(tags=["byok"], prefix="/byok")

# Cache for BYOK model-provider assignments (user-specific)
_ASSIGNMENT_CACHE_TTL = 300  # 5 minutes


async def _get_key_record(db, user_id: str) -> ApiKey | None:
    from sqlalchemy import select

    result = await db.execute(
        select(ApiKey).where(ApiKey.user_id == user_id, ApiKey.revoked.is_(False))  # noqa: B015
    )
    return result.scalar_one_or_none()


async def _get_user_provider_preference(user_id: str, model_id: str) -> str | None:
    """Get user's provider preference for a model from Redis cache."""
    try:
        redis = await get_redis()
        val = await redis.get(f"byok:pref:{user_id}:{model_id}")
        return val.decode() if val else None
    except Exception:
        return None


async def _set_user_provider_preference(user_id: str, model_id: str, provider: str) -> None:
    """Cache user's provider preference for a model in Redis."""
    try:
        redis = await get_redis()
        await redis.set(
            f"byok:pref:{user_id}:{model_id}",
            provider,
            ex=_ASSIGNMENT_CACHE_TTL,
        )
    except Exception:
        logger.debug("redis_cache_skip model=%s provider=%s", model_id, provider)


# ── GET /byok/models — all BYOK models with user's provider selection ──


@router.get("/models")
async def list_byok_models(user: CurrentUser):
    """Return all BYOK models with available providers and user's current selection."""
    from app.application.provisioning.key_resolver import _default_encrypter

    async with async_session_factory() as db:
        key_record = await _get_key_record(db, user.sub)

    configs = []
    for model_id, info in BYOK_MODEL_INFO.items():
        available = BYOK_MODEL_PROVIDERS.get(model_id, [])
        options = [
            ModelProviderOption(
                provider=p["provider"],
                name=PROVIDER_DISPLAY_NAMES.get(p["provider"], p["provider"]),
                default_base_url=p["default_url"],
            )
            for p in available
        ]

        # Check user's preference (from Redis or first available)
        pref_provider = await _get_user_provider_preference(user.sub, model_id)
        if not pref_provider and available:
            pref_provider = available[0]["provider"]

        has_key = False
        custom_url = None
        last_validated = None

        if pref_provider and key_record:
            key_col = PROVIDER_KEY_COLUMN.get(pref_provider)
            url_col = PROVIDER_URL_COLUMN.get(pref_provider)
            val_col = PROVIDER_VALIDATED_COLUMN.get(pref_provider)

            if key_col:
                encrypted = getattr(key_record, key_col, None)
                if encrypted:
                    try:
                        _default_encrypter.decrypt(encrypted.encode())
                        has_key = True
                    except Exception:
                        has_key = False

            if url_col:
                custom_url = getattr(key_record, url_col, None)

            if val_col:
                last_validated = getattr(key_record, val_col, None)

        configs.append(ByokModelConfig(
            model_id=model_id,
            model_name=info["name"],
            backend_model=f"{info['provider']}/{info['name'].lower().replace(' ', '-')}",
            available_providers=options,
            selected_provider=pref_provider,
            has_key=has_key,
            custom_url=custom_url,
            last_validated=last_validated,
        ))

    return {"models": [c.model_dump() for c in configs]}


# ── PUT /byok/models/{model_id} — assign provider to model ──


@router.put("/models/{model_id}")
async def update_model_provider(
    model_id: str,
    body: ModelProviderUpdate,
    user: CurrentUser,
):
    """Set which provider to use for a specific model."""
    available = BYOK_MODEL_PROVIDERS.get(model_id)
    if not available:
        raise HTTPException(status_code=404, detail=f"Unknown BYOK model: {model_id}")

    valid_providers = [p["provider"] for p in available]
    if body.provider not in valid_providers:
        raise HTTPException(
            status_code=400,
            detail=f"Provider '{body.provider}' is not available for {model_id}. "
            f"Available: {valid_providers}",
        )

    await _set_user_provider_preference(user.sub, model_id, body.provider)

    return {"ok": True, "model_id": model_id, "provider": body.provider}


# ── GET /byok/providers — all providers with status ──


@router.get("/providers")
async def list_providers(user: CurrentUser):
    """Return all providers with key status, model count, and metadata."""
    from app.application.provisioning.key_resolver import _default_encrypter

    async with async_session_factory() as db:
        key_record = await _get_key_record(db, user.sub)

    providers = []
    for provider, display_name in PROVIDER_DISPLAY_NAMES.items():
        models = get_models_for_provider(provider)
        has_key = False
        custom_url = None
        last_validated = None

        if key_record:
            key_col = PROVIDER_KEY_COLUMN.get(provider)
            url_col = PROVIDER_URL_COLUMN.get(provider)
            val_col = PROVIDER_VALIDATED_COLUMN.get(provider)

            if key_col:
                encrypted = getattr(key_record, key_col, None)
                if encrypted:
                    try:
                        _default_encrypter.decrypt(encrypted.encode())
                        has_key = True
                    except Exception:
                        has_key = False

            if url_col:
                custom_url = getattr(key_record, url_col, None)

            if val_col:
                last_validated = getattr(key_record, val_col, None)

        providers.append(ProviderStatus(
            provider=provider,
            name=display_name,
            has_key=has_key,
            model_count=len(models),
            models=models,
            custom_url=custom_url,
            last_validated=last_validated,
        ))

    return {"providers": [p.model_dump() for p in providers]}


# ── POST /byok/providers/{provider}/validate — validate a key ──


@router.post("/providers/{provider}/validate")
async def validate_provider_key(
    provider: str,
    body: ProviderKeyUpdate,
    _user: CurrentUser,
):
    """Validate an API key by sending a test request to the provider."""
    if provider not in PROVIDER_DISPLAY_NAMES:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    result: ValidateResult = await validate_key(
        provider=provider,
        api_key=body.api_key,
        custom_url=body.custom_url,
    )
    return result.model_dump()


# ── POST /byok/providers/{provider} — save/update key ──


@router.post("/providers/{provider}")
async def save_provider_key(
    provider: str,
    body: ProviderKeyUpdate,
    user: CurrentUser,
):
    """Save or update an API key for a provider. Validates before storing."""
    if provider not in PROVIDER_DISPLAY_NAMES:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    # Validate the key first
    result = await validate_key(
        provider=provider,
        api_key=body.api_key,
        custom_url=body.custom_url,
    )
    if not result.valid:
        raise HTTPException(
            status_code=400,
            detail=f"Key validation failed: {result.error}",
        )

    from app.application.provisioning.key_resolver import _default_encrypter

    key_col = PROVIDER_KEY_COLUMN[provider]
    url_col = PROVIDER_URL_COLUMN[provider]
    val_col = PROVIDER_VALIDATED_COLUMN[provider]
    encrypted = _default_encrypter.encrypt(body.api_key.encode()).decode()

    async with async_session_factory() as db:
        key_record = await _get_key_record(db, user.sub)
        if not key_record:
            raise HTTPException(
                status_code=404,
                detail="No API key record found. Contact support.",
            )

        setattr(key_record, key_col, encrypted)
        setattr(key_record, url_col, body.custom_url)
        setattr(key_record, val_col, datetime.now(UTC))
        await db.commit()

    return {"ok": True, "provider": provider}


# ── DELETE /byok/providers/{provider} — remove key ──


@router.delete("/providers/{provider}")
async def remove_provider_key(
    provider: str,
    user: CurrentUser,
):
    """Remove an API key for a provider."""
    if provider not in PROVIDER_DISPLAY_NAMES:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    key_col = PROVIDER_KEY_COLUMN[provider]
    url_col = PROVIDER_URL_COLUMN[provider]
    val_col = PROVIDER_VALIDATED_COLUMN[provider]

    async with async_session_factory() as db:
        key_record = await _get_key_record(db, user.sub)
        if key_record:
            setattr(key_record, key_col, None)
            setattr(key_record, url_col, None)
            setattr(key_record, val_col, None)
            await db.commit()

    # Invalidate cache
    try:
        redis = await get_redis()
        models = get_models_for_provider(provider)
        for model_id in models:
            await redis.delete(f"byok:pref:{user.sub}:{model_id}")
    except Exception:
        pass

    return {"ok": True, "provider": provider}
