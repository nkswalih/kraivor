"""seed_platform_model_config

Revision ID: 009
Revises: 008
Create Date: 2026-07-26
"""

import uuid as _uuid_mod

from alembic import op
import sqlalchemy as sa

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def _new_id() -> str:
    return str(_uuid_mod.uuid4())


def upgrade() -> None:
    # ── Providers ──────────────────────────────────────────────────────────
    providers = [
        {
            "provider_name": "groq",
            "display_name": "Groq",
            "base_url": "https://api.groq.com/openai/v1",
            "is_active": True,
            "rate_limit_rpm": 30,
            "rate_limit_tpm": 131072,
        },
        {
            "provider_name": "openrouter",
            "display_name": "OpenRouter",
            "base_url": "https://openrouter.ai/api/v1",
            "is_active": True,
            "rate_limit_rpm": 200,
            "rate_limit_tpm": 200000,
        },
        {
            "provider_name": "anthropic",
            "display_name": "Anthropic",
            "base_url": "https://api.anthropic.com/v1",
            "is_active": True,
            "rate_limit_rpm": 50,
            "rate_limit_tpm": 40000,
        },
        {
            "provider_name": "openai",
            "display_name": "OpenAI",
            "base_url": "https://api.openai.com/v1",
            "is_active": True,
            "rate_limit_rpm": 500,
            "rate_limit_tpm": 200000,
        },
        {
            "provider_name": "google",
            "display_name": "Google AI",
            "base_url": "https://generativelanguage.googleapis.com/v1beta",
            "is_active": True,
            "rate_limit_rpm": 60,
            "rate_limit_tpm": 40000,
        },
        {
            "provider_name": "deepseek",
            "display_name": "DeepSeek",
            "base_url": "https://api.deepseek.com/v1",
            "is_active": True,
            "rate_limit_rpm": 60,
            "rate_limit_tpm": 40000,
        },
        {
            "provider_name": "xai",
            "display_name": "xAI",
            "base_url": "https://api.x.ai/v1",
            "is_active": True,
            "rate_limit_rpm": 60,
            "rate_limit_tpm": 40000,
        },
    ]

    for p in providers:
        op.execute(
            sa.text(
                "INSERT INTO ai.platform_providers "
                "(id, provider_name, display_name, base_url, is_active, rate_limit_rpm, rate_limit_tpm, created_at, updated_at) "
                "VALUES "
                f"('{_new_id()}', '{p['provider_name']}', '{p['display_name']}', '{p['base_url']}', "
                f"{p['is_active']}, {p['rate_limit_rpm']}, {p['rate_limit_tpm']}, NOW(), NOW())"
            )
        )

    # ── Models ─────────────────────────────────────────────────────────────
    models = [
        # Groq (native API — fast inference)
        {
            "model_id": "qwen/qwen3.6-27b",
            "display_name": "Qwen 3.6 27B",
            "provider_name": "groq",
            "status": "active",
            "tier": "fast",
            "context_window": 131072,
            "max_output_tokens": 32768,
            "supports_vision": False,
            "supports_tools": True,
            "supports_reasoning": True,
        },
        {
            "model_id": "llama-3.3-70b-versatile",
            "display_name": "Llama 3.3 70B Versatile",
            "provider_name": "groq",
            "status": "active",
            "tier": "standard",
            "context_window": 131072,
            "max_output_tokens": 32768,
            "supports_vision": False,
            "supports_tools": True,
            "supports_reasoning": True,
        },
        {
            "model_id": "llama-3.1-8b-instant",
            "display_name": "Llama 3.1 8B Instant",
            "provider_name": "groq",
            "status": "active",
            "tier": "fast",
            "context_window": 131072,
            "max_output_tokens": 8192,
            "supports_vision": False,
            "supports_tools": True,
            "supports_reasoning": False,
        },
        {
            "model_id": "openai/gpt-oss-120b",
            "display_name": "OpenAI GPT-OSS 120B",
            "provider_name": "groq",
            "status": "active",
            "tier": "standard",
            "context_window": 131072,
            "max_output_tokens": 32768,
            "supports_vision": False,
            "supports_tools": True,
            "supports_reasoning": True,
        },
        {
            "model_id": "openai/gpt-oss-20b",
            "display_name": "OpenAI GPT-OSS 20B",
            "provider_name": "groq",
            "status": "active",
            "tier": "fast",
            "context_window": 131072,
            "max_output_tokens": 16384,
            "supports_vision": False,
            "supports_tools": True,
            "supports_reasoning": False,
        },
        # Free (OpenRouter)
        {
            "model_id": "cohere/north-mini-code:free",
            "display_name": "Cohere North Mini Code",
            "provider_name": "openrouter",
            "status": "active",
            "tier": "fast",
            "context_window": 128000,
            "max_output_tokens": 8192,
            "supports_vision": False,
            "supports_tools": False,
            "supports_reasoning": False,
        },
        {
            "model_id": "nvidia/nemotron-3-ultra-550b-a55b:free",
            "display_name": "NVIDIA Nemotron Ultra 550B",
            "provider_name": "openrouter",
            "status": "active",
            "tier": "standard",
            "context_window": 131072,
            "max_output_tokens": 32768,
            "supports_vision": False,
            "supports_tools": True,
            "supports_reasoning": True,
        },
        {
            "model_id": "tencent/hy3:free",
            "display_name": "Tencent HY3",
            "provider_name": "openrouter",
            "status": "active",
            "tier": "standard",
            "context_window": 131072,
            "max_output_tokens": 32768,
            "supports_vision": False,
            "supports_tools": True,
            "supports_reasoning": True,
        },
        {
            "model_id": "poolside/laguna-xs-2.1:free",
            "display_name": "Poolside Laguna XS",
            "provider_name": "openrouter",
            "status": "active",
            "tier": "fast",
            "context_window": 128000,
            "max_output_tokens": 8192,
            "supports_vision": False,
            "supports_tools": False,
            "supports_reasoning": False,
        },
        {
            "model_id": "poolside/laguna-m.1:free",
            "display_name": "Poolside Laguna M",
            "provider_name": "openrouter",
            "status": "active",
            "tier": "standard",
            "context_window": 131072,
            "max_output_tokens": 32768,
            "supports_vision": False,
            "supports_tools": True,
            "supports_reasoning": True,
        },
        {
            "model_id": "nvidia/nemotron-3-super-120b-a12b:free",
            "display_name": "NVIDIA Nemotron Super 120B",
            "provider_name": "openrouter",
            "status": "active",
            "tier": "standard",
            "context_window": 131072,
            "max_output_tokens": 32768,
            "supports_vision": False,
            "supports_tools": True,
            "supports_reasoning": True,
        },
        {
            "model_id": "google/gemma-4-31b-it:free",
            "display_name": "Google Gemma 4 31B",
            "provider_name": "openrouter",
            "status": "active",
            "tier": "standard",
            "context_window": 131072,
            "max_output_tokens": 32768,
            "supports_vision": False,
            "supports_tools": True,
            "supports_reasoning": False,
        },
        {
            "model_id": "nvidia/nemotron-3-nano-30b-a3b:free",
            "display_name": "NVIDIA Nemotron Nano 30B",
            "provider_name": "openrouter",
            "status": "active",
            "tier": "fast",
            "context_window": 131072,
            "max_output_tokens": 16384,
            "supports_vision": False,
            "supports_tools": True,
            "supports_reasoning": False,
        },
        # BYOK — Anthropic
        {
            "model_id": "anthropic/claude-fable-5",
            "display_name": "Claude Fable 5",
            "provider_name": "anthropic",
            "status": "active",
            "tier": "standard",
            "context_window": 200000,
            "max_output_tokens": 32768,
            "supports_vision": True,
            "supports_tools": True,
            "supports_reasoning": True,
        },
        {
            "model_id": "anthropic/claude-opus-4-8",
            "display_name": "Claude Opus 4.8",
            "provider_name": "anthropic",
            "status": "active",
            "tier": "extended",
            "context_window": 200000,
            "max_output_tokens": 32768,
            "supports_vision": True,
            "supports_tools": True,
            "supports_reasoning": True,
        },
        {
            "model_id": "anthropic/claude-opus-4-7",
            "display_name": "Claude Opus 4.7",
            "provider_name": "anthropic",
            "status": "active",
            "tier": "extended",
            "context_window": 200000,
            "max_output_tokens": 32768,
            "supports_vision": True,
            "supports_tools": True,
            "supports_reasoning": True,
        },
        {
            "model_id": "anthropic/claude-sonnet-5",
            "display_name": "Claude Sonnet 5",
            "provider_name": "anthropic",
            "status": "active",
            "tier": "standard",
            "context_window": 200000,
            "max_output_tokens": 16384,
            "supports_vision": True,
            "supports_tools": True,
            "supports_reasoning": True,
        },
        {
            "model_id": "anthropic/claude-sonnet-4-6",
            "display_name": "Claude Sonnet 4.6",
            "provider_name": "anthropic",
            "status": "active",
            "tier": "standard",
            "context_window": 200000,
            "max_output_tokens": 16384,
            "supports_vision": True,
            "supports_tools": True,
            "supports_reasoning": True,
        },
        # BYOK — OpenAI
        {
            "model_id": "openai/gpt-5.6-sol",
            "display_name": "GPT-5.6 Sol",
            "provider_name": "openai",
            "status": "active",
            "tier": "extended",
            "context_window": 256000,
            "max_output_tokens": 32768,
            "supports_vision": True,
            "supports_tools": True,
            "supports_reasoning": True,
        },
        {
            "model_id": "openai/gpt-5.6-terra",
            "display_name": "GPT-5.6 Terra",
            "provider_name": "openai",
            "status": "active",
            "tier": "extended",
            "context_window": 256000,
            "max_output_tokens": 32768,
            "supports_vision": True,
            "supports_tools": True,
            "supports_reasoning": True,
        },
        {
            "model_id": "openai/gpt-5.5",
            "display_name": "GPT-5.5",
            "provider_name": "openai",
            "status": "active",
            "tier": "standard",
            "context_window": 256000,
            "max_output_tokens": 16384,
            "supports_vision": True,
            "supports_tools": True,
            "supports_reasoning": True,
        },
        {
            "model_id": "openai/gpt-5.4",
            "display_name": "GPT-5.4",
            "provider_name": "openai",
            "status": "active",
            "tier": "standard",
            "context_window": 256000,
            "max_output_tokens": 16384,
            "supports_vision": True,
            "supports_tools": True,
            "supports_reasoning": False,
        },
        # BYOK — Google
        {
            "model_id": "google/gemini-3.5-flash",
            "display_name": "Gemini 3.5 Flash",
            "provider_name": "google",
            "status": "active",
            "tier": "fast",
            "context_window": 1000000,
            "max_output_tokens": 8192,
            "supports_vision": True,
            "supports_tools": True,
            "supports_reasoning": False,
        },
        {
            "model_id": "google/gemini-3.1-pro",
            "display_name": "Gemini 3.1 Pro",
            "provider_name": "google",
            "status": "active",
            "tier": "standard",
            "context_window": 1000000,
            "max_output_tokens": 32768,
            "supports_vision": True,
            "supports_tools": True,
            "supports_reasoning": True,
        },
        # BYOK — DeepSeek
        {
            "model_id": "deepseek/deepseek-v4-pro",
            "display_name": "DeepSeek V4 Pro",
            "provider_name": "deepseek",
            "status": "active",
            "tier": "standard",
            "context_window": 131072,
            "max_output_tokens": 32768,
            "supports_vision": False,
            "supports_tools": True,
            "supports_reasoning": True,
        },
        # BYOK — xAI
        {
            "model_id": "xai/grok-4.3",
            "display_name": "Grok 4.3",
            "provider_name": "xai",
            "status": "active",
            "tier": "standard",
            "context_window": 131072,
            "max_output_tokens": 32768,
            "supports_vision": True,
            "supports_tools": True,
            "supports_reasoning": True,
        },
    ]

    for m in models:
        op.execute(
            sa.text(
                "INSERT INTO ai.platform_models "
                "(id, model_id, display_name, provider_name, status, tier, context_window, max_output_tokens, "
                "supports_vision, supports_tools, supports_reasoning, created_at, updated_at) "
                "VALUES "
                f"('{_new_id()}', '{m['model_id']}', '{m['display_name']}', '{m['provider_name']}', "
                f"'{m['status']}', '{m['tier']}', {m['context_window']}, {m['max_output_tokens']}, "
                f"{m['supports_vision']}, {m['supports_tools']}, {m['supports_reasoning']}, NOW(), NOW())"
            )
        )

    # ── Task Routes ────────────────────────────────────────────────────────
    routes = [
        {
            "task_name": "greeting",
            "primary_model_id": "qwen/qwen3.6-27b",
            "fallback_model_id": "llama-3.3-70b-versatile",
            "max_tokens": 300,
            "timeout_seconds": 15,
        },
        {
            "task_name": "simple_qa",
            "primary_model_id": "qwen/qwen3.6-27b",
            "fallback_model_id": "llama-3.3-70b-versatile",
            "max_tokens": 1024,
            "timeout_seconds": 30,
        },
        {
            "task_name": "complex_analysis",
            "primary_model_id": "llama-3.3-70b-versatile",
            "fallback_model_id": "qwen/qwen3.6-27b",
            "max_tokens": 4096,
            "timeout_seconds": 60,
        },
        {
            "task_name": "code_generation",
            "primary_model_id": "qwen/qwen3.6-27b",
            "fallback_model_id": "llama-3.3-70b-versatile",
            "max_tokens": 8192,
            "timeout_seconds": 60,
        },
        {
            "task_name": "summarization",
            "primary_model_id": "qwen/qwen3.6-27b",
            "fallback_model_id": "llama-3.3-70b-versatile",
            "max_tokens": 2048,
            "timeout_seconds": 30,
        },
        {
            "task_name": "translation",
            "primary_model_id": "qwen/qwen3.6-27b",
            "fallback_model_id": "llama-3.3-70b-versatile",
            "max_tokens": 2048,
            "timeout_seconds": 30,
        },
        {
            "task_name": "creative_writing",
            "primary_model_id": "llama-3.3-70b-versatile",
            "fallback_model_id": "qwen/qwen3.6-27b",
            "max_tokens": 4096,
            "timeout_seconds": 45,
        },
        {
            "task_name": "data_extraction",
            "primary_model_id": "qwen/qwen3.6-27b",
            "fallback_model_id": "llama-3.3-70b-versatile",
            "max_tokens": 4096,
            "timeout_seconds": 30,
        },
        {
            "task_name": "tool_calling",
            "primary_model_id": "qwen/qwen3.6-27b",
            "fallback_model_id": "llama-3.3-70b-versatile",
            "max_tokens": 4096,
            "timeout_seconds": 30,
        },
        {
            "task_name": "vision_analysis",
            "primary_model_id": "qwen/qwen3.6-27b",
            "fallback_model_id": "llama-3.3-70b-versatile",
            "max_tokens": 2048,
            "timeout_seconds": 45,
        },
    ]

    for r in routes:
        fb = f"'{r['fallback_model_id']}'" if r["fallback_model_id"] else "NULL"
        timeout = str(r["timeout_seconds"]) if r["timeout_seconds"] else "NULL"
        op.execute(
            sa.text(
                "INSERT INTO ai.platform_task_routes "
                "(id, task_name, primary_model_id, fallback_model_id, max_tokens, timeout_seconds, created_at, updated_at) "
                "VALUES "
                f"('{_new_id()}', '{r['task_name']}', '{r['primary_model_id']}', {fb}, "
                f"{r['max_tokens']}, {timeout}, NOW(), NOW())"
            )
        )


def downgrade() -> None:
    op.execute("DELETE FROM ai.platform_task_routes")
    op.execute("DELETE FROM ai.platform_models")
    op.execute("DELETE FROM ai.platform_providers")
