"""Knowledge Metrics — tracks query latency, source reliability, cache hit rates, and usage patterns.

All metrics are stored in PostgreSQL and can be queried via the monitoring API.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import text
from app.infrastructure.db.database import async_session_factory

logger = logging.getLogger(__name__)


@dataclass
class QueryMetric:
    """A single query metric event."""
    query: str
    workspace_id: str
    latency_ms: float
    source_count: int
    cache_hit: bool
    provider: str = "unknown"
    success: bool = True
    error: str | None = None


class KnowledgeMetrics:
    """Tracks and queries knowledge engine performance metrics."""

    async def ensure_tables(self):
        """Create metrics tables if they don't exist."""
        async with async_session_factory() as session:
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS ai.knowledge_metrics (
                    id SERIAL PRIMARY KEY,
                    workspace_id VARCHAR NOT NULL,
                    event_type VARCHAR(50) NOT NULL,
                    query TEXT,
                    latency_ms FLOAT,
                    source_count INTEGER DEFAULT 0,
                    cache_hit BOOLEAN DEFAULT FALSE,
                    provider VARCHAR(100),
                    success BOOLEAN DEFAULT TRUE,
                    error TEXT,
                    metadata JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_km_ws_type
                ON ai.knowledge_metrics(workspace_id, event_type, created_at DESC)
            """))
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_km_created
                ON ai.knowledge_metrics(created_at DESC)
            """))
            await session.commit()

    async def record_query(self, metric: QueryMetric):
        """Record a query metric event."""
        await self.ensure_tables()

        event_type = "cache_hit" if metric.cache_hit else "query"
        async with async_session_factory() as session:
            await session.execute(text("""
                INSERT INTO ai.knowledge_metrics
                    (workspace_id, event_type, query, latency_ms, source_count,
                     cache_hit, provider, success, error)
                VALUES
                    (:ws, :event_type, :query, :latency, :sources,
                     :cache_hit, :provider, :success, :error)
            """), {
                "ws": metric.workspace_id,
                "event_type": event_type,
                "query": metric.query[:500],
                "latency": metric.latency_ms,
                "sources": metric.source_count,
                "cache_hit": metric.cache_hit,
                "provider": metric.provider,
                "success": metric.success,
                "error": metric.error,
            })
            await session.commit()

    async def record_event(
        self,
        workspace_id: str,
        event_type: str,
        metadata: dict | None = None,
    ):
        """Record a generic event (index, dedup, feedback, etc.)."""
        await self.ensure_tables()

        async with async_session_factory() as session:
            await session.execute(text("""
                INSERT INTO ai.knowledge_metrics
                    (workspace_id, event_type, metadata)
                VALUES
                    (:ws, :event_type, :meta::jsonb)
            """), {
                "ws": workspace_id,
                "event_type": event_type,
                "meta": str(metadata) if metadata else None,
            })
            await session.commit()

    async def get_query_stats(
        self,
        workspace_id: str,
        hours: int = 24,
    ) -> dict:
        """Get query performance statistics for the last N hours."""
        await self.ensure_tables()

        async with async_session_factory() as session:
            result = await session.execute(text("""
                SELECT
                    COUNT(*) as total_queries,
                    COUNT(*) FILTER (WHERE cache_hit = TRUE) as cache_hits,
                    COUNT(*) FILTER (WHERE success = FALSE) as errors,
                    AVG(latency_ms) as avg_latency,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY latency_ms) as p50_latency,
                    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) as p95_latency,
                    MAX(latency_ms) as max_latency,
                    SUM(source_count) as total_sources_fetched
                FROM ai.knowledge_metrics
                WHERE workspace_id = :ws
                  AND event_type IN ('query', 'cache_hit')
                  AND created_at > NOW() - INTERVAL ':hours hours'
            """), {"ws": workspace_id, "hours": hours})
            row = result.fetchone()

        total = row.total_queries or 1
        cache_hits = row.cache_hits or 0

        return {
            "total_queries": row.total_queries or 0,
            "cache_hits": cache_hits,
            "cache_hit_rate": round(cache_hits / max(total, 1), 3),
            "errors": row.errors or 0,
            "error_rate": round((row.errors or 0) / max(total, 1), 3),
            "avg_latency_ms": round(float(row.avg_latency or 0), 1),
            "p50_latency_ms": round(float(row.p50_latency or 0), 1),
            "p95_latency_ms": round(float(row.p95_latency or 0), 1),
            "max_latency_ms": round(float(row.max_latency or 0), 1),
            "total_sources_fetched": row.total_sources_fetched or 0,
            "period_hours": hours,
        }

    async def get_source_reliability(
        self,
        workspace_id: str,
        hours: int = 168,
    ) -> list[dict]:
        """Get reliability stats per source provider."""
        await self.ensure_tables()

        async with async_session_factory() as session:
            result = await session.execute(text("""
                SELECT
                    provider,
                    COUNT(*) as queries,
                    AVG(latency_ms) as avg_latency,
                    COUNT(*) FILTER (WHERE success = FALSE) as errors
                FROM ai.knowledge_metrics
                WHERE workspace_id = :ws
                  AND event_type = 'query'
                  AND created_at > NOW() - INTERVAL ':hours hours'
                GROUP BY provider
                ORDER BY queries DESC
            """), {"ws": workspace_id, "hours": hours})
            rows = result.fetchall()

        return [
            {
                "provider": row.provider,
                "queries": row.queries,
                "avg_latency_ms": round(float(row.avg_latency or 0), 1),
                "errors": row.errors,
                "reliability": round(1.0 - (row.errors / max(row.queries, 1)), 3),
            }
            for row in rows
        ]

    async def get_usage_timeline(
        self,
        workspace_id: str,
        hours: int = 24,
        bucket_minutes: int = 60,
    ) -> list[dict]:
        """Get query volume over time in time buckets."""
        await self.ensure_tables()

        async with async_session_factory() as session:
            result = await session.execute(text("""
                SELECT
                    date_trunc('hour', created_at
                        - (EXTRACT(minute FROM created_at)::int % :bucket) * INTERVAL '1 minute'
                    ) as bucket,
                    COUNT(*) as queries,
                    COUNT(*) FILTER (WHERE cache_hit = TRUE) as cache_hits,
                    AVG(latency_ms) as avg_latency
                FROM ai.knowledge_metrics
                WHERE workspace_id = :ws
                  AND event_type IN ('query', 'cache_hit')
                  AND created_at > NOW() - INTERVAL ':hours hours'
                GROUP BY bucket
                ORDER BY bucket ASC
            """), {"ws": workspace_id, "hours": hours, "bucket": bucket_minutes})
            rows = result.fetchall()

        return [
            {
                "bucket": row.bucket.isoformat() if row.bucket else None,
                "queries": row.queries,
                "cache_hits": row.cache_hits,
                "avg_latency_ms": round(float(row.avg_latency or 0), 1),
            }
            for row in rows
        ]

    async def get_top_queries(
        self,
        workspace_id: str,
        limit: int = 10,
        hours: int = 168,
    ) -> list[dict]:
        """Get most frequently asked queries."""
        await self.ensure_tables()

        async with async_session_factory() as session:
            result = await session.execute(text("""
                SELECT
                    query,
                    COUNT(*) as count,
                    AVG(latency_ms) as avg_latency,
                    AVG(source_count) as avg_sources
                FROM ai.knowledge_metrics
                WHERE workspace_id = :ws
                  AND event_type = 'query'
                  AND query IS NOT NULL
                  AND created_at > NOW() - INTERVAL ':hours hours'
                GROUP BY query
                ORDER BY count DESC
                LIMIT :limit
            """), {"ws": workspace_id, "hours": hours, "limit": limit})
            rows = result.fetchall()

        return [
            {
                "query": row.query[:200],
                "count": row.count,
                "avg_latency_ms": round(float(row.avg_latency or 0), 1),
                "avg_sources": round(float(row.avg_sources or 0), 1),
            }
            for row in rows
        ]

    async def cleanup_old_metrics(self, days: int = 30) -> int:
        """Delete metrics older than N days."""
        async with async_session_factory() as session:
            result = await session.execute(text("""
                DELETE FROM ai.knowledge_metrics
                WHERE created_at < NOW() - INTERVAL ':days days'
            """), {"days": days})
            await session.commit()
            return result.rowcount
