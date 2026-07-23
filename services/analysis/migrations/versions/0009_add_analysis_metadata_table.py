"""Create analysis_metadata table for aggregated parse results

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-30
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "analysis_metadata",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "job_id",
            UUID(as_uuid=True),
            sa.ForeignKey("analysis.analysis_jobs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("class_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("function_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("endpoint_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("languages", JSON(), nullable=True),
        sa.Column("frameworks", JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        schema="analysis",
    )


def downgrade() -> None:
    op.drop_table("analysis_metadata", schema="analysis")
