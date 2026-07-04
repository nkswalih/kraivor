from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.models.base import Base, TimestampMixin, UUIDMixin


class ApiKey(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "api_keys"
    __table_args__ = {"schema": "ai"}

    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    workspace_id: Mapped[str | None] = mapped_column(String, nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    scopes: Mapped[dict] = mapped_column(JSON, default=lambda: ["chat"])
    tier: Mapped[str] = mapped_column(String(20), default="free")

    openrouter_subkey_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    groq_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    google_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    active_provider: Mapped[str] = mapped_column(String(50), default="openrouter")

    rate_limit_rpm: Mapped[int] = mapped_column(Integer, default=60)
    rate_limit_tpm: Mapped[int] = mapped_column(Integer, default=100000)
    usage_this_month: Mapped[int] = mapped_column(Integer, default=0)
    usage_limit_monthly: Mapped[int] = mapped_column(Integer, default=1_000_000)

    last_used_at = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at = mapped_column(DateTime(timezone=True), nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
