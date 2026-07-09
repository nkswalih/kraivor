"""Add depth column to analysis_jobs

Revision ID: 0014
Revises: 0013
Create Date: 2026-07-09
"""

import sqlalchemy as sa

from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "analysis_jobs",
        sa.Column("depth", sa.SmallInteger(), server_default="1", nullable=False),
        schema="analysis",
    )


def downgrade() -> None:
    op.drop_column("analysis_jobs", "depth", schema="analysis")
