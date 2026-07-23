"""Knowledge Store — PostgreSQL CRUD for knowledge embeddings."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime

from sqlalchemy import text

from app.infrastructure.db.database import async_session_factory

logger = logging.getLogger(__name__)


def _generate_id(workspace_id: str, source_url: str) -> str:
    """Generate deterministic ID from workspace + URL."""
    raw = f"{workspace_id}:{source_url}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


class KnowledgeStore:
    """Stores and retrieves knowledge embeddings from PostgreSQL."""

    async def store(
        self,
        workspace_id: str,
        source_url: str,
        source_provider: str,
        title: str,
        content: str,
        trust_score: float = 0.5,
        author: str | None = None,
        published_at: datetime | None = None,
        summary: str | None = None,
        embedding: list[float] | None = None,
        metadata: dict | None = None,
        source_type: str | None = None,
        original_filename: str | None = None,
        language: str | None = None,
    ) -> str:
        """Store a knowledge item. Returns the stored item ID."""
        item_id = _generate_id(workspace_id, source_url)
        embedding_str = json.dumps(embedding) if embedding else None

        async with async_session_factory() as session:
            await session.execute(
                text("""
                    INSERT INTO ai.knowledge_embeddings
                        (id, workspace_id, source_url, source_provider, source_trust_score,
                         title, author, published_at, fetched_at, content, summary,
                         embedding, metadata, created_at, source_type, original_filename, language)
                    VALUES
                        (:id, :workspace_id, :source_url, :source_provider, :trust_score,
                         :title, :author, :published_at, NOW(), :content, :summary,
                         :embedding, :metadata, NOW(), :source_type, :original_filename, :language)
                    ON CONFLICT (id) DO UPDATE SET
                        content = EXCLUDED.content,
                        summary = EXCLUDED.summary,
                        embedding = EXCLUDED.embedding,
                        fetched_at = NOW(),
                        source_trust_score = EXCLUDED.source_trust_score,
                        metadata = EXCLUDED.metadata,
                        source_type = EXCLUDED.source_type,
                        original_filename = EXCLUDED.original_filename,
                        language = EXCLUDED.language
                """),
                {
                    "id": item_id,
                    "workspace_id": workspace_id,
                    "source_url": source_url,
                    "source_provider": source_provider,
                    "trust_score": trust_score,
                    "title": title,
                    "author": author,
                    "published_at": published_at,
                    "content": content,
                    "summary": summary,
                    "embedding": embedding_str,
                    "metadata": json.dumps(metadata) if metadata else None,
                    "source_type": source_type,
                    "original_filename": original_filename,
                    "language": language,
                },
            )
            await session.commit()

        logger.info("Stored knowledge item %s for workspace %s", item_id, workspace_id)
        return item_id

    async def store_batch(
        self,
        workspace_id: str,
        items: list[dict],
    ) -> list[str]:
        """Store multiple knowledge items in batch."""
        ids = []
        for item in items:
            try:
                item_id = await self.store(
                    workspace_id=workspace_id,
                    source_url=item["source_url"],
                    source_provider=item["source_provider"],
                    title=item["title"],
                    content=item["content"],
                    trust_score=item.get("trust_score", 0.5),
                    author=item.get("author"),
                    summary=item.get("summary"),
                    embedding=item.get("embedding"),
                    metadata=item.get("metadata"),
                    source_type=item.get("source_type"),
                    original_filename=item.get("original_filename"),
                    language=item.get("language"),
                )
                ids.append(item_id)
            except Exception as e:
                logger.warning("Failed to store item %s: %s", item.get("source_url", "?"), e)
        return ids

    async def get(self, workspace_id: str, item_id: str) -> dict | None:
        """Get a single knowledge item by ID."""
        async with async_session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT id, workspace_id, source_url, source_provider, source_trust_score,
                           title, author, published_at, fetched_at, content, summary,
                           embedding, metadata, created_at, source_type, original_filename, language
                    FROM ai.knowledge_embeddings
                    WHERE workspace_id = :workspace_id AND id = :item_id
                """),
                {"workspace_id": workspace_id, "item_id": item_id},
            )
            row = result.mappings().first()

        if not row:
            return None

        return dict(row)

    async def list_items(
        self,
        workspace_id: str,
        limit: int = 20,
        offset: int = 0,
        source_type: str | None = None,
    ) -> list[dict]:
        """List knowledge items for a workspace."""
        query = """
            SELECT id, workspace_id, source_url, source_provider, source_trust_score,
                   title, author, fetched_at, content, summary, created_at,
                   source_type, original_filename, language
            FROM ai.knowledge_embeddings
            WHERE workspace_id = :workspace_id
        """
        params: dict = {"workspace_id": workspace_id, "limit": limit, "offset": offset}

        if source_type:
            query += " AND source_type = :source_type"
            params["source_type"] = source_type

        query += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"

        async with async_session_factory() as session:
            result = await session.execute(text(query), params)
            rows = result.mappings().all()

        return [dict(r) for r in rows]

    async def search_text(
        self,
        workspace_id: str,
        query: str,
        top_k: int = 10,
    ) -> list[dict]:
        """Full-text search knowledge items."""
        async with async_session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT id, workspace_id, source_url, source_provider, source_trust_score,
                           title, content, summary, fetched_at,
                           ts_rank_cd(to_tsvector('english', coalesce(title, '') || ' ' || coalesce(content, '')),
                                       plainto_tsquery('english', :query)) AS text_rank
                    FROM ai.knowledge_embeddings
                    WHERE workspace_id = :workspace_id
                      AND to_tsvector('english', coalesce(title, '') || ' ' || coalesce(content, ''))
                          @@ plainto_tsquery('english', :query)
                    ORDER BY text_rank DESC
                    LIMIT :top_k
                """),
                {"workspace_id": workspace_id, "query": query, "top_k": top_k},
            )
            rows = result.mappings().all()

        return [dict(r) for r in rows]

    async def delete(self, workspace_id: str, item_id: str) -> bool:
        """Delete a knowledge item."""
        async with async_session_factory() as session:
            result = await session.execute(
                text("""
                    DELETE FROM ai.knowledge_embeddings
                    WHERE workspace_id = :workspace_id AND id = :item_id
                """),
                {"workspace_id": workspace_id, "item_id": item_id},
            )
            await session.commit()
            return result.rowcount > 0

    async def delete_batch(self, workspace_id: str, item_ids: list[str]) -> int:
        """Delete multiple knowledge items."""
        if not item_ids:
            return 0
        async with async_session_factory() as session:
            result = await session.execute(
                text("""
                    DELETE FROM ai.knowledge_embeddings
                    WHERE workspace_id = :workspace_id AND id = ANY(:item_ids)
                """),
                {"workspace_id": workspace_id, "item_ids": item_ids},
            )
            await session.commit()
            return result.rowcount

    async def get_stats(self, workspace_id: str) -> dict:
        """Get knowledge base statistics for a workspace."""
        async with async_session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT
                        COUNT(*) AS total_items,
                        COUNT(DISTINCT source_url) AS unique_urls,
                        COUNT(DISTINCT source_provider) AS providers,
                        AVG(source_trust_score) AS avg_trust,
                        MIN(fetched_at) AS oldest,
                        MAX(fetched_at) AS newest,
                        source_type,
                        language
                    FROM ai.knowledge_embeddings
                    WHERE workspace_id = :workspace_id
                    GROUP BY source_type, language
                """),
                {"workspace_id": workspace_id},
            )
            rows = result.mappings().all()

        if not rows:
            return {
                "total_items": 0,
                "unique_urls": 0,
                "providers": 0,
                "avg_trust": 0.0,
                "oldest": None,
                "newest": None,
                "source_types": {},
                "languages": {},
            }

        # Aggregate
        total = sum(r["total_items"] for r in rows)
        urls = sum(r["unique_urls"] for r in rows)
        providers = sum(r["providers"] for r in rows)
        trusts = [r["avg_trust"] for r in rows if r["avg_trust"] is not None]
        avg_trust = sum(trusts) / len(trusts) if trusts else 0.0
        oldest = min((r["oldest"] for r in rows if r["oldest"]), default=None)
        newest = max((r["newest"] for r in rows if r["newest"]), default=None)

        source_types = {}
        languages = {}
        for r in rows:
            st = r["source_type"] or "web"
            lang = r["language"] or "unknown"
            source_types[st] = source_types.get(st, 0) + r["total_items"]
            languages[lang] = languages.get(lang, 0) + r["total_items"]

        return {
            "total_items": total,
            "unique_urls": urls,
            "providers": providers,
            "avg_trust": round(avg_trust, 3),
            "oldest": str(oldest) if oldest else None,
            "newest": str(newest) if newest else None,
            "source_types": source_types,
            "languages": languages,
        }

    async def get_item_count(self, workspace_id: str) -> int:
        """Get total item count for a workspace."""
        async with async_session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT COUNT(*) FROM ai.knowledge_embeddings
                    WHERE workspace_id = :workspace_id
                """),
                {"workspace_id": workspace_id},
            )
            return result.scalar() or 0

    async def get_stale_items(
        self,
        workspace_id: str,
        stale_days: int = 30,
        limit: int = 100,
    ) -> list[dict]:
        """Get items older than stale_days for refresh."""
        async with async_session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT id, source_url, source_provider, title, fetched_at
                    FROM ai.knowledge_embeddings
                    WHERE workspace_id = :workspace_id
                      AND fetched_at < NOW() - (:stale_days || ' days')::INTERVAL
                    ORDER BY fetched_at ASC
                    LIMIT :limit
                """),
                {"workspace_id": workspace_id, "stale_days": stale_days, "limit": limit},
            )
            rows = result.mappings().all()

        return [dict(r) for r in rows]
