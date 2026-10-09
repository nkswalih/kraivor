"""Add ai_summary_error column to enterprise_guides

Revision ID: 0016
Revises: 0015
Create Date: 2026-10-05
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # Why a migration and not a field on `analysis_metadata`.
    #
    # `ai_executive_summary` lives on `enterprise_guides`, and the guide endpoint
    # reads from that table. Putting the reason the summary is missing in a
    # different table would mean the guide response had to join two sources to
    # describe one field -- and the two would disagree whenever a write to one
    # succeeded and the other did not.
    #
    # This is also different in kind from the `queue_wait_seconds` column that is
    # deliberately still around. That one is dead weight to be deleted in a
    # cleanup migration; this is new state that has to exist somewhere durable,
    # and a migration is the tool for that.
    #
    # JSONB rather than four columns: the envelope is built by another service
    # and read by a browser. A fixed set of columns would mean this migration had
    # to be revised every time a `ClassifiedError` category is added, and the
    # reason the AI service builds that envelope from named fields rather than
    # copying the exception is precisely so a new field cannot leak by accident.
    # A JSONB column keeps that property at both ends.
    #
    # Nullable, and null is the normal state. Almost every run has a summary and
    # therefore no error.
    op.add_column(
        "enterprise_guides",
        sa.Column("ai_summary_error", JSONB(), nullable=True),
        schema="analysis",
    )


def downgrade() -> None:
    op.drop_column("enterprise_guides", "ai_summary_error", schema="analysis")
