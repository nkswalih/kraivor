from datetime import datetime
from sqlalchemy import BigInteger, Integer, String
from app.infrastructure.db.models.base import Base, UUIDMixin, TimestampMixin
from sqlalchemy.orm import Mapped, mapped_column


class UsageLog(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "usage_logs"
    __table_args__ = {"schema": "ai"}

    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    conversation_id: Mapped[str | None] = mapped_column(String, nullable=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    tokens_input: Mapped[int] = mapped_column(Integer, default=0)
    tokens_output: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    agent_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="success")
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
