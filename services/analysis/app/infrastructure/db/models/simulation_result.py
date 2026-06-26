from uuid import UUID

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base, UUIDColumn


class SimulationResultModel(Base):
    __tablename__ = "simulation_results"
    __table_args__ = {"schema": "analysis"}

    id: Mapped[UUID] = UUIDColumn()
    job_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("analysis.analysis_jobs.id"), nullable=False, index=True
    )
    repo_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True
    )
    workspace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False
    )

    concurrent_users: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    overall_rpm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_rate_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    endpoints_analysis: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    bottlenecks: Mapped[list[object] | None] = mapped_column(JSONB, nullable=True)

    # Relationship
    job = relationship("AnalysisJobModel", back_populates="simulation_results")
