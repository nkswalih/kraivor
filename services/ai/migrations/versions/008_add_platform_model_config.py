"""add_platform_model_config

Revision ID: 008
Revises: 007
Create Date: 2026-07-26
"""

from alembic import op
import sqlalchemy as sa

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── platform_providers ──
    op.create_table(
        "platform_providers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("provider_name", sa.String(50), nullable=False, unique=True),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("base_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("rate_limit_rpm", sa.Integer(), nullable=True),
        sa.Column("rate_limit_tpm", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        schema="ai",
    )

    # ── platform_models ──
    op.create_table(
        "platform_models",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("model_id", sa.String(200), nullable=False, unique=True),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("provider_name", sa.String(50), nullable=False, index=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("tier", sa.String(20), nullable=False, server_default="free"),
        sa.Column("context_window", sa.Integer(), server_default="131072"),
        sa.Column("max_output_tokens", sa.Integer(), server_default="16384"),
        sa.Column("input_price_per_mtok", sa.Numeric(10, 6), server_default="0"),
        sa.Column("output_price_per_mtok", sa.Numeric(10, 6), server_default="0"),
        sa.Column("is_trial", sa.Boolean(), server_default="false"),
        sa.Column("trial_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("supports_tools", sa.Boolean(), server_default="false"),
        sa.Column("supports_vision", sa.Boolean(), server_default="false"),
        sa.Column("supports_reasoning", sa.Boolean(), server_default="false"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        schema="ai",
    )

    # ── platform_task_routes ──
    op.create_table(
        "platform_task_routes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("task_name", sa.String(100), nullable=False, unique=True),
        sa.Column("primary_model_id", sa.String(200), nullable=False),
        sa.Column("fallback_model_id", sa.String(200), nullable=True),
        sa.Column("max_tokens", sa.Integer(), nullable=False, server_default="4096"),
        sa.Column("timeout_seconds", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        schema="ai",
    )

    # ── platform_admins ──
    op.create_table(
        "platform_admins",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.String(100), nullable=False, unique=True, index=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        schema="ai",
    )


def downgrade() -> None:
    op.drop_table("platform_admins", schema="ai")
    op.drop_table("platform_task_routes", schema="ai")
    op.drop_table("platform_models", schema="ai")
    op.drop_table("platform_providers", schema="ai")
