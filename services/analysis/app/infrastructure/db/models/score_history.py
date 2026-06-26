from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Integer, SmallInteger, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class ScoreHistoryModel(Base):
    """TimescaleDB hypertable for score tracking over time.

    Note: This table requires TimescaleDB extension.
    Migration will include:
        SELECT create_hypertable('analysis.score_history', 'time');
    """

    __tablename__ = "score_history"
    __table_args__ = {"schema": "analysis"}

    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
        server_default=func.now(),
        nullable=False,
    )
    repo_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True
    )
    workspace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True
    )

    overall_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    performance_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    security_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    reliability_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    maintainability_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    devops_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    findings_count: Mapped[int] = mapped_column(Integer, default=0)
    job_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
