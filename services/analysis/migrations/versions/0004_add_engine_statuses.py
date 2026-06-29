"""Add engine_statuses and blocked_by JSON columns to analysis_jobs

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-29
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSON

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "analysis_jobs",
        sa.Column("blocked_by", JSON, nullable=True),
        schema="analysis",
    )
    op.add_column(
        "analysis_jobs",
        sa.Column("engine_statuses", JSON, nullable=True),
        schema="analysis",
    )


def downgrade() -> None:
    op.drop_column("analysis_jobs", "engine_statuses", schema="analysis")
    op.drop_column("analysis_jobs", "blocked_by", schema="analysis")
