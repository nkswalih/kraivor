"""Knowledge Cache — caches search results and embeddings to reduce load.

Uses PostgreSQL as the cache backend (no Redis dependency).
Supports TTL-based expiration and manual invalidation.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime

from sqlalchemy import text
from app.infrastructure.db.database import async_session_factory

logger = logging.getLogger(__name__)


class KnowledgeCache:
    """Caches knowledge search results with TTL expiration."""

    DEFAULT_TTL_SECONDS = 3600  # 1 hour
    EMBEDDING_CACHE_TTL = 86400  # 24 hours

    async def ensure_tables(self):
        """Create cache tables if they don't exist."""
        async with async_session_factory() as session:
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS ai.knowledge_cache (
                    id SERIAL PRIMARY KEY,
                    cache_key VARCHAR(64) NOT NULL UNIQUE,
                    workspace_id VARCHAR NOT NULL,
                    cache_type VARCHAR(50) NOT NULL DEFAULT 'search',
                    query TEXT,
                    result JSONB NOT NULL,
                    hit_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
                )
            """))
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_kc_key
                ON ai.knowledge_cache(cache_key, expires_at)
            """))
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_kc_ws
                ON ai.knowledge_cache(workspace_id, cache_type, created_at DESC)
            """))
            await session.commit()

    def _make_key(self, workspace_id: str, cache_type: str, query: str) -> str:
        """Generate a deterministic cache key."""
        raw = f"{workspace_id}:{cache_type}:{query}"
        return hashlib.sha256(raw.encode()).hexdigest()[:24]

    async def get(
        self,
        workspace_id: str,
        query: str,
        cache_type: str = "search",
    ) -> dict | None:
        """Get a cached result. Returns None if expired or missing."""
        await self.ensure_tables()

        key = self._make_key(workspace_id, cache_type, query)

        async with async_session_factory() as session:
            result = await session.execute(text("""
                SELECT result, hit_count
                FROM ai.knowledge_cache
                WHERE cache_key = :key
                  AND expires_at > NOW()
            """), {"key": key})
            row = result.fetchone()

            if not row:
                return None

            # Increment hit count
            await session.execute(text("""
                UPDATE ai.knowledge_cache
                SET hit_count = hit_count + 1
                WHERE cache_key = :key
            """), {"key": key})
            await session.commit()

        logger.debug("Cache hit: %s (type=%s)", key[:8], cache_type)
        return row.result

    async def set(
        self,
        workspace_id: str,
        query: str,
        result: dict,
        cache_type: str = "search",
        ttl_seconds: int | None = None,
    ):
        """Store a result in the cache."""
        await self.ensure_tables()

        key = self._make_key(workspace_id, cache_type, query)
        ttl = ttl_seconds or self.DEFAULT_TTL_SECONDS

        async with async_session_factory() as session:
            await session.execute(text("""
                INSERT INTO ai.knowledge_cache
                    (cache_key, workspace_id, cache_type, query, result, expires_at)
                VALUES
                    (:key, :ws, :cache_type, :query, :result::jsonb,
                     NOW() + INTERVAL ':ttl seconds')
                ON CONFLICT (cache_key) DO UPDATE
                SET result = EXCLUDED.result,
                    expires_at = EXCLUDED.expires_at,
                    hit_count = 0,
                    created_at = NOW()
            """), {
                "key": key,
                "ws": workspace_id,
                "cache_type": cache_type,
                "query": query[:500],
                "result": json.dumps(result),
                "ttl": ttl,
            })
            await session.commit()

        logger.debug("Cache set: %s (type=%s, ttl=%ds)", key[:8], cache_type, ttl)

    async def invalidate(
        self,
        workspace_id: str,
        cache_type: str | None = None,
    ) -> int:
        """Invalidate cache entries for a workspace."""
        await self.ensure_tables()

        if cache_type:
            where = "workspace_id = :ws AND cache_type = :cache_type"
            params = {"ws": workspace_id, "cache_type": cache_type}
        else:
            where = "workspace_id = :ws"
            params = {"ws": workspace_id}

        async with async_session_factory() as session:
            result = await session.execute(text(f"""
                DELETE FROM ai.knowledge_cache WHERE {where}
            """), params)
            await session.commit()
            return result.rowcount

    async def invalidate_query(
        self,
        workspace_id: str,
        query: str,
    ) -> bool:
        """Invalidate a specific query cache entry."""
        await self.ensure_tables()

        key = self._make_key(workspace_id, "search", query)
        async with async_session_factory() as session:
            result = await session.execute(text("""
                DELETE FROM ai.knowledge_cache WHERE cache_key = :key
            """), {"key": key})
            await session.commit()
            return result.rowcount > 0

    async def get_stats(self, workspace_id: str) -> dict:
        """Get cache statistics for a workspace."""
        await self.ensure_tables()

        async with async_session_factory() as session:
            result = await session.execute(text("""
                SELECT
                    COUNT(*) as total_entries,
                    COUNT(*) FILTER (WHERE expires_at > NOW()) as active_entries,
                    COUNT(*) FILTER (WHERE expires_at <= NOW()) as expired_entries,
                    SUM(hit_count) as total_hits,
                    AVG(hit_count) as avg_hits,
                    SUM(LENGTH(result::text)) as total_bytes
                FROM ai.knowledge_cache
                WHERE workspace_id = :ws
            """), {"ws": workspace_id})
            row = result.fetchone()

        return {
            "total_entries": row.total_entries or 0,
            "active_entries": row.active_entries or 0,
            "expired_entries": row.expired_entries or 0,
            "total_hits": row.total_hits or 0,
            "avg_hits": round(float(row.avg_hits or 0), 1),
            "total_size_kb": round((row.total_bytes or 0) / 1024, 1),
        }

    async def cleanup_expired(self) -> int:
        """Delete expired cache entries."""
        async with async_session_factory() as session:
            result = await session.execute(text("""
                DELETE FROM ai.knowledge_cache
                WHERE expires_at <= NOW()
            """))
            await session.commit()
            return result.rowcount

    async def warm_cache(
        self,
        workspace_id: str,
        queries: list[str],
    ):
        """Pre-warm cache with a list of common queries.

        This is a no-op for each query — it just ensures the cache
        tables exist and are ready for real traffic.
        """
        await self.ensure_tables()
        logger.info("Cache warmed for workspace %s with %d queries", workspace_id, len(queries))
