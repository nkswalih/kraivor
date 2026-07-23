"""Semantic Deduplication — detects near-duplicate content across knowledge sources.

Goes beyond URL matching to find:
- Same content published on different URLs
- Near-identical documentation from different versions
- Reprinted/translated versions of the same article
"""

from __future__ import annotations

import hashlib
import logging
import re
from collections import defaultdict

from sqlalchemy import text
from app.infrastructure.db.database import async_session_factory

logger = logging.getLogger(__name__)


class SemanticDeduplicator:
    """Detects and merges near-duplicate knowledge items."""

    # Similarity threshold for considering items as duplicates
    SIMILARITY_THRESHOLD = 0.85

    async def find_duplicates(
        self,
        workspace_id: str,
        threshold: float | None = None,
    ) -> list[dict]:
        """Find groups of near-duplicate items in the workspace."""
        threshold = threshold or self.SIMILARITY_THRESHOLD

        # Fetch all items with embeddings
        items = await self._fetch_items_with_embeddings(workspace_id)
        if len(items) < 2:
            return []

        # Compare each pair
        groups = []
        used = set()

        for i, item_a in enumerate(items):
            if i in used:
                continue

            duplicates = [item_a]
            emb_a = item_a.get("embedding_list")

            for j, item_b in enumerate(items):
                if j <= i or j in used:
                    continue

                emb_b = item_b.get("embedding_list")
                if emb_a and emb_b:
                    sim = self._cosine_similarity(emb_a, emb_b)
                    if sim >= threshold:
                        duplicates.append(item_b)
                        used.add(j)

            if len(duplicates) >= 2:
                used.add(i)
                # Pick the best one to keep (highest trust score)
                best = max(duplicates, key=lambda x: x.get("trust_score", 0))
                groups.append({
                    "keep": best,
                    "remove": [d for d in duplicates if d["id"] != best["id"]],
                    "similarity": threshold,
                    "count": len(duplicates),
                })

        return groups

    async def deduplicate_workspace(
        self,
        workspace_id: str,
        dry_run: bool = True,
    ) -> dict:
        """Find and optionally remove duplicates from a workspace."""
        groups = await self.find_duplicates(workspace_id)

        removed = 0
        for group in groups:
            if not dry_run:
                for item in group["remove"]:
                    await self._remove_item(workspace_id, item["id"])
                    removed += 1

        return {
            "duplicate_groups": len(groups),
            "items_to_remove": sum(len(g["remove"]) for g in groups),
            "items_removed": removed,
            "dry_run": dry_run,
        }

    async def _fetch_items_with_embeddings(
        self, workspace_id: str
    ) -> list[dict]:
        """Fetch knowledge items with their embeddings."""
        async with async_session_factory() as session:
            result = await session.execute(text("""
                SELECT id, title, source_url, source_provider,
                       source_trust_score, embedding, content
                FROM ai.knowledge_embeddings
                WHERE workspace_id = :ws
                  AND embedding IS NOT NULL
                ORDER BY fetched_at DESC
                LIMIT 200
            """), {"ws": workspace_id})
            rows = result.fetchall()

        import json
        items = []
        for row in rows:
            emb_list = None
            if row.embedding:
                try:
                    emb_list = json.loads(row.embedding)
                except (json.JSONDecodeError, TypeError):
                    pass

            items.append({
                "id": row.id,
                "title": row.title,
                "url": row.source_url,
                "provider": row.source_provider,
                "trust_score": row.source_trust_score,
                "content_preview": row.content[:200] if row.content else "",
                "embedding_list": emb_list,
            })

        return items

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if len(a) != len(b):
            # Truncate to shorter
            min_len = min(len(a), len(b))
            a, b = a[:min_len], b[:min_len]

        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    async def _remove_item(self, workspace_id: str, item_id: str):
        """Remove a duplicate knowledge item."""
        async with async_session_factory() as session:
            await session.execute(text("""
                DELETE FROM ai.knowledge_embeddings
                WHERE id = :item_id AND workspace_id = :ws
            """), {"item_id": item_id, "ws": workspace_id})
            await session.commit()

        logger.info("Removed duplicate item: %s", item_id)
