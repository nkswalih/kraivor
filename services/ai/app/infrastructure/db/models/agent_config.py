from sqlalchemy import JSON, Boolean, String, Text
from app.infrastructure.db.models.base import Base, UUIDMixin, TimestampMixin
from sqlalchemy.orm import Mapped, mapped_column


class AgentConfig(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "agent_configs"
    __table_args__ = {"schema": "ai"}

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    temperature: Mapped[float] = mapped_column(default=0.7)
    max_tokens: Mapped[int] = mapped_column(default=4096)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    tools: Mapped[dict | None] = mapped_column(JSON, nullable=True)
