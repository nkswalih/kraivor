import asyncio
import json
from typing import Annotated

import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from app.api.dependencies.auth import JWTPayload, get_current_user
from app.api.dependencies.backpressure import (
    acquire_llm_slot,
    release_llm_slot,
)
from app.api.dependencies.rate_limiter import check_rate_limit
from app.api.schemas.chat import ChatRequest, ChatResponse
from app.application.chat.chat_service import ChatService
from app.application.usage.usage_service import get_daily_usage_summary
from app.infrastructure.llm.error_classifier import ClassifiedError, ErrorCategory
from app.application.admin.model_registry import ModelRegistry
from app.infrastructure.llm.router import KRAIVOR_MODEL
from app.core.exceptions import AllProvidersFailedError

CurrentUser = Annotated[JWTPayload, Depends(get_current_user)]
RateLimit = Annotated[None, Depends(check_rate_limit)]

router = APIRouter(tags=["chat"])

chat_service = ChatService()

LLM_CHAIN_TIMEOUT = 90


@router.post("/chat")
async def chat(request: ChatRequest, user: CurrentUser, req: Request, _: RateLimit = None):
    conv_id = request.conversation_id or str(uuid.uuid4())
    auth_header = req.headers.get("Authorization", "")
    auth_token = auth_header[7:] if auth_header.startswith("Bearer ") else None

    await acquire_llm_slot()
    try:
        if request.stream:

            async def event_generator():
                try:
                    async for chunk in chat_service.stream_chat(
                        user_id=user.sub,
                        message=request.message,
                        conversation_id=conv_id,
                        workspace_id=request.workspace_id,
                        repo_ids=request.repo_ids,
                        history=None,
                        user_name=user.name,
                        model=request.model,
                        auth_token=auth_token,
                        mode=request.mode,
                    ):
                        if chunk.get("type") == "error":
                            yield {"event": "error", "data": json.dumps(chunk)}
                        elif chunk.get("done"):
                            yield {"event": "done", "data": json.dumps(chunk)}
                        elif chunk.get("status"):
                            yield {"event": "status", "data": json.dumps(chunk)}
                        else:
                            yield {"event": "chunk", "data": json.dumps(chunk)}
                except ClassifiedError as e:
                    yield {"event": "error", "data": json.dumps({
                        "type": "error",
                        "error": e.user_message,
                        "category": e.category.value,
                        "suggested_action": e.suggested_action.value,
                        "retry_after": e.retry_after,
                    })}
                except AllProvidersFailedError:
                    yield {"event": "error", "data": json.dumps({
                        "type": "error",
                        "error": "AI service is temporarily at capacity. Please try again in a few minutes.",
                        "category": "all_providers_failed",
                        "suggested_action": "add_key",
                    })}
                finally:
                    await release_llm_slot()

            return EventSourceResponse(event_generator())

        result = await asyncio.wait_for(
            chat_service.chat(
                user_id=user.sub,
                message=request.message,
                conversation_id=conv_id,
                workspace_id=request.workspace_id,
                repo_ids=request.repo_ids,
                user_name=user.name,
                model=request.model,
                auth_token=auth_token,
                mode=request.mode,
            ),
            timeout=LLM_CHAIN_TIMEOUT,
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
    except TimeoutError:
        raise HTTPException(
            status_code=504,
            detail={
                "error": "llm_timeout",
                "message": "The AI model took too long to respond. Please try a simpler question.",
                "retry_after": 10,
            },
        ) from None
    except ClassifiedError as e:
        status_map = {
            ErrorCategory.BILLING_EXHAUSTED: 402,
            ErrorCategory.RATE_LIMITED: 429,
            ErrorCategory.AUTH_FAILED: 401,
            ErrorCategory.PROVIDER_UNAVAILABLE: 503,
            ErrorCategory.CONTEXT_OVERFLOW: 413,
            ErrorCategory.TIMEOUT: 504,
        }
        status = status_map.get(e.category, 500)
        headers = {}
        if e.retry_after:
            headers["Retry-After"] = str(int(e.retry_after))
        raise HTTPException(
            status_code=status,
            detail={
                "error": e.category.value,
                "message": e.user_message,
                "suggested_action": e.suggested_action.value,
            },
            headers=headers,
        ) from e
    except AllProvidersFailedError:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "all_providers_failed",
                "message": "AI credits are exhausted for today. Add your own API key in Settings to continue, or try again tomorrow.",
                "suggested_action": "add_key",
            },
        ) from None
    finally:
        await release_llm_slot()


@router.post("/completions")
async def completions(request: dict, user: CurrentUser, req: Request, _: RateLimit = None):
    conv_id = str(uuid.uuid4())
    auth_header = req.headers.get("Authorization", "")
    auth_token = auth_header[7:] if auth_header.startswith("Bearer ") else None
    await acquire_llm_slot()
    try:
        result = await asyncio.wait_for(
            chat_service.chat(
                user_id=user.sub,
                message=request.get("messages", [{}])[-1].get("content", ""),
                workspace_id=request.get("workspace_id", ""),
                user_name=user.name,
                model=request.get("model"),
                auth_token=auth_token,
            ),
            timeout=LLM_CHAIN_TIMEOUT,
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
    except TimeoutError:
        raise HTTPException(
            status_code=504,
            detail={
                "error": "llm_timeout",
                "message": "The AI model took too long to respond.",
                "retry_after": 10,
            },
        ) from None
    except ClassifiedError as e:
        status_map = {
            ErrorCategory.BILLING_EXHAUSTED: 402,
            ErrorCategory.RATE_LIMITED: 429,
            ErrorCategory.AUTH_FAILED: 401,
            ErrorCategory.PROVIDER_UNAVAILABLE: 503,
        }
        status = status_map.get(e.category, 500)
        raise HTTPException(
            status_code=status,
            detail={
                "error": e.category.value,
                "message": e.user_message,
                "suggested_action": e.suggested_action.value,
            },
        ) from e
    except AllProvidersFailedError:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "all_providers_failed",
                "message": "AI credits are exhausted for today. Add your own API key in Settings to continue, or try again tomorrow.",
                "suggested_action": "add_key",
            },
        ) from None
    finally:
        await release_llm_slot()


@router.get("/models")
async def list_models(user: CurrentUser):
    models = ModelRegistry.get_selector_models()
    # Derive default from DB: first kraivor provider model, else first model, else hardcoded
    default_id = KRAIVOR_MODEL
    for m in models:
        if m.get("provider") == "kraivor":
            default_id = m["id"]
            break
    if not models:
        default_id = KRAIVOR_MODEL
    return {"models": models, "default": default_id}


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


# ── Daily usage endpoint ──────────────────────────────────────

@router.get("/usage/daily")
async def daily_usage(user: CurrentUser):
    """Return the user's token usage for today."""
    summary = await get_daily_usage_summary(user.sub)
    return summary
