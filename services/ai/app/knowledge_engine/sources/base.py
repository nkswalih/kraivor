"""Base protocols and data models for knowledge sources."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable


@dataclass
class SourceResult:
    """A single search result from a knowledge source."""

    url: str
    title: str
    snippet: str
    source_provider: str
    published_at: datetime | None = None
    author: str | None = None
    trust_score: float = 0.5
    metadata: dict = field(default_factory=dict)

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(f"{self.url}:{self.title}".encode()).hexdigest()[:16]


@dataclass
class SourceContent:
    """Full content fetched from a source."""

    url: str
    title: str
    text: str
    source_provider: str
    published_at: datetime | None = None
    author: str | None = None
    trust_score: float = 0.5
    fetched_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict = field(default_factory=dict)

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.text.encode()).hexdigest()[:16]


@dataclass
class RankedSource:
    """A source with its computed ranking scores."""

    source: SourceContent
    relevance_score: float = 0.0
    authority_score: float = 0.0
    freshness_score: float = 0.0
    extractability_score: float = 0.0
    composite_score: float = 0.0

    def to_context_dict(self) -> dict:
        return {
            "url": self.source.url,
            "title": self.source.title,
            "text": self.source.text[:3000],
            "published_at": self.source.published_at.isoformat() if self.source.published_at else None,
            "author": self.source.author,
            "trust_score": round(self.source.trust_score, 2),
            "relevance_score": round(self.relevance_score, 2),
            "authority_score": round(self.authority_score, 2),
            "freshness_score": round(self.freshness_score, 2),
            "composite_score": round(self.composite_score, 2),
        }


@runtime_checkable
class BaseSourceProvider(Protocol):
    """Protocol for all knowledge source providers."""

    @property
    def name(self) -> str: ...

    @property
    def base_trust_score(self) -> float: ...

    async def search(self, query: str, max_results: int = 5) -> list[SourceResult]: ...

    async def fetch_content(self, url: str) -> SourceContent | None: ...
