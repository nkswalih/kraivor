"""Add language_breakdown column to analysis_jobs

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-09
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "analysis_jobs",
        sa.Column("language_breakdown", JSON(), nullable=True),
        schema="analysis",
    )


def downgrade() -> None:
    op.drop_column("analysis_jobs", "language_breakdown", schema="analysis")
