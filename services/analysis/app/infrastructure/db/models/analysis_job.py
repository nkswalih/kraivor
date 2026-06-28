from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, Integer, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDColumn


class AnalysisJobModel(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "analysis_jobs"
    __table_args__ = {"schema": "analysis"}

    id: Mapped[UUID] = UUIDColumn()
    repo_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    workspace_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    triggered_by: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(20), default="manual")
    repo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    branch: Mapped[str] = mapped_column(String(255), default="main")
    deep_scan: Mapped[bool] = mapped_column(Boolean, default=True)
    simulate_users: Mapped[list[int] | None] = mapped_column(
        ARRAY(Integer), nullable=True, default=[100, 500, 5000]
    )

    status: Mapped[str] = mapped_column(String(30), default="queued", index=True)
    progress_pct: Mapped[int] = mapped_column(SmallInteger, default=0)
    progress_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    total_files: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_lines: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_findings: Mapped[int] = mapped_column(Integer, default=0)
    critical_count: Mapped[int] = mapped_column(Integer, default=0)
    high_count: Mapped[int] = mapped_column(Integer, default=0)
    medium_count: Mapped[int] = mapped_column(Integer, default=0)
    low_count: Mapped[int] = mapped_column(Integer, default=0)

    overall_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    performance_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    security_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    reliability_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    maintainability_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    devops_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    queue_wait_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    findings = relationship("FindingModel", back_populates="job", lazy="selectin")
    dead_code_entries = relationship("DeadCodeModel", back_populates="job", lazy="selectin")
    error_findings = relationship("ErrorFindingModel", back_populates="job", lazy="selectin")
    performance_metrics = relationship("PerformanceMetricModel", back_populates="job", lazy="selectin")
    simulation_results = relationship("SimulationResultModel", back_populates="job", lazy="selectin")
    enterprise_guide = relationship("EnterpriseGuideModel", back_populates="job", uselist=False, lazy="selectin")
