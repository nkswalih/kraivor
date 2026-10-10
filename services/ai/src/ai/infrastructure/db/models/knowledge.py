"""Knowledge Embeddings ORM model — stores retrieved knowledge for future use."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.models.base import Base


class KnowledgeEmbedding(Base):
    """Stores knowledge retrieved from web sources with embeddings for semantic search."""

    __tablename__ = "knowledge_embeddings"
    __table_args__ = (
        Index("ix_knowledge_ws_provider", "workspace_id", "source_provider"),
        Index("ix_knowledge_ws_fetched", "workspace_id", "fetched_at"),
        Index("ix_knowledge_url", "source_url"),
        {"schema": "ai"},
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    source_trust_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    author: Mapped[str | None] = mapped_column(String(500), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
