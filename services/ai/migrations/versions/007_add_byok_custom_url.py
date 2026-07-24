"""add_byok_custom_url

Revision ID: 007
Revises: 006
Create Date: 2026-07-24
"""

from alembic import op
import sqlalchemy as sa

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None

PROVIDERS = ["openrouter", "groq", "google", "anthropic", "openai", "deepseek", "xai"]


def upgrade() -> None:
    for provider in PROVIDERS:
        op.add_column(
            "api_keys",
            sa.Column(
                f"{provider}_custom_url",
                sa.Text(),
                nullable=True,
            ),
            schema="ai",
        )
        op.add_column(
            "api_keys",
            sa.Column(
                f"{provider}_last_validated",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
            schema="ai",
        )


def downgrade() -> None:
    for provider in PROVIDERS:
        op.drop_column("api_keys", f"{provider}_last_validated", schema="ai")
        op.drop_column("api_keys", f"{provider}_custom_url", schema="ai")
