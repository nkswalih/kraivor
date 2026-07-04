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

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    # Relationship
    job = relationship("AnalysisJobModel", back_populates="enterprise_guide")
