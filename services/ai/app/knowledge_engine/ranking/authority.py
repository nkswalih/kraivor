"""L2: Authority and freshness scoring."""

from __future__ import annotations

from datetime import UTC, datetime

from app.knowledge_engine.sources.base import RankedSource


def score_authority_and_freshness(
    ranked: list[RankedSource],
    half_life_days: int = 30,
) -> list[RankedSource]:
    """Score sources by authority (trust) and freshness (recency).

    Composite: 0.6 * authority + 0.4 * freshness
    """
    now = datetime.now(UTC)
    for r in ranked:
        # Authority: trust score from curated list
        authority = r.source.trust_score

        # Freshness: exponential decay from publication date
        if r.source.published_at:
            pub = r.source.published_at
            if pub.tzinfo is None:
                pub = pub.replace(tzinfo=UTC)
            delta_days = max(0, (now - pub).days)
            freshness = max(0.1, 0.5 ** (delta_days / half_life_days))
        else:
            freshness = 0.5  # Unknown date = moderate score

        r.authority_score = authority
        r.freshness_score = freshness

    return ranked


def get_domain_half_life(url: str) -> int:
    """Get appropriate freshness half-life based on domain."""
    from urllib.parse import urlparse

    domain = urlparse(url).netloc.lower()

    if any(kw in domain for kw in ["news", "techcrunch", "verge", "arstechnica"]):
        return 7  # News: fast decay
    if "github.com" in domain:
        return 30  # Releases: moderate decay
    if any(d in domain for d in ["arxiv.org", "semanticscholar.org"]):
        return 365  # Research: slow decay
    if any(d in domain for d in ["stackoverflow.com", "dev.to"]):
        return 90  # Community: moderate decay
    if "reddit.com" in domain:
        return 30  # Reddit: fast decay
    return 60  # Default
