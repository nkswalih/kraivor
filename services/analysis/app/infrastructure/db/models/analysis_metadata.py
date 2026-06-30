from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import JSON, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base, UUIDColumn


class AnalysisMetadataModel(Base):
    __tablename__ = "analysis_metadata"
    __table_args__ = {"schema": "analysis"}

    id: Mapped[UUID] = UUIDColumn()
    job_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("analysis.analysis_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    class_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    function_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    endpoint_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    languages: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    frameworks: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        onupdate=lambda: datetime.now(),
        nullable=True,
    )
