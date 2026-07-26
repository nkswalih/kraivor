from datetime import datetime

from sqlalchemy import Boolean, DateTime, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.models.base import Base, TimestampMixin, UUIDMixin


class PlatformModel(Base, UUIDMixin, TimestampMixin):
    """Model registry — global model configuration (platform-level)."""

    __tablename__ = "platform_models"
    __table_args__ = {"schema": "ai"}

    frontend_id: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    model_id: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    tier: Mapped[str] = mapped_column(String(20), nullable=False, default="free")
    context_window: Mapped[int] = mapped_column(default=131072)
    max_output_tokens: Mapped[int] = mapped_column(default=16384)
    input_price_per_mtok: Mapped[float] = mapped_column(Numeric(10, 6), default=0.0)
    output_price_per_mtok: Mapped[float] = mapped_column(Numeric(10, 6), default=0.0)
    is_trial: Mapped[bool] = mapped_column(Boolean, default=False)
    trial_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    supports_tools: Mapped[bool] = mapped_column(Boolean, default=False)
    supports_vision: Mapped[bool] = mapped_column(Boolean, default=False)
    supports_reasoning: Mapped[bool] = mapped_column(Boolean, default=False)
    latency_display: Mapped[str | None] = mapped_column(String(10), nullable=True)
    icon_key: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
