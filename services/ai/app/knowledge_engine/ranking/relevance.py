"""L1: Semantic relevance scoring using the existing embedder."""

from __future__ import annotations

import logging
from app.knowledge_engine.sources.base import SourceResult, SourceContent, RankedSource

logger = logging.getLogger(__name__)


async def score_relevance(
    query: str,
    sources: list[SourceResult | SourceContent],
    embedder=None,
) -> list[RankedSource]:
    """Score sources by semantic relevance to the query.

    Uses cosine similarity between query embedding and source snippet/title embeddings.
    Falls back to keyword matching if embedder is unavailable.
    """
    if not sources:
        return []

    ranked = []
    for src in sources:
        ranked.append(RankedSource(source=src))

    if embedder is not None:
        try:
            query_embedding = await embedder.embed(query)
            for r in ranked:
                text = f"{r.source.title} {r.source.snippet}"
                src_embedding = await embedder.embed(text)
                r.relevance_score = _cosine_similarity(query_embedding, src_embedding)
        except Exception as e:
            logger.warning("Embedding-based relevance failed, falling back to keyword: %s", e)
            _keyword_score(query, ranked)
    else:
        _keyword_score(query, ranked)

    return ranked


def _get_snippet(source) -> str:
    """Get snippet text from either SourceResult or SourceContent."""
    if hasattr(source, "snippet"):
        return source.snippet
    if hasattr(source, "text"):
        return source.text[:500]
    return ""


def _keyword_score(query: str, ranked: list[RankedSource]) -> None:
    """Fallback keyword-based relevance scoring."""
    query_words = set(query.lower().split())
    # Remove common stop words
    stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
                  "have", "has", "had", "do", "does", "did", "will", "would", "could",
                  "should", "may", "might", "can", "shall", "to", "of", "in", "for",
                  "on", "with", "at", "by", "from", "as", "into", "through", "during",
                  "before", "after", "above", "below", "between", "under", "again",
                  "and", "but", "or", "nor", "not", "so", "yet", "both", "either",
                  "neither", "each", "every", "all", "any", "few", "more", "most",
                  "other", "some", "such", "no", "only", "own", "same", "than",
                  "too", "very", "just", "because", "if", "when", "where", "how",
                  "what", "which", "who", "whom", "this", "that", "these", "those"}
    query_words -= stop_words

    for r in ranked:
        text = f"{r.source.title} {_get_snippet(r.source)}".lower()
        text_words = set(text.split())
        if query_words:
            overlap = len(query_words & text_words)
            r.relevance_score = min(1.0, overlap / max(len(query_words), 1))
        else:
            r.relevance_score = 0.3


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
