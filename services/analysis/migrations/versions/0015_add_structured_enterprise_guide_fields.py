"""Add 16 structured JSONB columns to enterprise_guides

Revision ID: 0015
Revises: 0014
Create Date: 2026-07-10
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "enterprise_guides",
        sa.Column("repository_health", JSONB(), nullable=True),
        schema="analysis",
    )
    op.add_column(
        "enterprise_guides",
        sa.Column("engineering_scorecard", JSONB(), nullable=True),
        schema="analysis",
    )
    op.add_column(
        "enterprise_guides",
        sa.Column("business_risk", JSONB(), nullable=True),
        schema="analysis",
    )
    op.add_column(
        "enterprise_guides",
        sa.Column("scalability_review", JSONB(), nullable=True),
        schema="analysis",
    )
    op.add_column(
        "enterprise_guides",
        sa.Column("technical_debt", JSONB(), nullable=True),
        schema="analysis",
    )
    op.add_column(
        "enterprise_guides",
        sa.Column("issue_clusters", JSONB(), nullable=True),
        schema="analysis",
    )
    op.add_column(
        "enterprise_guides",
        sa.Column("hotspots", JSONB(), nullable=True),
        schema="analysis",
    )
    op.add_column(
        "enterprise_guides",
        sa.Column("service_health", JSONB(), nullable=True),
        schema="analysis",
    )
    op.add_column(
        "enterprise_guides",
        sa.Column("quick_wins", JSONB(), nullable=True),
        schema="analysis",
    )
    op.add_column(
        "enterprise_guides",
        sa.Column("sprint_roadmap", JSONB(), nullable=True),
        schema="analysis",
    )
    op.add_column(
        "enterprise_guides",
        sa.Column("deployment_readiness", JSONB(), nullable=True),
        schema="analysis",
    )
    op.add_column(
        "enterprise_guides",
        sa.Column("release_recommendation", JSONB(), nullable=True),
        schema="analysis",
    )
    op.add_column(
        "enterprise_guides",
        sa.Column("ownership", JSONB(), nullable=True),
        schema="analysis",
    )
    op.add_column(
        "enterprise_guides",
        sa.Column("estimated_effort", JSONB(), nullable=True),
        schema="analysis",
    )
    op.add_column(
        "enterprise_guides",
        sa.Column("ai_recommendations", JSONB(), nullable=True),
        schema="analysis",
    )
    op.add_column(
        "enterprise_guides",
        sa.Column("raw_findings", JSONB(), nullable=True),
        schema="analysis",
    )


def downgrade() -> None:
    op.drop_column("enterprise_guides", "raw_findings", schema="analysis")
    op.drop_column("enterprise_guides", "ai_recommendations", schema="analysis")
    op.drop_column("enterprise_guides", "estimated_effort", schema="analysis")
    op.drop_column("enterprise_guides", "ownership", schema="analysis")
    op.drop_column("enterprise_guides", "release_recommendation", schema="analysis")
    op.drop_column("enterprise_guides", "deployment_readiness", schema="analysis")
    op.drop_column("enterprise_guides", "sprint_roadmap", schema="analysis")
    op.drop_column("enterprise_guides", "quick_wins", schema="analysis")
    op.drop_column("enterprise_guides", "service_health", schema="analysis")
    op.drop_column("enterprise_guides", "hotspots", schema="analysis")
    op.drop_column("enterprise_guides", "issue_clusters", schema="analysis")
    op.drop_column("enterprise_guides", "technical_debt", schema="analysis")
    op.drop_column("enterprise_guides", "scalability_review", schema="analysis")
    op.drop_column("enterprise_guides", "business_risk", schema="analysis")
    op.drop_column("enterprise_guides", "engineering_scorecard", schema="analysis")
    op.drop_column("enterprise_guides", "repository_health", schema="analysis")
