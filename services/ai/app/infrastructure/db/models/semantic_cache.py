from datetime import datetime
from sqlalchemy import Integer, String, Text
from app.infrastructure.db.models.base import Base, UUIDMixin
from sqlalchemy.orm import Mapped, mapped_column


class SemanticCache(Base, UUIDMixin):
    __tablename__ = "semantic_cache"
    __table_args__ = {"schema": "ai"}

    query_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    tokens_saved: Mapped[int] = mapped_column(Integer, default=0)
    hit_count: Mapped[int] = mapped_column(Integer, default=1)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
