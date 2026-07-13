"""add multimodal columns to knowledge_embeddings

Revision ID: 006
Revises: 005
Create Date: 2026-07-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add multimodal support columns
    op.add_column(
        "knowledge_embeddings",
        sa.Column("source_type", sa.String(20), nullable=True, server_default="web"),
        schema="ai",
    )
    op.add_column(
        "knowledge_embeddings",
        sa.Column("original_filename", sa.Text(), nullable=True),
        schema="ai",
    )
    op.add_column(
        "knowledge_embeddings",
        sa.Column("language", sa.String(10), nullable=True),
        schema="ai",
    )

    # Indexes for new columns
    op.create_index(
        "ix_knowledge_ws_source_type",
        "knowledge_embeddings",
        ["workspace_id", "source_type"],
        schema="ai",
    )
    op.create_index(
        "ix_knowledge_language",
        "knowledge_embeddings",
        ["language"],
        schema="ai",
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_language", schema="ai")
    op.drop_index("ix_knowledge_ws_source_type", schema="ai")
    op.drop_column("knowledge_embeddings", "language", schema="ai")
    op.drop_column("knowledge_embeddings", "original_filename", schema="ai")
    op.drop_column("knowledge_embeddings", "source_type", schema="ai")
