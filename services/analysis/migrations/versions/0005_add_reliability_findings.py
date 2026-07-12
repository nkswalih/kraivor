"""Add reliability_findings table for the Reliability Engine

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-29
"""

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "reliability_findings",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column(
            "job_id",
            sa.Uuid(),
            sa.ForeignKey("analysis.analysis_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("repo_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("reliability_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("line_start", sa.Integer(), nullable=True),
        sa.Column("line_end", sa.Integer(), nullable=True),
        sa.Column("code_snippet", sa.Text(), nullable=True),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column(
            "confidence", sa.Float(), server_default=sa.text("0.8"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="analysis",
    )
    op.create_index(
        "idx_reliability_job", "reliability_findings", ["job_id"], schema="analysis"
    )
    op.create_index(
        "idx_reliability_type",
        "reliability_findings",
        ["reliability_type"],
        schema="analysis",
    )


def downgrade() -> None:
    op.drop_index(
        "idx_reliability_type", table_name="reliability_findings", schema="analysis"
    )
    op.drop_index(
        "idx_reliability_job", table_name="reliability_findings", schema="analysis"
    )
    op.drop_table("reliability_findings", schema="analysis")
