"""Database-backed model registry with in-memory cache.

Replaces the hardcoded TASK_ROUTES, FREE_MODELS, and provider mappings
in router.py and failover_engine.py with database-driven configuration
that can be updated via the admin panel without code deploys.

Cache strategy:
- Module-level dicts populated by async reload()
- Sync getters read from dicts (fast, no DB hit)
- On admin mutations, call await reload() to refresh
- On startup, call await reload() to populate cache
"""

import logging

from sqlalchemy import select

from app.infrastructure.db.database import async_session_factory
from app.infrastructure.db.models.platform_model import PlatformModel
from app.infrastructure.db.models.platform_provider import PlatformProvider
from app.infrastructure.db.models.platform_task_route import PlatformTaskRoute

logger = logging.getLogger(__name__)

# ── In-memory cache (populated by reload()) ───────────────────────────

_routes: dict[str, dict] = {}
_models: list[dict] = []
_model_providers: dict[str, str] = {}  # model_id → provider_name
_frontend_providers: dict[str, str] = {}  # frontend_id → provider_name
_providers: dict[str, dict] = {}  # provider_name → config dict

# ── Default routes (used when DB has no route for a task) ─────────────

_DEFAULT_ROUTES: dict[str, dict] = {
    "intent_classify": {
        "model": "qwen/qwen3.6-27b",
        "fallback": "llama-3.3-70b-versatile",
        "max_tokens": 256,
    },
    "simple_qa": {
        "model": "qwen/qwen3.6-27b",
        "fallback": "llama-3.3-70b-versatile",
        "max_tokens": 4096,
    },
    "code_generation": {
        "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "fallback": "llama-3.3-70b-versatile",
        "max_tokens": 16384,
    },
    "code_review": {
        "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "fallback": "llama-3.3-70b-versatile",
        "max_tokens": 4096,
    },
    "security_analysis": {
        "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "fallback": "llama-3.3-70b-versatile",
        "max_tokens": 4096,
    },
    "architecture_review": {
        "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "fallback": "llama-3.3-70b-versatile",
        "max_tokens": 8192,
    },
    "performance_analysis": {
        "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "fallback": "llama-3.3-70b-versatile",
        "max_tokens": 4096,
    },
    "tool_calling": {
        "model": "llama-3.3-70b-versatile",
        "fallback": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "max_tokens": 4096,
    },
    "embeddings": {
        "model": "openai/gpt-oss-120b:free",
        "fallback": None,
        "max_tokens": 8192,
    },
}


class ModelRegistry:
    """Database-backed model registry. Call reload() on startup and after admin mutations."""

    @classmethod
    async def reload(cls) -> None:
        """Reload all cached data from the database."""
        global _routes, _models, _model_providers, _frontend_providers, _providers

        async with async_session_factory() as session:
            # ── Routes ──
            result = await session.execute(
                select(PlatformTaskRoute).where(
                    PlatformTaskRoute.is_active.is_(True),
                    PlatformTaskRoute.deleted_at.is_(None),
                )
            )
            db_routes = result.scalars().all()
            _routes = {
                r.task_name: {
                    "model": r.primary_model_id,
                    "fallback": r.fallback_model_id,
                    "max_tokens": r.max_tokens,
                    "timeout": r.timeout_seconds,
                }
                for r in db_routes
            }

            # ── Models ──
            result = await session.execute(
                select(PlatformModel).where(
                    PlatformModel.status == "active",
                    PlatformModel.deleted_at.is_(None),
                )
            )
            db_models = result.scalars().all()
            _models = [
                {
                    "frontend_id": m.frontend_id,
                    "model_id": m.model_id,
                    "display_name": m.display_name,
                    "provider_name": m.provider_name,
                    "tier": m.tier,
                    "context_window": m.context_window,
                    "max_output_tokens": m.max_output_tokens,
                    "supports_tools": m.supports_tools,
                    "supports_vision": m.supports_vision,
                    "supports_reasoning": m.supports_reasoning,
                    "is_trial": m.is_trial,
                    "latency_display": m.latency_display,
                    "icon_key": m.icon_key,
                }
                for m in db_models
            ]
            _model_providers = {m.model_id: m.provider_name for m in db_models}
            _frontend_providers = {m.frontend_id: m.provider_name for m in db_models}

            # ── Providers ──
            result = await session.execute(
                select(PlatformProvider).where(
                    PlatformProvider.is_active.is_(True),
                    PlatformProvider.deleted_at.is_(None),
                )
            )
            db_providers = result.scalars().all()
            _providers = {
                p.provider_name: {
                    "provider_name": p.provider_name,
                    "display_name": p.display_name,
                    "api_key_encrypted": p.api_key_encrypted,
                    "base_url": p.base_url,
                    "rate_limit_rpm": p.rate_limit_rpm,
                    "rate_limit_tpm": p.rate_limit_tpm,
                }
                for p in db_providers
            }

        logger.info(
            "ModelRegistry reloaded: %d routes, %d models, %d providers",
            len(_routes), len(_models), len(_providers),
        )

    # ── Sync getters (read from in-memory cache) ──────────────────────

    @classmethod
    def get_task_route(cls, task_name: str) -> dict:
        """Get route config for a task. Falls back to defaults if not in DB."""
        return _routes.get(task_name, _DEFAULT_ROUTES.get(task_name, _DEFAULT_ROUTES["simple_qa"]))

    @classmethod
    def get_active_models(cls, provider: str | None = None) -> list[dict]:
        """Get all active models, optionally filtered by provider."""
        if provider:
            return [m for m in _models if m["provider_name"] == provider]
        return list(_models)

    @classmethod
    def get_model_provider(cls, model_id: str) -> str | None:
        """Look up which provider a model belongs to. Returns None if not in cache."""
        return _model_providers.get(model_id)

    @classmethod
    def get_provider_config(cls, provider_name: str) -> dict | None:
        """Get provider config (API key, base URL) from cache."""
        return _providers.get(provider_name)

    @classmethod
    def get_failover_models(cls, exclude_models: set[str] | None = None) -> list[str]:
        """Get active model IDs for cross-provider failover."""
        exclude = exclude_models or set()
        return [m["model_id"] for m in _models if m["model_id"] not in exclude]

    @classmethod
    def get_selector_models(cls) -> list[dict]:
        """Get all active models formatted for the frontend model selector dropdown."""
        _PROVIDER_TO_TIER: dict[str, str] = {
            "kraivor": "kraivor",
            "groq": "groq",
            "openrouter": "free",
        }

        def _context_display(window: int) -> str:
            if window >= 1_000_000:
                return "1M"
            return f"{window // 1024}K"

        result = []
        for m in _models:
            tier = _PROVIDER_TO_TIER.get(m["provider_name"], "byok")
            result.append({
                "id": m["frontend_id"],
                "name": m["display_name"],
                "tier": tier,
                "provider": m["provider_name"],
                "backendModel": m["model_id"],
                "latency": m["latency_display"],
                "context": _context_display(m["context_window"]),
                "iconKey": m["icon_key"],
            })
        return result
