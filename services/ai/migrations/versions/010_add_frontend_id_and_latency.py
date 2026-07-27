"""add_frontend_id_and_latency

Revision ID: 010
Revises: 009
Create Date: 2026-07-26
"""

import uuid as _uuid_mod

from alembic import op
import sqlalchemy as sa

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def _new_id() -> str:
    return str(_uuid_mod.uuid4())


# ── frontend_id → model_id mapping for existing rows ───────────────────
_FRONTEND_TO_BACKEND: dict[str, str] = {
    "groq-qwen3.6-27b": "qwen/qwen3.6-27b",
    "groq-llama-3.3-70b": "llama-3.3-70b-versatile",
    "groq-llama-3.1-8b": "llama-3.1-8b-instant",
    "groq-gpt-oss-120b": "openai/gpt-oss-120b",
    "groq-gpt-oss-20b": "openai/gpt-oss-20b",
    "cohere-north-mini-code": "cohere/north-mini-code:free",
    "nvidia-nemotron-ultra": "nvidia/nemotron-3-ultra-550b-a55b:free",
    "tencent-hy3": "tencent/hy3:free",
    "poolside-laguna-xs": "poolside/laguna-xs-2.1:free",
    "poolside-laguna-m": "poolside/laguna-m.1:free",
    "nvidia-nemotron-super": "nvidia/nemotron-3-super-120b-a12b:free",
    "google-gemma-4": "google/gemma-4-31b-it:free",
    "nvidia-nemotron-nano": "nvidia/nemotron-3-nano-30b-a3b:free",
    "claude-fable-5": "anthropic/claude-fable-5",
    "claude-opus-4-8": "anthropic/claude-opus-4-8",
    "claude-opus-4-7": "anthropic/claude-opus-4-7",
    "claude-sonnet-5": "anthropic/claude-sonnet-5",
    "claude-sonnet-4-6": "anthropic/claude-sonnet-4-6",
    "gpt-5.6-sol": "openai/gpt-5.6-sol",
    "gpt-5.6-terra": "openai/gpt-5.6-terra",
    "gpt-5.5": "openai/gpt-5.5",
    "gpt-5.4": "openai/gpt-5.4",
    "gemini-3.5-flash": "google/gemini-3.5-flash",
    "gemini-3.1-pro": "google/gemini-3.1-pro",
    "deepseek-v4-pro": "deepseek/deepseek-v4-pro",
    "grok-4.3": "xai/grok-4.3",
}

# ── latency display values per backend model ────────────────────────────
_LATENCY: dict[str, str] = {
    "qwen/qwen3.6-27b": "0.3s",
    "llama-3.3-70b-versatile": "0.4s",
    "llama-3.1-8b-instant": "0.2s",
    "openai/gpt-oss-120b": "0.5s",
    "openai/gpt-oss-20b": "0.3s",
    "cohere/north-mini-code:free": "0.6s",
    "nvidia/nemotron-3-ultra-550b-a55b:free": "2.0s",
    "tencent/hy3:free": "3.4s",
    "poolside/laguna-xs-2.1:free": "0.8s",
    "poolside/laguna-m.1:free": "1.2s",
    "nvidia/nemotron-3-super-120b-a12b:free": "2.5s",
    "google/gemma-4-31b-it:free": "1.0s",
    "nvidia/nemotron-3-nano-30b-a3b:free": "0.6s",
    "anthropic/claude-fable-5": "1.5s",
    "anthropic/claude-opus-4-8": "2.0s",
    "anthropic/claude-opus-4-7": "2.2s",
    "anthropic/claude-sonnet-5": "1.2s",
    "anthropic/claude-sonnet-4-6": "1.0s",
    "openai/gpt-5.6-sol": "1.0s",
    "openai/gpt-5.6-terra": "1.2s",
    "openai/gpt-5.5": "0.9s",
    "openai/gpt-5.4": "0.8s",
    "google/gemini-3.5-flash": "0.5s",
    "google/gemini-3.1-pro": "1.5s",
    "deepseek/deepseek-v4-pro": "1.0s",
    "xai/grok-4.3": "1.5s",
}


def upgrade() -> None:
    # ── Add columns ─────────────────────────────────────────────────────
    op.add_column(
        "platform_models",
        sa.Column("frontend_id", sa.String(200), nullable=True),
        schema="ai",
    )
    op.add_column(
        "platform_models",
        sa.Column("latency_display", sa.String(10), nullable=True),
        schema="ai",
    )

    # ── Populate frontend_id + latency_display for existing rows ────────
    for fe_id, be_id in _FRONTEND_TO_BACKEND.items():
        latency = _LATENCY.get(be_id, "0.5s")
        op.execute(
            sa.text(
                "UPDATE ai.platform_models "
                f"SET frontend_id = '{fe_id}', latency_display = '{latency}' "
                f"WHERE model_id = '{be_id}'"
            )
        )

    # ── Insert Kraivor provider ─────────────────────────────────────────
    op.execute(
        sa.text(
            "INSERT INTO ai.platform_providers "
            "(id, provider_name, display_name, base_url, is_active, created_at, updated_at) "
            f"VALUES ('{_new_id()}', 'kraivor', 'Kraivor AI', NULL, true, NOW(), NOW()) "
            "ON CONFLICT (provider_name) DO NOTHING"
        )
    )

    # ── Insert krait-2.0 model ─────────────────────────────────────────
    op.execute(
        sa.text(
            "INSERT INTO ai.platform_models "
            "(id, frontend_id, model_id, display_name, provider_name, status, tier, "
            "context_window, max_output_tokens, supports_vision, supports_tools, "
            "supports_reasoning, latency_display, created_at, updated_at) "
            f"VALUES ('{_new_id()}', 'krait-2.0', 'openrouter/auto', 'Krait 2.0', "
            "'kraivor', 'active', 'standard', 131072, 16384, false, true, false, "
            "'0.4s', NOW(), NOW()) "
            "ON CONFLICT (model_id) DO NOTHING"
        )
    )

    # ── Make frontend_id NOT NULL after backfill ────────────────────────
    op.alter_column(
        "platform_models",
        "frontend_id",
        nullable=False,
        schema="ai",
    )

    # ── Add unique constraint ───────────────────────────────────────────
    op.create_unique_constraint(
        "uq_platform_models_frontend_id",
        "platform_models",
        ["frontend_id"],
        schema="ai",
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_platform_models_frontend_id",
        "platform_models",
        schema="ai",
    )
    op.drop_column("platform_models", "frontend_id", schema="ai")
    op.drop_column("platform_models", "latency_display", schema="ai")
    op.execute(sa.text("DELETE FROM ai.platform_models WHERE model_id = 'openrouter/auto'"))
    op.execute(sa.text("DELETE FROM ai.platform_providers WHERE provider_name = 'kraivor'"))
