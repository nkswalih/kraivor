"""add_model_icon_key

Revision ID: 011
Revises: 010
Create Date: 2026-07-26
"""

from alembic import op
import sqlalchemy as sa

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None

# ── icon_key values per provider (default icon assignment) ──────────────
_PROVIDER_ICONS: dict[str, str] = {
    "kraivor": "krait",
    "groq": "groq",
    "anthropic": "claude",
    "openai": "openai",
    "google": "gemini",
    "xai": "grok",
    "deepseek": "deepseek",
    "meta": "meta",
    "mistral": "mistral",
    "nvidia": "nvidia",
    "cohere": "cohere",
    "tencent": "tencent",
    "poolside": "poolside",
}


def upgrade() -> None:
    op.add_column(
        "platform_models",
        sa.Column("icon_key", sa.String(50), nullable=True),
        schema="ai",
    )

    for provider, icon in _PROVIDER_ICONS.items():
        op.execute(
            sa.text(
                "UPDATE ai.platform_models "
                f"SET icon_key = '{icon}' "
                f"WHERE provider_name = '{provider}' AND icon_key IS NULL"
            )
        )


def downgrade() -> None:
    op.drop_column("platform_models", "icon_key", schema="ai")
