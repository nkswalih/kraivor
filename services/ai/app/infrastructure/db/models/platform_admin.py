from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.models.base import Base, TimestampMixin, UUIDMixin


class PlatformAdmin(Base, UUIDMixin, TimestampMixin):
    """Platform superadmin list — controls who can access admin endpoints."""

    __tablename__ = "platform_admins"
    __table_args__ = {"schema": "ai"}

    user_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
