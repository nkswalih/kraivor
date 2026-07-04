from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base, UUIDColumn


class PerformanceMetricModel(Base):
    __tablename__ = "performance_metrics"
    __table_args__ = {"schema": "analysis"}

    id: Mapped[UUID] = UUIDColumn()
    job_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("analysis.analysis_jobs.id"),
        nullable=False,
        index=True,
    )
    repo_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True
    )
    workspace_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)

    metric_type: Mapped[str] = mapped_column(String(50), nullable=False)
    endpoint: Mapped[str | None] = mapped_column(Text, nullable=True)
    http_method: Mapped[str | None] = mapped_column(String(10), nullable=True)
    estimated_rpm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    p50_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    p95_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    p99_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_concurrent_users: Mapped[int | None] = mapped_column(Integer, nullable=True)

    bottleneck_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bottleneck_severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    bottleneck_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationship
    job = relationship("AnalysisJobModel", back_populates="performance_metrics")
