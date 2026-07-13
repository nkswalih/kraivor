"""Combines all ranking layers into a composite score."""

from __future__ import annotations

import logging

from app.knowledge_engine.ranking.relevance import score_relevance
from app.knowledge_engine.ranking.authority import (
    score_authority_and_freshness,
    get_domain_half_life,
)
from app.knowledge_engine.ranking.extractability import score_extractability
from app.knowledge_engine.sources.base import SourceResult, SourceContent

logger = logging.getLogger(__name__)


async def rank_sources(
    query: str,
    sources: list[SourceResult | SourceContent],
    embedder=None,
    min_composite_score: float = 0.4,
) -> list:
    """Full three-layer ranking pipeline.

    L1: Relevance (semantic similarity)
    L2: Authority + Freshness (trust score + temporal decay)
    L3: Extractability (content structure quality)

    Composite = 0.4 * relevance + 0.35 * authority + 0.15 * freshness + 0.1 * extractability
    """
    if not sources:
        return []

    # L1: Relevance
    ranked = await score_relevance(query, sources, embedder)

    # L2: Authority + Freshness (per-source half-life)
    for r in ranked:
        half_life = get_domain_half_life(r.source.url)
        score_authority_and_freshness([r], half_life)

    # L3: Extractability
    score_extractability(ranked)

    # Composite score
    for r in ranked:
        r.composite_score = (
            0.40 * r.relevance_score
            + 0.35 * r.authority_score
            + 0.15 * r.freshness_score
            + 0.10 * r.extractability_score
        )

    # Filter by minimum score and sort
    ranked = [r for r in ranked if r.composite_score >= min_composite_score]
    ranked.sort(key=lambda r: r.composite_score, reverse=True)

    logger.info(
        "Ranked %d sources (from %d), top score: %.2f",
        len(ranked),
        len(sources),
        ranked[0].composite_score if ranked else 0,
    )

    return ranked
