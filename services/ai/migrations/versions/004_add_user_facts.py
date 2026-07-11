"""add user_facts table for cross-session memory

Revision ID: 004
Revises: 003
Create Date: 2026-07-11
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_facts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False, index=True),
        sa.Column("fact_type", sa.String(50), nullable=False, index=True),
        sa.Column("fact_key", sa.String(255), nullable=False),
        sa.Column("fact_value", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("source_conversation_id", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        schema="ai",
    )
    op.create_index(
        "ix_user_facts_user_fact",
        "user_facts",
        ["user_id", "fact_type"],
        schema="ai",
    )
    op.create_index(
        "ix_user_facts_user_key",
        "user_facts",
        ["user_id", "fact_key"],
        unique=True,
        schema="ai",
    )


def downgrade() -> None:
    op.drop_index("ix_user_facts_user_key", schema="ai")
    op.drop_index("ix_user_facts_user_fact", schema="ai")
    op.drop_table("user_facts", schema="ai")
