"""Add languages_detected column to analysis_jobs

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-30
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "analysis_jobs",
        sa.Column("languages_detected", JSON(), nullable=True),
        schema="analysis",
    )


def downgrade() -> None:
    op.drop_column("analysis_jobs", "languages_detected", schema="analysis")
