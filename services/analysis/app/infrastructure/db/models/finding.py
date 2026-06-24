from uuid import UUID

from sqlalchemy import Boolean, Float, Integer, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base, UUIDColumn


class FindingModel(Base):
    __tablename__ = "analysis_results"
    __table_args__ = {"schema": "analysis"}

    id: Mapped[UUID] = UUIDColumn()
    job_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    repo_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True
    )
    workspace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False
    )

    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    rule_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    enterprise_pattern: Mapped[str | None] = mapped_column(Text, nullable=True)

    file_path: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    line_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    line_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    code_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    fix_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)

    score_impact: Mapped[float | None] = mapped_column(Float, nullable=True)
    rpm_impact: Mapped[int | None] = mapped_column(Integer, nullable=True)
    breaks_at_users: Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_ai_enriched: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationship
    job = relationship("AnalysisJobModel", back_populates="findings")
