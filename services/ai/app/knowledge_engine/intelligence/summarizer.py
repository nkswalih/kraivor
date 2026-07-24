"""Knowledge Summarizer — auto-generates summaries of knowledge collections.

Uses LLM to create concise summaries of:
- All knowledge about a specific topic
- All knowledge in a workspace (overview)
- Knowledge from a specific source/provider
"""

from __future__ import annotations

import logging

from app.infrastructure.db.database import async_session_factory
from app.infrastructure.llm.client import LLMClient
from app.infrastructure.llm.router import ModelRouter
from app.application.provisioning.key_resolver import KeyResolver

logger = logging.getLogger(__name__)


class KnowledgeSummarizer:
    """Generates summaries of knowledge collections using LLM."""

    def __init__(self):
        self.router = ModelRouter()
        self.key_resolver = KeyResolver()

    async def summarize_topic(
        self,
        workspace_id: str,
        topic: str,
        max_items: int = 10,
    ) -> dict:
        """Summarize all knowledge about a specific topic."""
        items = await self._fetch_knowledge(workspace_id, topic, max_items)

        if not items:
            return {
                "topic": topic,
                "summary": f"No knowledge found about '{topic}'.",
                "sources_count": 0,
                "key_points": [],
            }

        # Build context for LLM
        context = self._build_context(items)

        # Generate summary via LLM
        summary, key_points = await self._generate_summary(
            f"Summarize the following knowledge about '{topic}':\n\n{context}"
        )

        return {
            "topic": topic,
            "summary": summary,
            "sources_count": len(items),
            "key_points": key_points,
            "sources": [{"title": i["title"], "url": i["url"], "provider": i["provider"]} for i in items[:5]],
        }

    async def summarize_workspace(
        self,
        workspace_id: str,
    ) -> dict:
        """Generate an overview summary of all knowledge in a workspace."""
        from sqlalchemy import text

        async with async_session_factory() as session:
            result = await session.execute(text("""
                SELECT title, content, source_provider, source_url, source_trust_score
                FROM ai.knowledge_embeddings
                WHERE workspace_id = :ws
                ORDER BY fetched_at DESC
                LIMIT 30
            """), {"ws": workspace_id})
            rows = result.fetchall()

        items = [
            {
                "title": row.title,
                "content": row.content[:1500],
                "provider": row.source_provider,
                "url": row.source_url,
                "trust": row.source_trust_score,
            }
            for row in rows
        ]

        if not items:
            return {
                "summary": "No knowledge stored in this workspace yet.",
                "total_items": 0,
                "topics": [],
            }

        context = self._build_context(items)
        summary, key_points = await self._generate_summary(
            f"Provide a comprehensive overview of the knowledge stored in this workspace:\n\n{context}"
        )

        # Extract topics from titles
        topics = list({i["title"].split(":")[0].strip()[:50] for i in items if i["title"]})

        return {
            "summary": summary,
            "total_items": len(items),
            "topics": topics[:10],
            "key_points": key_points,
        }

    async def summarize_source(
        self,
        workspace_id: str,
        provider: str,
        max_items: int = 10,
    ) -> dict:
        """Summarize all knowledge from a specific source/provider."""
        from sqlalchemy import text

        async with async_session_factory() as session:
            result = await session.execute(text("""
                SELECT title, content, source_url, source_trust_score
                FROM ai.knowledge_embeddings
                WHERE workspace_id = :ws AND source_provider = :provider
                ORDER BY fetched_at DESC
                LIMIT :limit
            """), {"ws": workspace_id, "provider": provider, "limit": max_items})
            rows = result.fetchall()

        items = [
            {
                "title": row.title,
                "content": row.content[:1500],
                "url": row.source_url,
                "trust": row.source_trust_score,
            }
            for row in rows
        ]

        if not items:
            return {
                "source": provider,
                "summary": f"No knowledge from source '{provider}'.",
                "count": 0,
            }

        context = self._build_context(items)
        summary, key_points = await self._generate_summary(
            f"Summarize knowledge from source '{provider}':\n\n{context}"
        )

        return {
            "source": provider,
            "summary": summary,
            "count": len(items),
            "key_points": key_points,
        }

    def _build_context(self, items: list[dict]) -> str:
        """Build a context string from knowledge items."""
        parts = []
        for i, item in enumerate(items, 1):
            parts.append(f"[{i}] {item['title']}\n{item['content'][:1000]}\n")
        return "\n".join(parts)

    async def _generate_summary(self, prompt: str) -> tuple[str, list[str]]:
        """Generate a summary using LLM."""
        try:
            route = self.router.get_route("tool_calling")
            api_key, provider = await self.key_resolver.resolve("", route["model"])
            client = LLMClient(api_key=api_key, provider=provider, model=route["model"])

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a knowledge summarizer. Given a collection of knowledge items, "
                        "produce a concise summary (3-5 paragraphs) and extract 3-5 key points. "
                        "Format your response as:\n\nSUMMARY:\n<your summary>\n\nKEY_POINTS:\n- point 1\n- point 2\n- ..."
                    ),
                },
                {"role": "user", "content": prompt},
            ]

            response = await client.generate(messages, max_tokens=1000)
            content = response.get("content", "")

            # Parse response
            summary = content
            key_points = []

            if "KEY_POINTS:" in content:
                parts = content.split("KEY_POINTS:")
                summary = parts[0].replace("SUMMARY:", "").strip()
                key_points_text = parts[1].strip()
                key_points = [
                    line.strip().lstrip("- ")
                    for line in key_points_text.split("\n")
                    if line.strip().startswith("-")
                ]

            return summary, key_points[:5]

        except Exception as e:
            logger.warning("LLM summary generation failed: %s", e)
            return "Summary generation unavailable.", []

    async def _fetch_knowledge(
        self, workspace_id: str, query: str, limit: int
    ) -> list[dict]:
        """Fetch knowledge items matching a query."""
        from sqlalchemy import text

        async with async_session_factory() as session:
            result = await session.execute(text("""
                SELECT title, content, source_provider, source_url, source_trust_score
                FROM ai.knowledge_embeddings
                WHERE workspace_id = :ws
                  AND to_tsvector('english', coalesce(title, '') || ' ' || coalesce(content, ''))
                      @@ plainto_tsquery('english', :query)
                ORDER BY source_trust_score DESC
                LIMIT :limit
            """), {"ws": workspace_id, "query": query, "limit": limit})
            rows = result.fetchall()

        return [
            {
                "title": row.title,
                "content": row.content[:2000],
                "provider": row.source_provider,
                "url": row.source_url,
                "trust": row.source_trust_score,
            }
            for row in rows
        ]
