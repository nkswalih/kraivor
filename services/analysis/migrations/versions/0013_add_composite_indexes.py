"""Add composite indexes for common query patterns

- (job_id, status, severity) on analysis_results — covers the main
  findings-list query (WHERE job_id + status + optional severity filter +
  ORDER BY severity)
- (job_id, status, category) on analysis_results — covers category-filtered
  queries and count_by_category aggregation

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-09
"""

import sqlalchemy as sa

from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_index(
        "idx_results_job_status_severity",
        "analysis_results",
        ["job_id", "status", "severity"],
        schema="analysis",
        postgresql_using="btree",
    )
    op.create_index(
        "idx_results_job_status_category",
        "analysis_results",
        ["job_id", "status", "category"],
        schema="analysis",
        postgresql_using="btree",
    )


def downgrade() -> None:
    op.drop_index(
        "idx_results_job_status_severity",
        table_name="analysis_results",
        schema="analysis",
    )
    op.drop_index(
        "idx_results_job_status_category",
        table_name="analysis_results",
        schema="analysis",
    )
