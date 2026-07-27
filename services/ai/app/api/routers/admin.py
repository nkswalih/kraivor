from datetime import UTC, datetime
from typing import Literal
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.api.dependencies.admin import require_superadmin
from app.api.dependencies.auth import JWTPayload
from app.infrastructure.db.database import async_session_factory
from app.infrastructure.db.models.platform_model import PlatformModel
from app.infrastructure.db.models.platform_provider import PlatformProvider
from app.infrastructure.db.models.platform_task_route import PlatformTaskRoute
from app.application.admin.model_registry import ModelRegistry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/admin", tags=["admin"])


# ── Schemas ──────────────────────────────────────────────────────────────


class ProviderCreate(BaseModel):
    provider_name: str
    display_name: str
    api_key: str | None = None
    base_url: str | None = None
    is_active: bool = True
    rate_limit_rpm: int | None = None
    rate_limit_tpm: int | None = None


class ProviderUpdate(BaseModel):
    display_name: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    is_active: bool | None = None
    rate_limit_rpm: int | None = None
    rate_limit_tpm: int | None = None


class ModelCreate(BaseModel):
    frontend_id: str
    model_id: str
    display_name: str
    provider_name: str
    status: Literal["active", "inactive", "deprecated"] = "active"
    tier: Literal["fast", "standard", "balanced", "extended", "free"] = "standard"
    context_window: int = 131072
    max_output_tokens: int = 16384
    input_price_per_mtok: float = 0.0
    output_price_per_mtok: float = 0.0
    is_trial: bool = False
    trial_expires_at: datetime | None = None
    supports_tools: bool = False
    supports_vision: bool = False
    supports_reasoning: bool = False
    icon_key: str | None = None
    notes: str | None = None


class ModelUpdate(BaseModel):
    frontend_id: str | None = None
    display_name: str | None = None
    provider_name: str | None = None
    status: Literal["active", "inactive", "deprecated"] | None = None
    tier: Literal["fast", "standard", "balanced", "extended", "free"] | None = None
    context_window: int | None = None
    max_output_tokens: int | None = None
    input_price_per_mtok: float | None = None
    output_price_per_mtok: float | None = None
    is_trial: bool | None = None
    trial_expires_at: datetime | None = None
    supports_tools: bool | None = None
    supports_vision: bool | None = None
    supports_reasoning: bool | None = None
    icon_key: str | None = None
    notes: str | None = None


class RouteCreate(BaseModel):
    task_name: str
    primary_model_id: str
    fallback_model_id: str | None = None
    max_tokens: int = 4096
    timeout_seconds: int | None = None
    is_active: bool = True


class RouteUpdate(BaseModel):
    primary_model_id: str | None = None
    fallback_model_id: str | None = None
    max_tokens: int | None = None
    timeout_seconds: int | None = None
    is_active: bool | None = None


# ── Helpers ──────────────────────────────────────────────────────────────


def _serialize_provider(p: PlatformProvider) -> dict:
    return {
        "id": str(p.id),
        "provider_name": p.provider_name,
        "display_name": p.display_name,
        "has_api_key": p.api_key_encrypted is not None,
        "base_url": p.base_url,
        "is_active": p.is_active,
        "rate_limit_rpm": p.rate_limit_rpm,
        "rate_limit_tpm": p.rate_limit_tpm,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


_MODEL_PREFIX_TO_ICON: dict[str, str] = {
    "cohere": "cohere",
    "nvidia": "nvidia",
    "poolside": "poolside",
    "tencent": "tencent",
    "google": "gemini",
    "deepseek": "deepseek",
    "meta": "meta",
    "mistral": "mistral",
    "anthropic": "claude",
    "openai": "openai",
    "xai": "grok",
}


def _resolve_icon_key(icon_key: str | None, model_id: str) -> str | None:
    if icon_key:
        return icon_key
    prefix = model_id.split("/")[0] if "/" in model_id else ""
    return _MODEL_PREFIX_TO_ICON.get(prefix)


def _serialize_model(m: PlatformModel) -> dict:
    return {
        "id": str(m.id),
        "frontend_id": m.frontend_id,
        "model_id": m.model_id,
        "display_name": m.display_name,
        "provider_name": m.provider_name,
        "status": m.status,
        "tier": m.tier,
        "context_window": m.context_window,
        "max_output_tokens": m.max_output_tokens,
        "input_price_per_mtok": float(m.input_price_per_mtok),
        "output_price_per_mtok": float(m.output_price_per_mtok),
        "is_trial": m.is_trial,
        "trial_expires_at": m.trial_expires_at.isoformat() if m.trial_expires_at else None,
        "supports_tools": m.supports_tools,
        "supports_vision": m.supports_vision,
        "supports_reasoning": m.supports_reasoning,
        "latency_display": m.latency_display,
        "icon_key": _resolve_icon_key(m.icon_key, m.model_id),
        "notes": m.notes,
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "updated_at": m.updated_at.isoformat() if m.updated_at else None,
    }


def _serialize_route(r: PlatformTaskRoute) -> dict:
    return {
        "id": str(r.id),
        "task_name": r.task_name,
        "primary_model_id": r.primary_model_id,
        "fallback_model_id": r.fallback_model_id,
        "max_tokens": r.max_tokens,
        "timeout_seconds": r.timeout_seconds,
        "is_active": r.is_active,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }


# ── Auth check ───────────────────────────────────────────────────────────


@router.get("/me")
async def admin_me(current_user: JWTPayload = Depends(require_superadmin)):
    return {"user_id": current_user.sub, "email": current_user.email, "is_superadmin": True}


# ── Providers ────────────────────────────────────────────────────────────


@router.get("/providers")
async def list_providers(_: JWTPayload = Depends(require_superadmin)):
    async with async_session_factory() as session:
        result = await session.execute(
            select(PlatformProvider).where(PlatformProvider.deleted_at.is_(None))
        )
        providers = result.scalars().all()
    return {"providers": [_serialize_provider(p) for p in providers]}


@router.post("/providers")
async def create_provider(
    body: ProviderCreate,
    _: JWTPayload = Depends(require_superadmin),
):
    async with async_session_factory() as session:
        existing = await session.execute(
            select(PlatformProvider).where(PlatformProvider.provider_name == body.provider_name)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Provider already exists")

        # Encrypt API key if provided
        encrypted_key = None
        if body.api_key:
            from app.application.provisioning.key_resolver import _default_encrypter
            encrypted_key = _default_encrypter.encrypt(body.api_key.encode()).decode()

        provider = PlatformProvider(
            provider_name=body.provider_name,
            display_name=body.display_name,
            api_key_encrypted=encrypted_key,
            base_url=body.base_url,
            is_active=body.is_active,
            rate_limit_rpm=body.rate_limit_rpm,
            rate_limit_tpm=body.rate_limit_tpm,
        )
        session.add(provider)
        await session.commit()
        await session.refresh(provider)
        await ModelRegistry.reload()
        return _serialize_provider(provider)


@router.patch("/providers/{provider_id}")
async def update_provider(
    provider_id: str,
    body: ProviderUpdate,
    _: JWTPayload = Depends(require_superadmin),
):
    async with async_session_factory() as session:
        result = await session.execute(
            select(PlatformProvider).where(PlatformProvider.id == uuid.UUID(provider_id))
        )
        provider = result.scalar_one_or_none()
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")

        if body.display_name is not None:
            provider.display_name = body.display_name
        if body.api_key is not None:
            from app.application.provisioning.key_resolver import _default_encrypter
            provider.api_key_encrypted = (
                _default_encrypter.encrypt(body.api_key.encode()).decode()
                if body.api_key
                else None
            )
        if body.base_url is not None:
            provider.base_url = body.base_url
        if body.is_active is not None:
            provider.is_active = body.is_active
        if body.rate_limit_rpm is not None:
            provider.rate_limit_rpm = body.rate_limit_rpm
        if body.rate_limit_tpm is not None:
            provider.rate_limit_tpm = body.rate_limit_tpm

        await session.commit()
        await session.refresh(provider)
        await ModelRegistry.reload()
        return _serialize_provider(provider)


@router.delete("/providers/{provider_id}")
async def delete_provider(
    provider_id: str,
    _: JWTPayload = Depends(require_superadmin),
):
    async with async_session_factory() as session:
        result = await session.execute(
            select(PlatformProvider).where(PlatformProvider.id == uuid.UUID(provider_id))
        )
        provider = result.scalar_one_or_none()
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        provider.deleted_at = datetime.now(UTC)
        await session.commit()
        await ModelRegistry.reload()
        return {"deleted": True}


# ── Models ───────────────────────────────────────────────────────────────


@router.get("/models")
async def list_models(_: JWTPayload = Depends(require_superadmin)):
    async with async_session_factory() as session:
        result = await session.execute(
            select(PlatformModel).where(PlatformModel.deleted_at.is_(None))
        )
        models = result.scalars().all()
    return {"models": [_serialize_model(m) for m in models]}


@router.post("/models")
async def create_model(
    body: ModelCreate,
    _: JWTPayload = Depends(require_superadmin),
):
    async with async_session_factory() as session:
        existing = await session.execute(
            select(PlatformModel).where(PlatformModel.model_id == body.model_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Model already exists")

        provider = await session.execute(
            select(PlatformProvider).where(
                PlatformProvider.provider_name == body.provider_name,
                PlatformProvider.deleted_at.is_(None),
            )
        )
        if not provider.scalar_one_or_none():
            raise HTTPException(
                status_code=422,
                detail=f"Provider '{body.provider_name}' does not exist",
            )

        model = PlatformModel(**body.model_dump())
        session.add(model)
        await session.commit()
        await session.refresh(model)
        await ModelRegistry.reload()
        return _serialize_model(model)


@router.patch("/models/{model_id}")
async def update_model(
    model_id: str,
    body: ModelUpdate,
    _: JWTPayload = Depends(require_superadmin),
):
    async with async_session_factory() as session:
        result = await session.execute(
            select(PlatformModel).where(PlatformModel.id == uuid.UUID(model_id))
        )
        model = result.scalar_one_or_none()
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")

        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(model, field, value)

        await session.commit()
        await session.refresh(model)
        await ModelRegistry.reload()
        return _serialize_model(model)


@router.delete("/models/{model_id}")
async def delete_model(
    model_id: str,
    _: JWTPayload = Depends(require_superadmin),
):
    async with async_session_factory() as session:
        result = await session.execute(
            select(PlatformModel).where(PlatformModel.id == uuid.UUID(model_id))
        )
        model = result.scalar_one_or_none()
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        model.deleted_at = datetime.now(UTC)
        await session.commit()
        await ModelRegistry.reload()
        return {"deleted": True}


# ── Task Routes ──────────────────────────────────────────────────────────


@router.get("/routes")
async def list_routes(_: JWTPayload = Depends(require_superadmin)):
    async with async_session_factory() as session:
        result = await session.execute(
            select(PlatformTaskRoute).where(PlatformTaskRoute.deleted_at.is_(None))
        )
        routes = result.scalars().all()
    return {"routes": [_serialize_route(r) for r in routes]}


@router.post("/routes")
async def create_route(
    body: RouteCreate,
    _: JWTPayload = Depends(require_superadmin),
):
    async with async_session_factory() as session:
        existing = await session.execute(
            select(PlatformTaskRoute).where(PlatformTaskRoute.task_name == body.task_name)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Route already exists")

        primary = await session.execute(
            select(PlatformModel).where(
                PlatformModel.model_id == body.primary_model_id,
                PlatformModel.deleted_at.is_(None),
            )
        )
        if not primary.scalar_one_or_none():
            raise HTTPException(
                status_code=422,
                detail=f"Primary model '{body.primary_model_id}' does not exist",
            )

        if body.fallback_model_id:
            fallback = await session.execute(
                select(PlatformModel).where(
                    PlatformModel.model_id == body.fallback_model_id,
                    PlatformModel.deleted_at.is_(None),
                )
            )
            if not fallback.scalar_one_or_none():
                raise HTTPException(
                    status_code=422,
                    detail=f"Fallback model '{body.fallback_model_id}' does not exist",
                )

        route = PlatformTaskRoute(**body.model_dump())
        session.add(route)
        await session.commit()
        await session.refresh(route)
        await ModelRegistry.reload()
        return _serialize_route(route)


@router.patch("/routes/{route_id}")
async def update_route(
    route_id: str,
    body: RouteUpdate,
    _: JWTPayload = Depends(require_superadmin),
):
    async with async_session_factory() as session:
        result = await session.execute(
            select(PlatformTaskRoute).where(PlatformTaskRoute.id == uuid.UUID(route_id))
        )
        route = result.scalar_one_or_none()
        if not route:
            raise HTTPException(status_code=404, detail="Route not found")

        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(route, field, value)

        await session.commit()
        await session.refresh(route)
        await ModelRegistry.reload()
        return _serialize_route(route)


@router.delete("/routes/{route_id}")
async def delete_route(
    route_id: str,
    _: JWTPayload = Depends(require_superadmin),
):
    async with async_session_factory() as session:
        result = await session.execute(
            select(PlatformTaskRoute).where(PlatformTaskRoute.id == uuid.UUID(route_id))
        )
        route = result.scalar_one_or_none()
        if not route:
            raise HTTPException(status_code=404, detail="Route not found")
        route.deleted_at = datetime.now(UTC)
        await session.commit()
        await ModelRegistry.reload()
        return {"deleted": True}


# ── Cache ────────────────────────────────────────────────────────────────


@router.post("/cache/invalidate")
async def invalidate_cache(_: JWTPayload = Depends(require_superadmin)):
    await ModelRegistry.reload()
    return {"invalidated": True}
