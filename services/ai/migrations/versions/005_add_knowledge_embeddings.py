"""add knowledge_embeddings table for knowledge storage

Revision ID: 005
Revises: 004
Create Date: 2026-07-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create knowledge_embeddings table
    op.create_table(
        "knowledge_embeddings",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("workspace_id", sa.String(), nullable=False, index=True),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_provider", sa.String(50), nullable=False, index=True),
        sa.Column("source_trust_score", sa.Float(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("author", sa.String(500), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("embedding", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        schema="ai",
    )

    # Indexes for efficient queries
    op.create_index(
        "ix_knowledge_ws_provider",
        "knowledge_embeddings",
        ["workspace_id", "source_provider"],
        schema="ai",
    )
    op.create_index(
        "ix_knowledge_ws_fetched",
        "knowledge_embeddings",
        ["workspace_id", "fetched_at"],
        schema="ai",
    )
    op.create_index(
        "ix_knowledge_url",
        "knowledge_embeddings",
        ["source_url"],
        schema="ai",
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_url", schema="ai")
    op.drop_index("ix_knowledge_ws_fetched", schema="ai")
    op.drop_index("ix_knowledge_ws_provider", schema="ai")
    op.drop_table("knowledge_embeddings", schema="ai")
