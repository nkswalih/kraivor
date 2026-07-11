from sqlalchemy import Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.models.base import Base, TimestampMixin


class UserFact(Base, TimestampMixin):
    __tablename__ = "user_facts"
    __table_args__ = {"schema": "ai"}

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    fact_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    fact_key: Mapped[str] = mapped_column(String(255), nullable=False)
    fact_value: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    source_conversation_id: Mapped[str | None] = mapped_column(
        String, nullable=True
    )
