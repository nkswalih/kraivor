from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.models.base import Base, TimestampMixin, UUIDMixin


class IndexJob(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "index_jobs"
    __table_args__ = {"schema": "ai"}

    repo_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    clone_url: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    total_files: Mapped[int | None] = mapped_column(Integer, nullable=True)
    files_indexed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunks_created: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
