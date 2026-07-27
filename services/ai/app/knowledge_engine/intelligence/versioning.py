"""Knowledge Versioning — tracks how knowledge changes over time.

When the same URL is re-indexed with updated content, the old version is
preserved as a historical version. This allows:
- Tracking how documentation evolves
- Reverting to previous versions
- Auditing knowledge freshness
"""

from __future__ import annotations

import logging

from sqlalchemy import text
from app.infrastructure.db.database import async_session_factory

logger = logging.getLogger(__name__)


class KnowledgeVersioning:
    """Tracks historical versions of knowledge items."""

    async def ensure_table(self):
        """Create version history table if it doesn't exist."""
        async with async_session_factory() as session:
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS ai.knowledge_versions (
                    id SERIAL PRIMARY KEY,
                    workspace_id VARCHAR NOT NULL,
                    item_id VARCHAR NOT NULL,
                    version INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    summary TEXT,
                    source_trust_score FLOAT,
                    snapshot_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    change_reason VARCHAR(100)
                )
            """))
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_kv_item
                ON ai.knowledge_versions(workspace_id, item_id, version DESC)
            """))
            await session.commit()

    async def snapshot_before_update(
        self,
        workspace_id: str,
        item_id: str,
        reason: str = "auto_update",
    ):
        """Save current version before updating an item."""
        await self.ensure_table()

        async with async_session_factory() as session:
            # Get current item
            result = await session.execute(text("""
                SELECT content, summary, source_trust_score
                FROM ai.knowledge_embeddings
                WHERE id = :item_id AND workspace_id = :ws
            """), {"item_id": item_id, "ws": workspace_id})
            row = result.fetchone()

            if not row:
                return

            # Get current max version
            ver_result = await session.execute(text("""
                SELECT COALESCE(MAX(version), 0) + 1 as next_ver
                FROM ai.knowledge_versions
                WHERE item_id = :item_id AND workspace_id = :ws
            """), {"item_id": item_id, "ws": workspace_id})
            next_ver = ver_result.fetchone().next_ver

            # Insert version snapshot
            await session.execute(text("""
                INSERT INTO ai.knowledge_versions
                    (workspace_id, item_id, version, content, summary,
                     source_trust_score, change_reason)
                VALUES
                    (:ws, :item_id, :version, :content, :summary,
                     :trust, :reason)
            """), {
                "ws": workspace_id,
                "item_id": item_id,
                "version": next_ver,
                "content": row.content,
                "summary": row.summary,
                "trust": row.source_trust_score,
                "reason": reason,
            })
            await session.commit()

        logger.info("Version snapshot saved: item=%s, v%d", item_id, next_ver)

    async def get_version_history(
        self,
        workspace_id: str,
        item_id: str,
        limit: int = 10,
    ) -> list[dict]:
        """Get version history for a knowledge item."""
        await self.ensure_table()

        async with async_session_factory() as session:
            result = await session.execute(text("""
                SELECT version, content, summary, source_trust_score,
                       snapshot_at, change_reason
                FROM ai.knowledge_versions
                WHERE workspace_id = :ws AND item_id = :item_id
                ORDER BY version DESC
                LIMIT :limit
            """), {"ws": workspace_id, "item_id": item_id, "limit": limit})
            rows = result.fetchall()

        return [
            {
                "version": row.version,
                "content_preview": row.content[:300] if row.content else "",
                "summary": row.summary,
                "trust_score": row.source_trust_score,
                "snapshot_at": row.snapshot_at.isoformat() if row.snapshot_at else None,
                "reason": row.change_reason,
            }
            for row in rows
        ]

    async def revert_to_version(
        self,
        workspace_id: str,
        item_id: str,
        version: int,
    ) -> bool:
        """Revert a knowledge item to a previous version."""
        await self.ensure_table()

        async with async_session_factory() as session:
            result = await session.execute(text("""
                SELECT content, summary, source_trust_score
                FROM ai.knowledge_versions
                WHERE workspace_id = :ws AND item_id = :item_id AND version = :version
            """), {"ws": workspace_id, "item_id": item_id, "version": version})
            row = result.fetchone()

            if not row:
                return False

            # Snapshot current before reverting
            await self.snapshot_before_update(workspace_id, item_id, reason="before_revert")

            # Apply reverted version
            await session.execute(text("""
                UPDATE ai.knowledge_embeddings
                SET content = :content, summary = :summary,
                    source_trust_score = :trust, fetched_at = NOW()
                WHERE id = :item_id AND workspace_id = :ws
            """), {
                "content": row.content,
                "summary": row.summary,
                "trust": row.source_trust_score,
                "item_id": item_id,
                "ws": workspace_id,
            })
            await session.commit()

        logger.info("Reverted item %s to version %d", item_id, version)
        return True

    async def get_version_stats(self, workspace_id: str) -> dict:
        """Get versioning statistics for a workspace."""
        await self.ensure_table()

        async with async_session_factory() as session:
            result = await session.execute(text("""
                SELECT
                    COUNT(DISTINCT item_id) as versioned_items,
                    COUNT(*) as total_versions,
                    MAX(version) as max_version,
                    MIN(snapshot_at) as oldest_snapshot,
                    MAX(snapshot_at) as newest_snapshot
                FROM ai.knowledge_versions
                WHERE workspace_id = :ws
            """), {"ws": workspace_id})
            row = result.fetchone()

        return {
            "versioned_items": row.versioned_items or 0,
            "total_versions": row.total_versions or 0,
            "max_version": row.max_version or 0,
            "oldest_snapshot": row.oldest_snapshot.isoformat() if row.oldest_snapshot else None,
            "newest_snapshot": row.newest_snapshot.isoformat() if row.newest_snapshot else None,
        }
