"""Context builder — formats ranked knowledge with citations for LLM consumption."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.knowledge_engine.sources.base import RankedSource

logger = logging.getLogger(__name__)


def build_knowledge_context(
    ranked_sources: list[RankedSource],
    query: str,
    max_tokens: int = 8000,
    max_citations: int = 10,
) -> str:
    """Build a structured context string from ranked sources.

    Returns formatted knowledge with inline citations for the LLM.
    """
    if not ranked_sources:
        return "No relevant knowledge found."

    sources = ranked_sources[:max_citations]

    lines = [
        f"## Research Results for: {query}",
        "",
        f"*Retrieved {len(sources)} sources at {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}*",
        "",
    ]

    for i, rs in enumerate(sources, 1):
        src = rs.source
        pub_info = ""
        if src.published_at:
            pub_info = f" | Published: {src.published_at.strftime('%Y-%m-%d')}"

        trust_label = _trust_label(rs.composite_score)

        lines.append(f"### [{i}] {src.title}")
        lines.append(f"**Source:** {src.source_provider} | **Trust:** {trust_label} | **Score:** {rs.composite_score:.2f}{pub_info}")
        lines.append(f"**URL:** {src.url}")
        lines.append("")
        lines.append(src.text[:2000])
        lines.append("")
        lines.append("---")
        lines.append("")

    # Add citation summary
    lines.append("## Source Summary")
    lines.append("")
    for i, rs in enumerate(sources, 1):
        lines.append(f"[{i}] {rs.source.title} — {rs.source.url}")
    lines.append("")

    return "\n".join(lines)


def build_citation_list(ranked_sources: list[RankedSource], max_citations: int = 10) -> list[dict]:
    """Build a structured citation list for metadata."""
    citations = []
    for i, rs in enumerate(ranked_sources[:max_citations], 1):
        citations.append({
            "index": i,
            "title": rs.source.title,
            "url": rs.source.url,
            "source_provider": rs.source.source_provider,
            "published_at": rs.source.published_at.isoformat() if rs.source.published_at else None,
            "composite_score": round(rs.composite_score, 3),
            "trust_score": round(rs.source.trust_score, 3),
        })
    return citations


def _trust_label(score: float) -> str:
    """Convert composite score to a human-readable trust label."""
    if score >= 0.8:
        return "High"
    if score >= 0.6:
        return "Medium"
    if score >= 0.4:
        return "Low"
    return "Very Low"
