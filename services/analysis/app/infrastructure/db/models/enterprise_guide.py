from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base, UUIDColumn


class EnterpriseGuideModel(Base):
    __tablename__ = "enterprise_guides"
    __table_args__ = {"schema": "analysis"}

    id: Mapped[UUID] = UUIDColumn()
    job_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("analysis.analysis_jobs.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    repo_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True
    )
    workspace_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)

    # ── Legacy columns (backward compat) ────────────────────────
    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    critical_issues: Mapped[list[object] | None] = mapped_column(JSONB, nullable=True)
    high_issues: Mapped[list[object] | None] = mapped_column(JSONB, nullable=True)
    medium_issues: Mapped[list[object] | None] = mapped_column(JSONB, nullable=True)
    architecture_review: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True
    )
    capacity_analysis: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True
    )
    migration_path: Mapped[list[object] | None] = mapped_column(JSONB, nullable=True)
    ai_executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── New structured columns ──────────────────────────────────
    repository_health: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True
    )
    engineering_scorecard: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True
    )
    business_risk: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True
    )
    scalability_review: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True
    )
    technical_debt: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True
    )
    issue_clusters: Mapped[list[object] | None] = mapped_column(JSONB, nullable=True)
    hotspots: Mapped[list[object] | None] = mapped_column(JSONB, nullable=True)
    service_health: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True
    )
    quick_wins: Mapped[list[object] | None] = mapped_column(JSONB, nullable=True)
    sprint_roadmap: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True
    )
    deployment_readiness: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True
    )
    release_recommendation: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True
    )
    ownership: Mapped[list[object] | None] = mapped_column(JSONB, nullable=True)
    estimated_effort: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True
    )
    ai_recommendations: Mapped[list[object] | None] = mapped_column(
        JSONB, nullable=True
    )
    raw_findings: Mapped[list[object] | None] = mapped_column(JSONB, nullable=True)

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    # Relationship
    job = relationship("AnalysisJobModel", back_populates="enterprise_guide")
