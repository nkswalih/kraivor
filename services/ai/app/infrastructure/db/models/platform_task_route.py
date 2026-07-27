from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.models.base import Base, TimestampMixin, UUIDMixin


class PlatformTaskRoute(Base, UUIDMixin, TimestampMixin):
    """Task route configuration — maps task names to primary/fallback models."""

    __tablename__ = "platform_task_routes"
    __table_args__ = {"schema": "ai"}

    task_name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    primary_model_id: Mapped[str] = mapped_column(
        String(200), nullable=False
    )
    fallback_model_id: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )
    max_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=4096)
    timeout_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
