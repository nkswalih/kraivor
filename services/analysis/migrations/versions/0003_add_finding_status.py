"""Add status column to analysis_results for finding suppression

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-29
"""

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "analysis_results",
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        schema="analysis",
    )
    op.create_index(
        "idx_results_status", "analysis_results", ["status"], schema="analysis"
    )


def downgrade() -> None:
    op.drop_index(
        "idx_results_status", table_name="analysis_results", schema="analysis"
    )
    op.drop_column("analysis_results", "status", schema="analysis")
