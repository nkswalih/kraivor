"""Add devops_findings table for the DevOps Engine

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-29
"""

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "devops_findings",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("analysis.analysis_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("repo_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("devops_type", sa.String(50), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("line_start", sa.Integer(), nullable=True),
        sa.Column("line_end", sa.Integer(), nullable=True),
        sa.Column("code_snippet", sa.Text(), nullable=True),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), server_default=sa.text("0.8"), nullable=True),
        sa.Column("devops_score", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema="analysis",
    )
    op.create_index(
        "idx_devops_job",
        "devops_findings",
        ["job_id"],
        schema="analysis",
    )
    op.create_index(
        "idx_devops_type",
        "devops_findings",
        ["devops_type"],
        schema="analysis",
    )


def downgrade() -> None:
    op.drop_index("idx_devops_type", table_name="devops_findings", schema="analysis")
    op.drop_index("idx_devops_job", table_name="devops_findings", schema="analysis")
    op.drop_table("devops_findings", schema="analysis")
