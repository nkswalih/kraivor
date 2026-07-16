import json
from typing import Annotated

import uuid
from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from app.api.dependencies.auth import JWTPayload, get_current_user
from app.api.dependencies.rate_limiter import check_rate_limit
from app.api.schemas.chat import ChatRequest, ChatResponse
from app.application.chat.chat_service import ChatService
from app.infrastructure.llm.router import (
    ALL_MODEL_IDS,
    BYOK_MODELS,
    FREE_MODELS,
    KRAIVOR_MODEL,
    MODEL_BACKEND_MAP,
)

CurrentUser = Annotated[JWTPayload, Depends(get_current_user)]
RateLimit = Annotated[None, Depends(check_rate_limit)]

router = APIRouter(tags=["chat"])

chat_service = ChatService()


# ── Model tier metadata (mirrors frontend TIER_CONFIG) ──────
_MODEL_META = {
    KRAIVOR_MODEL: {"tier": "kraivor", "provider": "kraivor", "name": "Krait 2.0", "latency": "0.4s", "context": "128K"},
    "cohere-north-mini-code": {"tier": "free", "provider": "cohere", "name": "Cohere North Mini", "latency": "0.6s", "context": "128K"},
    "nvidia-nemotron-ultra": {"tier": "free", "provider": "nvidia", "name": "Nvidia Nemotron Ultra", "latency": "2.0s", "context": "1M"},
    "tencent-hy3": {"tier": "free", "provider": "tencent", "name": "Tencent HY3", "latency": "3.4s", "context": "262K"},
    "poolside-laguna-xs": {"tier": "free", "provider": "poolside", "name": "Poolside Laguna XS", "latency": "0.8s", "context": "128K"},
    "poolside-laguna-m": {"tier": "free", "provider": "poolside", "name": "Poolside Laguna M", "latency": "1.2s", "context": "128K"},
    "nvidia-nemotron-super": {"tier": "free", "provider": "nvidia", "name": "Nvidia Nemotron Super", "latency": "2.5s", "context": "128K"},
    "google-gemma-4": {"tier": "free", "provider": "google", "name": "Google Gemma 4", "latency": "1.0s", "context": "128K"},
    "nvidia-nemotron-nano": {"tier": "free", "provider": "nvidia", "name": "Nvidia Nemotron Nano", "latency": "0.6s", "context": "128K"},
    "openai-gpt-oss": {"tier": "free", "provider": "openai", "name": "OpenAI GPT OSS", "latency": "1.8s", "context": "128K"},
    "claude-fable-5": {"tier": "byok", "provider": "anthropic", "name": "Claude Fable 5", "latency": "1.5s", "context": "200K"},
    "claude-opus-4-8": {"tier": "byok", "provider": "anthropic", "name": "Claude Opus 4.8", "latency": "2.0s", "context": "200K"},
    "claude-opus-4-7": {"tier": "byok", "provider": "anthropic", "name": "Claude Opus 4.7", "latency": "2.2s", "context": "200K"},
    "claude-sonnet-5": {"tier": "byok", "provider": "anthropic", "name": "Claude Sonnet 5", "latency": "1.2s", "context": "200K"},
    "claude-sonnet-4-6": {"tier": "byok", "provider": "anthropic", "name": "Claude Sonnet 4.6", "latency": "1.0s", "context": "200K"},
    "gpt-5.6-sol": {"tier": "byok", "provider": "openai", "name": "GPT-5.6 Sol", "latency": "1.0s", "context": "128K"},
    "gpt-5.6-terra": {"tier": "byok", "provider": "openai", "name": "GPT-5.6 Terra", "latency": "1.2s", "context": "128K"},
    "gpt-5.5": {"tier": "byok", "provider": "openai", "name": "GPT-5.5", "latency": "0.9s", "context": "128K"},
    "gpt-5.4": {"tier": "byok", "provider": "openai", "name": "GPT-5.4", "latency": "0.8s", "context": "128K"},
    "gemini-3.5-flash": {"tier": "byok", "provider": "google", "name": "Gemini 3.5 Flash", "latency": "0.5s", "context": "1M"},
    "gemini-3.1-pro": {"tier": "byok", "provider": "google", "name": "Gemini 3.1 Pro", "latency": "1.5s", "context": "1M"},
    "deepseek-v4-pro": {"tier": "byok", "provider": "deepseek", "name": "DeepSeek V4 Pro", "latency": "1.0s", "context": "128K"},
    "grok-4.3": {"tier": "byok", "provider": "xai", "name": "Grok 4.3", "latency": "1.5s", "context": "128K"},
}


@router.post("/chat")
async def chat(request: ChatRequest, user: CurrentUser, _: RateLimit = None):
    conv_id = request.conversation_id or str(uuid.uuid4())

    if request.stream:

        async def event_generator():
            async for chunk in chat_service.stream_chat(
                user_id=user.sub,
                message=request.message,
                conversation_id=conv_id,
                workspace_id=request.workspace_id,
                repo_ids=request.repo_ids,
                history=None,
                user_name=user.name,
                model=request.model,
            ):
                if chunk.get("done"):
                    yield {"event": "done", "data": json.dumps(chunk)}
                else:
                    yield {"event": "chunk", "data": json.dumps(chunk)}

        return EventSourceResponse(event_generator())

    result = await chat_service.chat(
        user_id=user.sub,
        message=request.message,
        conversation_id=conv_id,
        workspace_id=request.workspace_id,
        repo_ids=request.repo_ids,
        user_name=user.name,
        model=request.model,
    )

    usage_info = result.get("usage") or {}
    return ChatResponse(
        conversation_id=conv_id,
        message_id=str(uuid.uuid4()),
        content=result.get("response", ""),
        model=usage_info.get("model", "unknown"),
        usage=usage_info,
        sources=result.get("sources"),
    )


@router.post("/completions")
async def completions(request: dict, user: CurrentUser, _: RateLimit = None):
    conv_id = str(uuid.uuid4())
    result = await chat_service.chat(
        user_id=user.sub,
        message=request.get("messages", [{}])[-1].get("content", ""),
        workspace_id=request.get("workspace_id", ""),
        user_name=user.name,
        model=request.get("model"),
    )
    usage_info = result.get("usage") or {}
    return ChatResponse(
        conversation_id=conv_id,
        message_id=str(uuid.uuid4()),
        content=result.get("response", ""),
        model=usage_info.get("model", "unknown"),
        usage=usage_info,
        sources=result.get("sources"),
    )


@router.get("/models")
async def list_models(user: CurrentUser):
    models = []
    for mid in ALL_MODEL_IDS:
        meta = _MODEL_META.get(mid, {})
        models.append({
            "id": mid,
            "name": meta.get("name", mid),
            "tier": meta.get("tier", "free"),
            "provider": meta.get("provider", "openrouter"),
            "latency": meta.get("latency"),
            "context": meta.get("context"),
            "backendModel": MODEL_BACKEND_MAP.get(mid),
        })
    return {"models": models, "default": KRAIVOR_MODEL}


# ── BYOK key management endpoints ────────────────────────────

@router.get("/byok/status")
async def byok_status(user: CurrentUser):
    """Return which BYOK providers the user has keys for."""
    from sqlalchemy import select
    from app.infrastructure.db.database import async_session_factory
    from app.infrastructure.db.models.api_key import ApiKey
    from app.application.provisioning.key_resolver import _default_encrypter

    async with async_session_factory() as db:
        result = await db.execute(
            select(ApiKey).where(ApiKey.user_id == user.sub, not ApiKey.revoked)
        )
        key_record = result.scalar_one_or_none()

    providers = {}
    if key_record:
        for provider, field in [
            ("openrouter", "openrouter_subkey_encrypted"),
            ("groq", "groq_key_encrypted"),
            ("google", "google_key_encrypted"),
            ("anthropic", "anthropic_key_encrypted"),
            ("openai", "openai_key_encrypted"),
            ("deepseek", "deepseek_key_encrypted"),
            ("xai", "xai_key_encrypted"),
        ]:
            encrypted = getattr(key_record, field, None)
            if encrypted:
                try:
                    _default_encrypter.decrypt(encrypted.encode())
                    providers[provider] = True
                except Exception:
                    providers[provider] = False
            else:
                providers[provider] = False

    return {"providers": providers}


@router.post("/byok/submit")
async def byok_submit(request: dict, user: CurrentUser):
    """Store an encrypted BYOK key for a provider.

    Request body: {"provider": "anthropic"|"openai"|"deepseek"|"xai"|"google"|"groq", "api_key": "sk-..."}
    """
    provider = request.get("provider", "")
    api_key = request.get("api_key", "")
    if not provider or not api_key:
        return {"error": "provider and api_key are required"}

    from app.application.provisioning.key_resolver import (
        PROVIDER_FIELD_MAP,
        _default_encrypter,
    )

    field = PROVIDER_FIELD_MAP.get(provider)
    if not field:
        return {"error": f"Unknown provider: {provider}"}

    encrypted = _default_encrypter.encrypt(api_key.encode()).decode()

    from sqlalchemy import select
    from app.infrastructure.db.database import async_session_factory
    from app.infrastructure.db.models.api_key import ApiKey

    async with async_session_factory() as db:
        result = await db.execute(
            select(ApiKey).where(ApiKey.user_id == user.sub, not ApiKey.revoked)
        )
        key_record = result.scalar_one_or_none()

        if not key_record:
            return {"error": "No API key record found. Contact support."}

        setattr(key_record, field, encrypted)
        await db.commit()

    return {"ok": True, "provider": provider}


@router.delete("/byok/{provider}")
async def byok_remove(provider: str, user: CurrentUser):
    """Remove a BYOK key for a provider."""
    from app.application.provisioning.key_resolver import PROVIDER_FIELD_MAP

    field = PROVIDER_FIELD_MAP.get(provider)
    if not field:
        return {"error": f"Unknown provider: {provider}"}

    from sqlalchemy import select
    from app.infrastructure.db.database import async_session_factory
    from app.infrastructure.db.models.api_key import ApiKey

    async with async_session_factory() as db:
        result = await db.execute(
            select(ApiKey).where(ApiKey.user_id == user.sub, not ApiKey.revoked)
        )
        key_record = result.scalar_one_or_none()

        if key_record:
            setattr(key_record, field, None)
            await db.commit()

    return {"ok": True, "provider": provider}
