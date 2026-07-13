"""Feedback Loop — tracks user reactions to improve knowledge quality scores.

When users indicate a response was helpful/unhelpful, the feedback is recorded
and used to adjust quality scores for the knowledge items that were referenced.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import text
from app.infrastructure.db.database import async_session_factory

logger = logging.getLogger(__name__)


class FeedbackTracker:
    """Tracks user feedback on knowledge quality and adjusts scores."""

    async def ensure_table(self):
        """Create feedback tracking table if it doesn't exist."""
        async with async_session_factory() as session:
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS ai.knowledge_feedback (
                    id SERIAL PRIMARY KEY,
                    workspace_id VARCHAR NOT NULL,
                    item_id VARCHAR NOT NULL,
                    conversation_id VARCHAR,
                    rating VARCHAR(20) NOT NULL,
                    comment TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_kf_item
                ON ai.knowledge_feedback(workspace_id, item_id)
            """))
            await session.commit()

    async def record_feedback(
        self,
        workspace_id: str,
        item_id: str,
        rating: str,
        conversation_id: str | None = None,
        comment: str | None = None,
    ):
        """Record user feedback on a knowledge item.

        rating: 'helpful', 'not_helpful', 'partially_helpful', 'outdated', 'incorrect'
        """
        await self.ensure_table()

        async with async_session_factory() as session:
            await session.execute(text("""
                INSERT INTO ai.knowledge_feedback
                    (workspace_id, item_id, conversation_id, rating, comment)
                VALUES
                    (:ws, :item_id, :conv_id, :rating, :comment)
            """), {
                "ws": workspace_id,
                "item_id": item_id,
                "conv_id": conversation_id,
                "rating": rating,
                "comment": comment,
            })
            await session.commit()

        # Adjust quality score based on feedback
        await self._adjust_quality_score(workspace_id, item_id, rating)

        logger.info("Feedback recorded: item=%s, rating=%s", item_id, rating)

    async def _adjust_quality_score(
        self, workspace_id: str, item_id: str, rating: str
    ):
        """Adjust quality score based on feedback rating."""
        adjustment = {
            "helpful": 0.15,
            "partially_helpful": 0.05,
            "not_helpful": -0.10,
            "outdated": -0.20,
            "incorrect": -0.30,
        }.get(rating, 0.0)

        if adjustment == 0.0:
            return

        async with async_session_factory() as session:
            # Update quality score
            await session.execute(text("""
                UPDATE ai.knowledge_quality
                SET composite_score = GREATEST(0.0, LEAST(1.0, composite_score + :adjustment)),
                    updated_at = NOW()
                WHERE item_id = :item_id AND workspace_id = :ws
            """), {"adjustment": adjustment, "item_id": item_id, "ws": workspace_id})
            await session.commit()

    async def get_item_feedback(
        self, workspace_id: str, item_id: str
    ) -> dict:
        """Get feedback summary for a knowledge item."""
        await self.ensure_table()

        async with async_session_factory() as session:
            result = await session.execute(text("""
                SELECT rating, COUNT(*) as count
                FROM ai.knowledge_feedback
                WHERE workspace_id = :ws AND item_id = :item_id
                GROUP BY rating
            """), {"ws": workspace_id, "item_id": item_id})
            rows = result.fetchall()

        ratings = {row.rating: row.count for row in rows}
        total = sum(ratings.values())

        return {
            "item_id": item_id,
            "total_feedback": total,
            "ratings": ratings,
            "helpful_rate": round(
                (ratings.get("helpful", 0) + ratings.get("partially_helpful", 0) * 0.5)
                / max(total, 1), 2
            ),
        }

    async def get_workspace_feedback_summary(
        self, workspace_id: str
    ) -> dict:
        """Get overall feedback summary for a workspace."""
        await self.ensure_table()

        async with async_session_factory() as session:
            result = await session.execute(text("""
                SELECT rating, COUNT(*) as count
                FROM ai.knowledge_feedback
                WHERE workspace_id = :ws
                GROUP BY rating
            """), {"ws": workspace_id})
            rows = result.fetchall()

            # Most helpful items
            helpful = await session.execute(text("""
                SELECT kf.item_id, k.title, kf.rating, kf.comment,
                       kf.created_at
                FROM ai.knowledge_feedback kf
                JOIN ai.knowledge_embeddings k ON k.id = kf.item_id
                WHERE kf.workspace_id = :ws AND kf.rating = 'helpful'
                ORDER BY kf.created_at DESC
                LIMIT 5
            """), {"ws": workspace_id})
            helpful_rows = helpful.fetchall()

            # Least helpful items
            unhelpful = await session.execute(text("""
                SELECT kf.item_id, k.title, kf.rating, kf.comment,
                       kf.created_at
                FROM ai.knowledge_feedback kf
                JOIN ai.knowledge_embeddings k ON k.id = kf.item_id
                WHERE kf.workspace_id = :ws AND kf.rating IN ('not_helpful', 'incorrect', 'outdated')
                ORDER BY kf.created_at DESC
                LIMIT 5
            """), {"ws": workspace_id})
            unhelpful_rows = unhelpful.fetchall()

        ratings = {row.rating: row.count for row in rows}
        total = sum(ratings.values())

        return {
            "total_feedback": total,
            "ratings": ratings,
            "helpful_rate": round(
                (ratings.get("helpful", 0) + ratings.get("partially_helpful", 0) * 0.5)
                / max(total, 1), 2
            ),
            "most_helpful": [
                {"item_id": r.item_id, "title": r.title, "comment": r.comment}
                for r in helpful_rows
            ],
            "needs_improvement": [
                {"item_id": r.item_id, "title": r.title, "rating": r.rating, "comment": r.comment}
                for r in unhelpful_rows
            ],
        }
