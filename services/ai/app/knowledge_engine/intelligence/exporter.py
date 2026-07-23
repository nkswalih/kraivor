"""Knowledge Export — exports workspace knowledge as structured JSON for backup/portability."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from sqlalchemy import text
from app.infrastructure.db.database import async_session_factory

logger = logging.getLogger(__name__)


class KnowledgeExporter:
    """Exports workspace knowledge as structured JSON."""

    async def export_workspace(
        self,
        workspace_id: str,
        include_embeddings: bool = False,
        include_versions: bool = False,
        include_feedback: bool = False,
        include_graph: bool = False,
    ) -> dict:
        """Export all knowledge for a workspace as a structured dict."""
        export = {
            "version": "1.0",
            "workspace_id": workspace_id,
            "exported_at": datetime.now(UTC).isoformat(),
            "items": [],
        }

        # Fetch all items
        items = await self._fetch_items(workspace_id, include_embeddings)
        export["items"] = items
        export["item_count"] = len(items)

        # Optional: include graph data
        if include_graph:
            export["graph"] = await self._export_graph(workspace_id)

        # Optional: include version history
        if include_versions:
            export["versions"] = await self._export_versions(workspace_id)

        # Optional: include feedback data
        if include_feedback:
            export["feedback"] = await self._export_feedback(workspace_id)

        # Summary stats
        export["stats"] = await self._compute_export_stats(workspace_id)

        return export

    async def export_as_json(
        self,
        workspace_id: str,
        **kwargs,
    ) -> str:
        """Export workspace knowledge as a JSON string."""
        data = await self.export_workspace(workspace_id, **kwargs)
        return json.dumps(data, indent=2, default=str)

    async def _fetch_items(
        self, workspace_id: str, include_embeddings: bool
    ) -> list[dict]:
        """Fetch all knowledge items."""
        fields = "id, source_url, source_provider, source_trust_score, title, author, published_at, fetched_at, content, summary, metadata"
        if include_embeddings:
            fields += ", embedding"

        async with async_session_factory() as session:
            result = await session.execute(text(f"""
                SELECT {fields}
                FROM ai.knowledge_embeddings
                WHERE workspace_id = :ws
                ORDER BY fetched_at DESC
            """), {"ws": workspace_id})
            rows = result.fetchall()

        items = []
        for row in rows:
            item = {
                "id": row.id,
                "source_url": row.source_url,
                "source_provider": row.source_provider,
                "trust_score": row.source_trust_score,
                "title": row.title,
                "author": row.author,
                "published_at": row.published_at.isoformat() if row.published_at else None,
                "fetched_at": row.fetched_at.isoformat() if row.fetched_at else None,
                "content": row.content,
                "summary": row.summary,
                "metadata": row.metadata,
            }
            if include_embeddings and hasattr(row, "embedding"):
                item["embedding"] = row.embedding
            items.append(item)

        return items

    async def _export_graph(self, workspace_id: str) -> dict:
        """Export knowledge graph data."""
        async with async_session_factory() as session:
            entities = await session.execute(text("""
                SELECT name, entity_type, mention_count
                FROM ai.knowledge_entities
                WHERE workspace_id = :ws
                ORDER BY mention_count DESC
            """), {"ws": workspace_id})
            entity_rows = entities.fetchall()

            rels = await session.execute(text("""
                SELECT source_entity, target_entity, relationship_type, weight, evidence_count
                FROM ai.knowledge_relationships
                WHERE workspace_id = :ws
            """), {"ws": workspace_id})
            rel_rows = rels.fetchall()

        return {
            "entities": [
                {"name": r.name, "type": r.entity_type, "mentions": r.mention_count}
                for r in entity_rows
            ],
            "relationships": [
                {
                    "source": r.source_entity,
                    "target": r.target_entity,
                    "type": r.relationship_type,
                    "weight": r.weight,
                    "evidence": r.evidence_count,
                }
                for r in rel_rows
            ],
        }

    async def _export_versions(self, workspace_id: str) -> list[dict]:
        """Export version history."""
        async with async_session_factory() as session:
            result = await session.execute(text("""
                SELECT item_id, version, content, summary, source_trust_score,
                       snapshot_at, change_reason
                FROM ai.knowledge_versions
                WHERE workspace_id = :ws
                ORDER BY item_id, version DESC
            """), {"ws": workspace_id})
            rows = result.fetchall()

        return [
            {
                "item_id": r.item_id,
                "version": r.version,
                "content_preview": r.content[:500] if r.content else "",
                "reason": r.change_reason,
                "snapshot_at": r.snapshot_at.isoformat() if r.snapshot_at else None,
            }
            for r in rows
        ]

    async def _export_feedback(self, workspace_id: str) -> list[dict]:
        """Export feedback data."""
        async with async_session_factory() as session:
            result = await session.execute(text("""
                SELECT item_id, rating, comment, created_at
                FROM ai.knowledge_feedback
                WHERE workspace_id = :ws
                ORDER BY created_at DESC
            """), {"ws": workspace_id})
            rows = result.fetchall()

        return [
            {
                "item_id": r.item_id,
                "rating": r.rating,
                "comment": r.comment,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]

    async def _compute_export_stats(self, workspace_id: str) -> dict:
        """Compute export statistics."""
        async with async_session_factory() as session:
            result = await session.execute(text("""
                SELECT
                    COUNT(*) as total_items,
                    COUNT(DISTINCT source_provider) as providers,
                    COUNT(DISTINCT source_url) as unique_urls,
                    AVG(source_trust_score) as avg_trust,
                    SUM(LENGTH(content)) as total_content_bytes
                FROM ai.knowledge_embeddings
                WHERE workspace_id = :ws
            """), {"ws": workspace_id})
            row = result.fetchone()

        return {
            "total_items": row.total_items or 0,
            "providers": row.providers or 0,
            "unique_urls": row.unique_urls or 0,
            "avg_trust": round(float(row.avg_trust or 0), 2),
            "total_content_kb": round((row.total_content_bytes or 0) / 1024, 1),
        }
