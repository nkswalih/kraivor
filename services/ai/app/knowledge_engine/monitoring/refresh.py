"""Knowledge Refresh Pipeline — automatically re-indexes stale knowledge.

When knowledge items get old, this pipeline:
1. Identifies stale items (older than configurable threshold)
2. Re-fetches content from source URLs
3. Updates the stored knowledge with fresh content
4. Snapshots the old version before updating
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from app.infrastructure.db.database import async_session_factory

logger = logging.getLogger(__name__)


class KnowledgeRefreshPipeline:
    """Identifies and refreshes stale knowledge items."""

    STALE_THRESHOLD_DAYS = 30
    MAX_REFRESH_PER_RUN = 20
    REFRESH_PROVIDERS = {"web", "docs", "github", "news", "package_registry"}

    async def identify_stale_items(
        self,
        workspace_id: str,
        stale_days: int | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """Find knowledge items that are older than the stale threshold."""
        threshold = stale_days or self.STALE_THRESHOLD_DAYS
        max_items = limit or self.MAX_REFRESH_PER_RUN

        async with async_session_factory() as session:
            result = await session.execute(text("""
                SELECT id, source_url, source_provider, title, fetched_at,
                       source_trust_score, LENGTH(content) as content_len
                FROM ai.knowledge_embeddings
                WHERE workspace_id = :ws
                  AND source_provider IN ('web', 'docs', 'github', 'news', 'package_registry')
                  AND fetched_at < NOW() - INTERVAL ':threshold days'
                  AND source_url NOT LIKE 'canvas://%%'
                  AND source_url NOT LIKE 'conversation://%%'
                ORDER BY fetched_at ASC
                LIMIT :limit
            """), {"ws": workspace_id, "threshold": threshold, "limit": max_items})
            rows = result.fetchall()

        return [
            {
                "id": row.id,
                "source_url": row.source_url,
                "provider": row.source_provider,
                "title": row.title,
                "fetched_at": row.fetched_at.isoformat() if row.fetched_at else None,
                "trust_score": row.source_trust_score,
                "content_size": row.content_len,
            }
            for row in rows
        ]

    async def refresh_item(
        self,
        workspace_id: str,
        item_id: str,
        source_url: str,
    ) -> dict:
        """Re-fetch and update a single knowledge item."""
        from app.knowledge_engine.store.knowledge_indexer import KnowledgeIndexer
        from app.knowledge_engine.intelligence.versioning import KnowledgeVersioning

        start = time.time()

        # Snapshot before update
        try:
            versioning = KnowledgeVersioning()
            await versioning.snapshot_before_update(workspace_id, item_id, reason="auto_refresh")
        except Exception as e:
            logger.debug("Version snapshot failed for %s: %s", item_id, e)

        # Fetch fresh content
        try:
            from app.knowledge_engine.engine import KnowledgeEngine
            engine = KnowledgeEngine()
            content = await engine.fetch(source_url)

            if not content or not content.text:
                return {
                    "id": item_id,
                    "status": "fetch_failed",
                    "error": "No content returned",
                    "latency_ms": round((time.time() - start) * 1000, 1),
                }

            # Update the stored item
            async with async_session_factory() as session:
                await session.execute(text("""
                    UPDATE ai.knowledge_embeddings
                    SET content = :content,
                        title = COALESCE(:title, title),
                        fetched_at = NOW()
                    WHERE id = :item_id AND workspace_id = :ws
                """), {
                    "content": content.text,
                    "title": content.title,
                    "item_id": item_id,
                    "ws": workspace_id,
                })
                await session.commit()

            latency = round((time.time() - start) * 1000, 1)
            logger.info("Refreshed item %s in %sms", item_id, latency)

            return {
                "id": item_id,
                "status": "refreshed",
                "title": content.title,
                "latency_ms": latency,
                "content_size": len(content.text),
            }

        except Exception as e:
            latency = round((time.time() - start) * 1000, 1)
            logger.warning("Refresh failed for %s: %s", item_id, e)
            return {
                "id": item_id,
                "status": "error",
                "error": str(e)[:200],
                "latency_ms": latency,
            }

    async def run_refresh_cycle(
        self,
        workspace_id: str,
        stale_days: int | None = None,
        max_items: int | None = None,
    ) -> dict:
        """Run a full refresh cycle: identify stale → re-fetch → update."""
        start = time.time()

        stale = await self.identify_stale_items(workspace_id, stale_days, max_items)

        if not stale:
            return {
                "workspace_id": workspace_id,
                "stale_found": 0,
                "refreshed": 0,
                "failed": 0,
                "total_latency_ms": 0,
                "status": "no_stale_items",
            }

        results = []
        for item in stale:
            result = await self.refresh_item(
                workspace_id,
                item["id"],
                item["source_url"],
            )
            results.append(result)

            # Small delay between refreshes to be polite to sources
            time.sleep(0.5)

        refreshed = sum(1 for r in results if r["status"] == "refreshed")
        failed = sum(1 for r in results if r["status"] in ("error", "fetch_failed"))
        total_latency = round((time.time() - start) * 1000, 1)

        return {
            "workspace_id": workspace_id,
            "stale_found": len(stale),
            "refreshed": refreshed,
            "failed": failed,
            "total_latency_ms": total_latency,
            "results": results,
            "status": "completed",
        }

    async def get_refresh_stats(self, workspace_id: str) -> dict:
        """Get refresh pipeline statistics."""
        threshold = self.STALE_THRESHOLD_DAYS

        async with async_session_factory() as session:
            result = await session.execute(text("""
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE fetched_at < NOW() - INTERVAL ':threshold days'
                        AND source_url NOT LIKE 'canvas://%%'
                        AND source_url NOT LIKE 'conversation://%%') as stale,
                    COUNT(*) FILTER (WHERE fetched_at > NOW() - INTERVAL '1 day') as refreshed_today,
                    COUNT(*) FILTER (WHERE fetched_at > NOW() - INTERVAL '7 days') as refreshed_week,
                    MIN(fetched_at) as oldest,
                    MAX(fetched_at) as newest
                FROM ai.knowledge_embeddings
                WHERE workspace_id = :ws
            """), {"ws": workspace_id, "threshold": threshold})
            row = result.fetchone()

        return {
            "total_items": row.total or 0,
            "stale_items": row.stale or 0,
            "refreshed_today": row.refreshed_today or 0,
            "refreshed_this_week": row.refreshed_week or 0,
            "oldest_item": row.oldest.isoformat() if row.oldest else None,
            "newest_item": row.newest.isoformat() if row.newest else None,
            "stale_threshold_days": threshold,
        }
