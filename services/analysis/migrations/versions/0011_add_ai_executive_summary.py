"""Add ai_executive_summary column to enterprise_guides

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-30
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "enterprise_guides",
        sa.Column("ai_executive_summary", sa.Text(), nullable=True),
        schema="analysis",
    )


def downgrade() -> None:
    op.drop_column("enterprise_guides", "ai_executive_summary", schema="analysis")
