"""Knowledge Quality Scoring — tracks usefulness and relevance of stored knowledge.

Measures:
1. Reference count: how often an item is retrieved in responses
2. Retrieval rank: position in search results when queried
3. Freshness penalty: older items score lower
4. Source trust: high-trust sources score higher
5. Content quality: well-structured content scores higher
6. Composite quality score: weighted combination of all signals
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import text

from app.infrastructure.db.database import async_session_factory

logger = logging.getLogger(__name__)


class KnowledgeQualityScorer:
    """Tracks and computes quality scores for knowledge items."""

    # Weight constants for composite scoring
    W_REFERENCE = 0.30
    W_FRESHNESS = 0.20
    W_TRUST = 0.25
    W_CONTENT = 0.15
    W_RANK = 0.10

    async def ensure_table(self):
        """Create quality tracking table if it doesn't exist."""
        async with async_session_factory() as session:
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS ai.knowledge_quality (
                    item_id VARCHAR PRIMARY KEY,
                    workspace_id VARCHAR NOT NULL,
                    reference_count INTEGER DEFAULT 0,
                    total_rank NUMERIC DEFAULT 0.0,
                    avg_rank NUMERIC DEFAULT 0.0,
                    last_referenced_at TIMESTAMP WITH TIME ZONE,
                    content_quality_score FLOAT DEFAULT 0.0,
                    composite_score FLOAT DEFAULT 0.0,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_kq_workspace
                ON ai.knowledge_quality(workspace_id, composite_score DESC)
            """))
            await session.commit()

    async def record_reference(
        self,
        item_id: str,
        workspace_id: str,
        rank: int = 1,
    ):
        """Record that a knowledge item was referenced in a response."""
        async with async_session_factory() as session:
            await session.execute(text("""
                INSERT INTO ai.knowledge_quality
                    (item_id, workspace_id, reference_count, total_rank, avg_rank,
                     last_referenced_at, updated_at)
                VALUES
                    (:item_id, :ws, 1, :rank, :rank, NOW(), NOW())
                ON CONFLICT (item_id) DO UPDATE SET
                    reference_count = ai.knowledge_quality.reference_count + 1,
                    total_rank = ai.knowledge_quality.total_rank + :rank,
                    avg_rank = (ai.knowledge_quality.total_rank + :rank) /
                               (ai.knowledge_quality.reference_count + 1),
                    last_referenced_at = NOW(),
                    updated_at = NOW()
            """), {"item_id": item_id, "ws": workspace_id, "rank": rank})
            await session.commit()

    async def compute_content_quality(self, content: str) -> float:
        """Score content quality based on structure analysis."""
        if not content:
            return 0.0

        score = 0.5  # baseline

        # Length bonus (information-rich content)
        length = len(content)
        if length > 500:
            score += 0.1
        if length > 1500:
            score += 0.1

        # Structure bonuses
        if "##" in content or "###" in content:  # Headings
            score += 0.05
        if "```" in content:  # Code blocks
            score += 0.05
        if "|" in content and "---" in content:  # Tables
            score += 0.05
        if "- " in content or "* " in content:  # Lists
            score += 0.05

        # Penalties
        if content.lower().startswith("no ") or content.lower().startswith("sorry"):
            score -= 0.1
        if content.count("!") > 3:  # Excessive exclamation
            score -= 0.05

        return max(0.0, min(1.0, score))

    async def update_composite_score(self, item_id: str, workspace_id: str):
        """Recompute the composite quality score for a knowledge item."""
        async with async_session_factory() as session:
            # Get quality data
            result = await session.execute(text("""
                SELECT q.reference_count, q.avg_rank, q.content_quality_score
                FROM ai.knowledge_quality q
                WHERE q.item_id = :item_id
            """), {"item_id": item_id})
            quality_row = result.fetchone()

            # Get item metadata
            result = await session.execute(text("""
                SELECT source_trust_score, fetched_at
                FROM ai.knowledge_embeddings
                WHERE id = :item_id
            """), {"item_id": item_id})
            item_row = result.fetchone()

            if not quality_row or not item_row:
                return

            # Reference score (log-scaled, max at 50 references)
            import math
            ref_score = min(1.0, math.log1p(quality_row.reference_count) / math.log1p(50))

            # Freshness score (exponential decay, 50% per 30 days)
            if item_row.fetched_at:
                days_old = (datetime.now(UTC) - item_row.fetched_at).days
                freshness = 0.5 ** (days_old / 30)
            else:
                freshness = 0.5

            # Trust score
            trust = item_row.source_trust_score or 0.5

            # Content quality
            content_q = quality_row.content_quality_score or 0.5

            # Rank score (lower rank = better, max 10)
            rank_score = max(0, 1.0 - (float(quality_row.avg_rank or 5) / 10))

            # Composite
            composite = (
                self.W_REFERENCE * ref_score
                + self.W_FRESHNESS * freshness
                + self.W_TRUST * trust
                + self.W_CONTENT * content_q
                + self.W_RANK * rank_score
            )

            await session.execute(text("""
                UPDATE ai.knowledge_quality
                SET composite_score = :composite, updated_at = NOW()
                WHERE item_id = :item_id
            """), {"composite": round(composite, 4), "item_id": item_id})
            await session.commit()

    async def get_top_quality(
        self,
        workspace_id: str,
        limit: int = 10,
    ) -> list[dict]:
        """Get the highest quality knowledge items for a workspace."""
        async with async_session_factory() as session:
            result = await session.execute(text("""
                SELECT q.item_id, q.reference_count, q.avg_rank, q.composite_score,
                       k.title, k.source_url, k.source_provider, k.source_trust_score
                FROM ai.knowledge_quality q
                JOIN ai.knowledge_embeddings k ON k.id = q.item_id
                WHERE q.workspace_id = :ws
                ORDER BY q.composite_score DESC
                LIMIT :limit
            """), {"ws": workspace_id, "limit": limit})
            rows = result.fetchall()

        return [
            {
                "item_id": row.item_id,
                "title": row.title,
                "url": row.source_url,
                "provider": row.source_provider,
                "trust_score": row.source_trust_score,
                "references": row.reference_count,
                "avg_rank": round(float(row.avg_rank or 0), 2),
                "quality_score": round(float(row.composite_score or 0), 4),
            }
            for row in rows
        ]

    async def get_quality_stats(self, workspace_id: str) -> dict:
        """Get quality statistics for a workspace."""
        async with async_session_factory() as session:
            result = await session.execute(text("""
                SELECT
                    COUNT(*) as total_tracked,
                    AVG(composite_score) as avg_quality,
                    MAX(composite_score) as max_quality,
                    SUM(reference_count) as total_references,
                    AVG(reference_count) as avg_references
                FROM ai.knowledge_quality
                WHERE workspace_id = :ws
            """), {"ws": workspace_id})
            row = result.fetchone()

        return {
            "total_tracked": row.total_tracked or 0,
            "avg_quality": round(float(row.avg_quality or 0), 4),
            "max_quality": round(float(row.max_quality or 0), 4),
            "total_references": row.total_references or 0,
            "avg_references": round(float(row.avg_references or 0), 2),
        }

    async def initialize_item(self, item_id: str, workspace_id: str, content: str):
        """Initialize quality tracking for a new knowledge item."""
        content_score = await self.compute_content_quality(content)

        async with async_session_factory() as session:
            await session.execute(text("""
                INSERT INTO ai.knowledge_quality
                    (item_id, workspace_id, content_quality_score, composite_score)
                VALUES
                    (:item_id, :ws, :score, :score)
                ON CONFLICT (item_id) DO NOTHING
            """), {"item_id": item_id, "ws": workspace_id, "score": round(content_score, 4)})
            await session.commit()
