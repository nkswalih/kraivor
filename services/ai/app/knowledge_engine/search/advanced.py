"""Advanced Search — filtered, multi-criteria knowledge search with ranking.

Extends the basic semantic/text search with:
- Date range filters (created after/before)
- Provider filters (web, docs, github, etc.)
- Trust score threshold (minimum trust)
- Content length filters
- Result ranking by composite score (relevance + trust + recency)
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import text
from app.infrastructure.db.database import async_session_factory
from app.infrastructure.rag.embedder import Embedder

logger = logging.getLogger(__name__)

_embedder = Embedder()


class AdvancedSearch:
    """Multi-criteria knowledge search with composite ranking."""

    async def search(
        self,
        workspace_id: str,
        query: str,
        top_k: int = 10,
        providers: list[str] | None = None,
        min_trust: float = 0.0,
        created_after: str | None = None,
        created_before: str | None = None,
        min_content_length: int = 0,
        include_embeddings: bool = False,
    ) -> dict:
        """Search with advanced filters and composite ranking.

        Args:
            workspace_id: Workspace to search in
            query: Search query (text-based full-text search)
            top_k: Max results to return
            providers: Filter by source providers
            min_trust: Minimum trust score threshold
            created_after: ISO date string — only items fetched after this date
            created_before: ISO date string — only items fetched before this date
            min_content_length: Minimum content character length
            include_embeddings: Whether to include embedding vectors in results

        Returns:
            Dict with results, filters applied, and stats
        """
        # Build the WHERE clause dynamically
        conditions = [
            "workspace_id = :ws",
            "to_tsvector('english', coalesce(title, '') || ' ' || coalesce(content, '')) @@ plainto_tsquery('english', :query)",
        ]
        params = {"ws": workspace_id, "query": query}

        if providers:
            placeholders = ", ".join(f":p{i}" for i in range(len(providers)))
            conditions.append(f"source_provider IN ({placeholders})")
            for i, p in enumerate(providers):
                params[f"p{i}"] = p

        if min_trust > 0:
            conditions.append("source_trust_score >= :min_trust")
            params["min_trust"] = min_trust

        if created_after:
            conditions.append("fetched_at >= :created_after::timestamptz")
            params["created_after"] = created_after

        if created_before:
            conditions.append("fetched_at <= :created_before::timestamptz")
            params["created_before"] = created_before

        if min_content_length > 0:
            conditions.append("LENGTH(content) >= :min_content")
            params["min_content"] = min_content_length

        where_clause = " AND ".join(conditions)

        # Compute text rank + trust + recency as composite score
        # recency: items from last 7 days get 1.0, decays to 0.3 over 90 days
        fields = """
            id, source_url, source_provider, source_trust_score,
            title, author, published_at, fetched_at,
            content, summary, metadata,
            ts_rank_cd(
                to_tsvector('english', coalesce(title, '') || ' ' || coalesce(content, '')),
                plainto_tsquery('english', :query)
            ) AS text_rank
        """
        if include_embeddings:
            fields += ", embedding"

        params["limit"] = top_k * 2  # fetch more for re-ranking

        async with async_session_factory() as session:
            result = await session.execute(text(f"""
                SELECT {fields}
                FROM ai.knowledge_embeddings
                WHERE {where_clause}
                ORDER BY text_rank DESC
                LIMIT :limit
            """), params)
            rows = result.fetchall()

        # Compute composite score: 0.50 * text_rank + 0.30 * trust + 0.20 * recency
        now = datetime.now(UTC)
        results = []
        for row in rows:
            text_rank = row.text_rank or 0.0
            trust = row.source_trust_score or 0.5

            # Recency score: 1.0 if fetched today, decays to 0.3 over 90 days
            if row.fetched_at:
                age_days = max(0, (now - row.fetched_at.replace(tzinfo=UTC)).days)
                recency = max(0.3, 1.0 - (age_days / 90) * 0.7)
            else:
                recency = 0.3

            composite = 0.50 * min(text_rank, 1.0) + 0.30 * trust + 0.20 * recency

            item = {
                "id": row.id,
                "source_url": row.source_url,
                "provider": row.source_provider,
                "trust_score": trust,
                "title": row.title,
                "author": row.author,
                "published_at": row.published_at.isoformat() if row.published_at else None,
                "fetched_at": row.fetched_at.isoformat() if row.fetched_at else None,
                "content": row.content[:2000] if row.content else "",
                "summary": row.summary,
                "metadata": row.metadata,
                "text_rank": round(text_rank, 4),
                "recency_score": round(recency, 3),
                "composite_score": round(composite, 4),
            }
            if include_embeddings and hasattr(row, "embedding"):
                item["embedding"] = row.embedding
            results.append(item)

        # Sort by composite score
        results.sort(key=lambda x: x["composite_score"], reverse=True)
        results = results[:top_k]

        return {
            "query": query,
            "results": results,
            "total": len(results),
            "filters_applied": {
                "providers": providers,
                "min_trust": min_trust,
                "created_after": created_after,
                "created_before": created_before,
                "min_content_length": min_content_length,
            },
        }

    async def search_by_date_range(
        self,
        workspace_id: str,
        start_date: str,
        end_date: str,
        top_k: int = 20,
    ) -> list[dict]:
        """Get all knowledge items within a date range, sorted by fetch date."""
        async with async_session_factory() as session:
            result = await session.execute(text("""
                SELECT id, source_url, source_provider, title, fetched_at,
                       source_trust_score, LENGTH(content) as content_len
                FROM ai.knowledge_embeddings
                WHERE workspace_id = :ws
                  AND fetched_at >= :start::timestamptz
                  AND fetched_at <= :end::timestamptz
                ORDER BY fetched_at DESC
                LIMIT :limit
            """), {"ws": workspace_id, "start": start_date, "end": end_date, "limit": top_k})
            rows = result.fetchall()

        return [
            {
                "id": row.id,
                "url": row.source_url,
                "provider": row.source_provider,
                "title": row.title,
                "fetched_at": row.fetched_at.isoformat() if row.fetched_at else None,
                "trust_score": row.source_trust_score,
                "content_size": row.content_len,
            }
            for row in rows
        ]

    async def search_low_quality(
        self,
        workspace_id: str,
        top_k: int = 20,
    ) -> list[dict]:
        """Find the lowest quality knowledge items for review/removal."""
        async with async_session_factory() as session:
            result = await session.execute(text("""
                SELECT k.id, k.source_url, k.title, k.source_provider,
                       k.source_trust_score, k.fetched_at,
                       q.composite_score
                FROM ai.knowledge_embeddings k
                LEFT JOIN ai.knowledge_quality q ON q.item_id = k.id
                WHERE k.workspace_id = :ws
                ORDER BY COALESCE(q.composite_score, 0.5) ASC
                LIMIT :limit
            """), {"ws": workspace_id, "limit": top_k})
            rows = result.fetchall()

        return [
            {
                "id": row.id,
                "url": row.source_url,
                "title": row.title,
                "provider": row.source_provider,
                "trust_score": row.source_trust_score,
                "quality_score": row.composite_score,
                "fetched_at": row.fetched_at.isoformat() if row.fetched_at else None,
            }
            for row in rows
        ]
