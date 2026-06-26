"""Initial schema for Analysis Service.

Revision ID: 0001
Revises:
Create Date: 2026-06-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS analysis")

    # ── Analysis Jobs ─────────────────────────────────────────────────────
    op.create_table(
        "analysis_jobs",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("repo_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("triggered_by", sa.Uuid(), nullable=False),
        sa.Column("trigger_type", sa.String(20), server_default="manual", nullable=True),
        sa.Column("repo_url", sa.Text(), nullable=True),
        sa.Column("branch", sa.String(255), server_default="main", nullable=True),
        sa.Column("deep_scan", sa.Boolean(), server_default=sa.text("true"), nullable=True),
        sa.Column("simulate_users", sa.ARRAY(sa.Integer()), server_default=sa.text("'{100,500,5000}'"), nullable=True),
        sa.Column("status", sa.String(30), server_default="queued", nullable=True),
        sa.Column("progress_pct", sa.SmallInteger(), server_default=sa.text("0"), nullable=True),
        sa.Column("progress_message", sa.String(500), nullable=True),
        sa.Column("total_findings", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.Column("critical_count", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.Column("high_count", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.Column("medium_count", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.Column("low_count", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.Column("overall_score", sa.SmallInteger(), nullable=True),
        sa.Column("performance_score", sa.SmallInteger(), nullable=True),
        sa.Column("security_score", sa.SmallInteger(), nullable=True),
        sa.Column("reliability_score", sa.SmallInteger(), nullable=True),
        sa.Column("maintainability_score", sa.SmallInteger(), nullable=True),
        sa.Column("devops_score", sa.SmallInteger(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("queue_wait_seconds", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", schema="analysis"),
        schema="analysis",
    )
    op.create_index("idx_jobs_repo", "analysis_jobs", ["repo_id", sa.text("created_at DESC")], schema="analysis")
    op.create_index("idx_jobs_workspace", "analysis_jobs", ["workspace_id", sa.text("created_at DESC")], schema="analysis")
    op.create_index("idx_jobs_status", "analysis_jobs", ["status"], schema="analysis", postgresql_where=sa.text("deleted_at IS NULL"))
    op.create_index("idx_jobs_triggered_by", "analysis_jobs", ["triggered_by"], schema="analysis")

    # ── Analysis Findings ──────────────────────────────────────────────────
    op.create_table(
        "analysis_results",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("analysis.analysis_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("repo_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("rule_id", sa.String(100), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column("enterprise_pattern", sa.Text(), nullable=True),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("line_start", sa.Integer(), nullable=True),
        sa.Column("line_end", sa.Integer(), nullable=True),
        sa.Column("code_snippet", sa.Text(), nullable=True),
        sa.Column("fix_snippet", sa.Text(), nullable=True),
        sa.Column("score_impact", sa.Numeric(5, 2), nullable=True),
        sa.Column("rpm_impact", sa.Integer(), nullable=True),
        sa.Column("breaks_at_users", sa.Integer(), nullable=True),
        sa.Column("is_ai_enriched", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("ai_explanation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id", schema="analysis"),
        schema="analysis",
    )
    op.create_index("idx_results_job", "analysis_results", ["job_id"], schema="analysis")
    op.create_index("idx_results_repo", "analysis_results", ["repo_id"], schema="analysis")
    op.create_index("idx_results_category", "analysis_results", ["repo_id", "category"], schema="analysis")
    op.create_index("idx_results_severity", "analysis_results", ["repo_id", "severity"], schema="analysis")
    op.create_index("idx_results_file", "analysis_results", ["repo_id", "file_path"], schema="analysis")

    # ── Dead Code ──────────────────────────────────────────────────────────
    op.create_table(
        "dead_code",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("analysis.analysis_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("repo_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("code_type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("line_start", sa.Integer(), nullable=True),
        sa.Column("line_end", sa.Integer(), nullable=True),
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Numeric(3, 2), server_default=sa.text("0.0"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id", schema="analysis"),
        schema="analysis",
    )
    op.create_index("idx_dead_code_job", "dead_code", ["job_id"], schema="analysis")
    op.create_index("idx_dead_code_type", "dead_code", ["repo_id", "code_type"], schema="analysis")
    op.create_index("idx_dead_code_file", "dead_code", ["repo_id", "file_path"], schema="analysis")

    # ── Error Findings ─────────────────────────────────────────────────────
    op.create_table(
        "error_findings",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("analysis.analysis_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("repo_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("error_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("line_start", sa.Integer(), nullable=True),
        sa.Column("line_end", sa.Integer(), nullable=True),
        sa.Column("code_snippet", sa.Text(), nullable=True),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id", schema="analysis"),
        schema="analysis",
    )
    op.create_index("idx_errors_job", "error_findings", ["job_id"], schema="analysis")
    op.create_index("idx_errors_type", "error_findings", ["repo_id", "error_type"], schema="analysis")

    # ── Performance Metrics ────────────────────────────────────────────────
    op.create_table(
        "performance_metrics",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("analysis.analysis_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("repo_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("metric_type", sa.String(50), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=True),
        sa.Column("http_method", sa.String(10), nullable=True),
        sa.Column("estimated_rpm", sa.Integer(), nullable=True),
        sa.Column("p50_latency_ms", sa.Integer(), nullable=True),
        sa.Column("p95_latency_ms", sa.Integer(), nullable=True),
        sa.Column("p99_latency_ms", sa.Integer(), nullable=True),
        sa.Column("max_concurrent_users", sa.Integer(), nullable=True),
        sa.Column("bottleneck_type", sa.String(100), nullable=True),
        sa.Column("bottleneck_severity", sa.String(20), nullable=True),
        sa.Column("bottleneck_detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id", schema="analysis"),
        schema="analysis",
    )
    op.create_index("idx_perf_job", "performance_metrics", ["job_id"], schema="analysis")
    op.create_index("idx_perf_repo", "performance_metrics", ["repo_id"], schema="analysis")

    # ── Simulation Results ─────────────────────────────────────────────────
    op.create_table(
        "simulation_results",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("analysis.analysis_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("repo_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("concurrent_users", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("overall_rpm", sa.Integer(), nullable=True),
        sa.Column("error_rate_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("endpoints_analysis", sa.JSONB(), nullable=True),
        sa.Column("bottlenecks", sa.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id", schema="analysis"),
        schema="analysis",
    )
    op.create_index("idx_sim_job", "simulation_results", ["job_id"], schema="analysis")
    op.create_index("idx_sim_users", "simulation_results", ["repo_id", "concurrent_users"], schema="analysis")

    # ── Score History ──────────────────────────────────────────────────────
    op.create_table(
        "score_history",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("repo_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("overall_score", sa.SmallInteger(), nullable=False),
        sa.Column("performance_score", sa.SmallInteger(), nullable=True),
        sa.Column("security_score", sa.SmallInteger(), nullable=True),
        sa.Column("reliability_score", sa.SmallInteger(), nullable=True),
        sa.Column("maintainability_score", sa.SmallInteger(), nullable=True),
        sa.Column("devops_score", sa.SmallInteger(), nullable=True),
        sa.Column("findings_count", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.Column("job_id", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("time", "repo_id", schema="analysis"),
        schema="analysis",
    )
    op.create_index("idx_score_history_repo", "score_history", ["repo_id", sa.text("time DESC")], schema="analysis")
    op.create_index("idx_score_history_workspace", "score_history", ["workspace_id", sa.text("time DESC")], schema="analysis")

    # ── Enterprise Guides ──────────────────────────────────────────────────
    op.create_table(
        "enterprise_guides",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("analysis.analysis_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("repo_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("executive_summary", sa.Text(), nullable=True),
        sa.Column("critical_issues", sa.JSONB(), nullable=True),
        sa.Column("high_issues", sa.JSONB(), nullable=True),
        sa.Column("medium_issues", sa.JSONB(), nullable=True),
        sa.Column("architecture_review", sa.JSONB(), nullable=True),
        sa.Column("capacity_analysis", sa.JSONB(), nullable=True),
        sa.Column("migration_path", sa.JSONB(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id", schema="analysis"),
        schema="analysis",
    )
    op.create_index("idx_guides_job", "enterprise_guides", ["job_id"], schema="analysis")
    op.create_index("idx_guides_repo", "enterprise_guides", ["repo_id"], schema="analysis")

    # ── File Analyses ──────────────────────────────────────────────────────
    op.create_table(
        "file_analyses",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("analysis.analysis_jobs.id"), nullable=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("original_filename", sa.Text(), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("language", sa.String(50), nullable=True),
        sa.Column("findings_count", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.Column("s3_key", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", schema="analysis"),
        schema="analysis",
    )


def downgrade() -> None:
    op.drop_table("file_analyses", schema="analysis")
    op.drop_table("enterprise_guides", schema="analysis")
    op.drop_table("score_history", schema="analysis")
    op.drop_table("simulation_results", schema="analysis")
    op.drop_table("performance_metrics", schema="analysis")
    op.drop_table("error_findings", schema="analysis")
    op.drop_table("dead_code", schema="analysis")
    op.drop_table("analysis_results", schema="analysis")
    op.drop_table("analysis_jobs", schema="analysis")
    op.execute("DROP SCHEMA IF EXISTS analysis")
