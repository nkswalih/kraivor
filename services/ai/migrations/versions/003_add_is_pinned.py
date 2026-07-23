"""add is_pinned column to conversations

Revision ID: 003
Revises: 002
Create Date: 2026-07-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("is_pinned", sa.Boolean(), server_default="false", nullable=False),
        schema="ai",
    )


def downgrade() -> None:
    op.drop_column("conversations", "is_pinned", schema="ai")
