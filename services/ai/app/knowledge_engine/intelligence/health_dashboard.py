"""Knowledge Health Dashboard — completeness, gaps, freshness, and health overview.

Provides a comprehensive health report for a workspace's knowledge base:
- Completeness: how well-covered are the workspace's technologies
- Freshness: how up-to-date is the knowledge
- Quality distribution: how knowledge scores are distributed
- Gaps: topics with no knowledge coverage
- Actionable recommendations
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from app.infrastructure.db.database import async_session_factory

logger = logging.getLogger(__name__)


class KnowledgeHealthDashboard:
    """Generates health reports for workspace knowledge bases."""

    async def get_health_report(self, workspace_id: str) -> dict:
        """Generate a comprehensive health report."""
        stats = await self._get_basic_stats(workspace_id)
        freshness = await self._get_freshness_report(workspace_id)
        quality_dist = await self._get_quality_distribution(workspace_id)
        provider_dist = await self._get_provider_distribution(workspace_id)
        gaps = await self._detect_gaps(workspace_id)
        recommendations = self._generate_recommendations(stats, freshness, quality_dist, gaps)

        return {
            "workspace_id": workspace_id,
            "generated_at": datetime.now(UTC).isoformat(),
            "overall_health": self._compute_health_score(stats, freshness, quality_dist),
            "stats": stats,
            "freshness": freshness,
            "quality_distribution": quality_dist,
            "provider_distribution": provider_dist,
            "gaps": gaps,
            "recommendations": recommendations,
        }

    async def _get_basic_stats(self, workspace_id: str) -> dict:
        """Get basic knowledge base statistics."""
        async with async_session_factory() as session:
            result = await session.execute(text("""
                SELECT
                    COUNT(*) as total_items,
                    COUNT(DISTINCT source_provider) as providers,
                    COUNT(DISTINCT source_url) as unique_urls,
                    AVG(source_trust_score) as avg_trust,
                    MIN(fetched_at) as oldest,
                    MAX(fetched_at) as newest,
                    SUM(LENGTH(content)) as total_bytes
                FROM ai.knowledge_embeddings
                WHERE workspace_id = :ws
            """), {"ws": workspace_id})
            row = result.fetchone()

        return {
            "total_items": row.total_items or 0,
            "providers": row.providers or 0,
            "unique_urls": row.unique_urls or 0,
            "avg_trust": round(float(row.avg_trust or 0), 2),
            "oldest_item": row.oldest.isoformat() if row.oldest else None,
            "newest_item": row.newest.isoformat() if row.newest else None,
            "total_content_mb": round((row.total_bytes or 0) / (1024 * 1024), 2),
        }

    async def _get_freshness_report(self, workspace_id: str) -> dict:
        """Analyze how fresh the knowledge is."""
        async with async_session_factory() as session:
            result = await session.execute(text("""
                SELECT
                    COUNT(*) FILTER (WHERE fetched_at > NOW() - INTERVAL '1 day') as today,
                    COUNT(*) FILTER (WHERE fetched_at > NOW() - INTERVAL '7 days') as this_week,
                    COUNT(*) FILTER (WHERE fetched_at > NOW() - INTERVAL '30 days') as this_month,
                    COUNT(*) FILTER (WHERE fetched_at > NOW() - INTERVAL '90 days') as this_quarter,
                    COUNT(*) FILTER (WHERE fetched_at < NOW() - INTERVAL '90 days') as stale,
                    COUNT(*) as total
                FROM ai.knowledge_embeddings
                WHERE workspace_id = :ws
            """), {"ws": workspace_id})
            row = result.fetchone()

        total = row.total or 1
        return {
            "today": row.today or 0,
            "this_week": row.this_week or 0,
            "this_month": row.this_month or 0,
            "this_quarter": row.this_quarter or 0,
            "stale": row.stale or 0,
            "freshness_score": round(
                ((row.today or 0) * 1.0 + (row.this_week or 0) * 0.8 + (row.this_month or 0) * 0.5)
                / total, 2
            ),
        }

    async def _get_quality_distribution(self, workspace_id: str) -> dict:
        """Analyze quality score distribution."""
        async with async_session_factory() as session:
            result = await session.execute(text("""
                SELECT
                    COUNT(*) FILTER (WHERE composite_score >= 0.8) as excellent,
                    COUNT(*) FILTER (WHERE composite_score >= 0.6 AND composite_score < 0.8) as good,
                    COUNT(*) FILTER (WHERE composite_score >= 0.4 AND composite_score < 0.6) as average,
                    COUNT(*) FILTER (WHERE composite_score >= 0.2 AND composite_score < 0.4) as poor,
                    COUNT(*) FILTER (WHERE composite_score < 0.2) as very_poor,
                    COUNT(*) as total
                FROM ai.knowledge_quality
                WHERE workspace_id = :ws
            """), {"ws": workspace_id})
            row = result.fetchone()

        total = row.total or 1
        return {
            "excellent": row.excellent or 0,
            "good": row.good or 0,
            "average": row.average or 0,
            "poor": row.poor or 0,
            "very_poor": row.very_poor or 0,
            "total_scored": row.total or 0,
            "quality_score": round(
                ((row.excellent or 0) * 1.0 + (row.good or 0) * 0.75 + (row.average or 0) * 0.5)
                / total, 2
            ),
        }

    async def _get_provider_distribution(self, workspace_id: str) -> list[dict]:
        """Get distribution of knowledge by provider."""
        async with async_session_factory() as session:
            result = await session.execute(text("""
                SELECT source_provider, COUNT(*) as count,
                       AVG(source_trust_score) as avg_trust,
                       MAX(fetched_at) as latest
                FROM ai.knowledge_embeddings
                WHERE workspace_id = :ws
                GROUP BY source_provider
                ORDER BY count DESC
            """), {"ws": workspace_id})
            rows = result.fetchall()

        return [
            {
                "provider": row.source_provider,
                "count": row.count,
                "avg_trust": round(float(row.avg_trust or 0), 2),
                "latest": row.latest.isoformat() if row.latest else None,
            }
            for row in rows
        ]

    async def _detect_gaps(self, workspace_id: str) -> list[dict]:
        """Detect knowledge gaps — important topics with no coverage."""
        gaps = []

        # Check common important topics
        important_topics = [
            ("security", "Security practices and vulnerabilities"),
            ("performance", "Performance optimization and benchmarks"),
            ("testing", "Testing strategies and frameworks"),
            ("deployment", "Deployment and CI/CD practices"),
            ("monitoring", "Monitoring and observability"),
            ("database", "Database design and optimization"),
            ("authentication", "Authentication and authorization"),
            ("api design", "API design patterns and best practices"),
        ]

        async with async_session_factory() as session:
            for topic, description in important_topics:
                result = await session.execute(text("""
                    SELECT COUNT(*) as count
                    FROM ai.knowledge_embeddings
                    WHERE workspace_id = :ws
                      AND to_tsvector('english', coalesce(title, '') || ' ' || coalesce(content, ''))
                          @@ plainto_tsquery('english', :topic)
                """), {"ws": workspace_id, "topic": topic})
                row = result.fetchone()

                if (row.count or 0) < 2:
                    gaps.append({
                        "topic": topic,
                        "description": description,
                        "current_items": row.count or 0,
                        "severity": "high" if (row.count or 0) == 0 else "medium",
                    })

        return gaps

    def _compute_health_score(
        self, stats: dict, freshness: dict, quality: dict
    ) -> dict:
        """Compute an overall health score (0-100)."""
        # Factor 1: Coverage (items count, 0-30 points)
        item_count = stats.get("total_items", 0)
        coverage = min(30, item_count * 2)

        # Factor 2: Freshness (0-30 points)
        freshness_score = freshness.get("freshness_score", 0) * 30

        # Factor 3: Quality (0-30 points)
        quality_score = quality.get("quality_score", 0) * 30

        # Factor 4: Diversity (providers count, 0-10 points)
        diversity = min(10, stats.get("providers", 0) * 2)

        total = round(coverage + freshness_score + quality_score + diversity)

        if total >= 80:
            grade = "excellent"
        elif total >= 60:
            grade = "good"
        elif total >= 40:
            grade = "fair"
        else:
            grade = "poor"

        return {
            "score": min(100, total),
            "grade": grade,
            "breakdown": {
                "coverage": round(coverage),
                "freshness": round(freshness_score),
                "quality": round(quality_score),
                "diversity": round(diversity),
            },
        }

    def _generate_recommendations(
        self, stats: dict, freshness: dict, quality: dict, gaps: list[dict]
    ) -> list[str]:
        """Generate actionable recommendations."""
        recommendations = []

        if stats.get("total_items", 0) < 10:
            recommendations.append(
                "Low knowledge coverage. Use research_topic to build up the knowledge base."
            )

        if freshness.get("stale", 0) > 5:
            recommendations.append(
                f"{freshness['stale']} items are stale (older than 90 days). "
                "Consider running proactive learning to refresh them."
            )

        if freshness.get("freshness_score", 0) < 0.3:
            recommendations.append(
                "Knowledge base is mostly outdated. Run run_proactive_learning to update."
            )

        if quality.get("very_poor", 0) > 3:
            recommendations.append(
                f"{quality['very_poor']} items have very low quality scores. "
                "Review and update or remove them."
            )

        high_severity_gaps = [g for g in gaps if g["severity"] == "high"]
        if high_severity_gaps:
            gap_topics = ", ".join(g["topic"] for g in high_severity_gaps[:3])
            recommendations.append(
                f"Missing critical knowledge about: {gap_topics}. "
                "Use research_topic to fill these gaps."
            )

        if stats.get("providers", 0) < 3:
            recommendations.append(
                "Low source diversity. Knowledge comes from few providers. "
                "Diversify sources for more balanced information."
            )

        if not recommendations:
            recommendations.append("Knowledge base is healthy! Keep it up to date.")

        return recommendations
