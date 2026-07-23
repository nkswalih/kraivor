"""Add total_files, total_lines columns to analysis_jobs

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-28
"""

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "analysis_jobs",
        sa.Column("total_files", sa.Integer(), nullable=True),
        schema="analysis",
    )
    op.add_column(
        "analysis_jobs",
        sa.Column("total_lines", sa.Integer(), nullable=True),
        schema="analysis",
    )


def downgrade() -> None:
    op.drop_column("analysis_jobs", "total_files", schema="analysis")
    op.drop_column("analysis_jobs", "total_lines", schema="analysis")
