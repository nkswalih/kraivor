"""sync conversation and message tables with ORM models

Revision ID: 002
Revises: 001
Create Date: 2026-06-30
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- conversations ---
    # drop metadata (no longer in model)
    op.drop_column("conversations", "metadata", schema="ai")

    # add model, message_count, is_archived, last_message_at
    op.add_column(
        "conversations",
        sa.Column("model", sa.String(100), nullable=True),
        schema="ai",
    )
    op.add_column(
        "conversations",
        sa.Column("message_count", sa.Integer(), server_default="0", nullable=False),
        schema="ai",
    )
    op.add_column(
        "conversations",
        sa.Column("is_archived", sa.Boolean(), server_default="false", nullable=False),
        schema="ai",
    )
    op.add_column(
        "conversations",
        sa.Column(
            "last_message_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        schema="ai",
    )

    # add deleted_at from TimestampMixin
    op.add_column(
        "conversations",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        schema="ai",
    )

    # make workspace_id NOT NULL
    op.alter_column(
        "conversations",
        "workspace_id",
        existing_type=sa.String(),
        nullable=False,
        schema="ai",
    )
    # make title NOT NULL with a default
    op.alter_column(
        "conversations",
        "title",
        existing_type=sa.String(255),
        nullable=False,
        server_default="New conversation",
        schema="ai",
    )

    # --- messages ---
    # add user_id, tokens_input, tokens_output
    op.add_column(
        "messages",
        sa.Column("user_id", sa.String(), nullable=False, server_default=""),
        schema="ai",
    )
    op.add_column(
        "messages",
        sa.Column("tokens_input", sa.Integer(), nullable=True),
        schema="ai",
    )
    op.add_column(
        "messages",
        sa.Column("tokens_output", sa.Integer(), nullable=True),
        schema="ai",
    )

    # add updated_at and deleted_at from TimestampMixin
    op.add_column(
        "messages",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        schema="ai",
    )
    op.add_column(
        "messages",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        schema="ai",
    )

    # drop token_count (replaced by tokens_input/tokens_output)
    op.drop_column("messages", "token_count", schema="ai")

    # add indexes
    op.create_index(op.f("ix_ai_messages_user_id"), "messages", ["user_id"], schema="ai")
    op.create_index(
        op.f("ix_ai_conversations_user_id"), "conversations", ["user_id"], schema="ai"
    )
    op.create_index(
        op.f("ix_ai_conversations_workspace_id"),
        "conversations",
        ["workspace_id"],
        schema="ai",
    )


def downgrade() -> None:
    # --- messages ---
    op.drop_index(op.f("ix_ai_messages_user_id"), table_name="messages", schema="ai")
    op.add_column(
        "messages",
        sa.Column("token_count", sa.Integer(), nullable=True),
        schema="ai",
    )
    op.drop_column("messages", "deleted_at", schema="ai")
    op.drop_column("messages", "updated_at", schema="ai")
    op.drop_column("messages", "tokens_output", schema="ai")
    op.drop_column("messages", "tokens_input", schema="ai")
    op.drop_column("messages", "user_id", schema="ai")

    # --- conversations ---
    op.drop_index(
        op.f("ix_ai_conversations_workspace_id"), table_name="conversations", schema="ai"
    )
    op.drop_index(
        op.f("ix_ai_conversations_user_id"), table_name="conversations", schema="ai"
    )
    op.alter_column(
        "conversations",
        "title",
        existing_type=sa.String(255),
        nullable=True,
        server_default=None,
        schema="ai",
    )
    op.alter_column(
        "conversations",
        "workspace_id",
        existing_type=sa.String(),
        nullable=True,
        schema="ai",
    )
    op.drop_column("conversations", "deleted_at", schema="ai")
    op.drop_column("conversations", "last_message_at", schema="ai")
    op.drop_column("conversations", "is_archived", schema="ai")
    op.drop_column("conversations", "message_count", schema="ai")
    op.drop_column("conversations", "model", schema="ai")
    op.add_column(
        "conversations",
        sa.Column("metadata", postgresql.JSON(), nullable=True),
        schema="ai",
    )
