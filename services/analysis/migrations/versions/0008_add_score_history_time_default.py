"""Add missing server_default to score_history.time column

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-29
"""

import sqlalchemy as sa

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.alter_column(
        "score_history", "time", server_default=sa.func.now(), schema="analysis"
    )


def downgrade() -> None:
    op.alter_column("score_history", "time", server_default=None, schema="analysis")
