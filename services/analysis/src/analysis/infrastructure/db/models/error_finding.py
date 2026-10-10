from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base, UUIDColumn


class ErrorFindingModel(Base):
    __tablename__ = "error_findings"
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

    error_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    line_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    line_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    code_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationship
    job = relationship("AnalysisJobModel", back_populates="error_findings")
