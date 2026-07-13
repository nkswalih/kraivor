"""Knowledge Retriever — searches stored knowledge with semantic + text search."""

from __future__ import annotations

import logging

from app.infrastructure.rag.embedder import Embedder
from app.knowledge_engine.store.knowledge_store import KnowledgeStore

logger = logging.getLogger(__name__)

_embedder = Embedder()


class KnowledgeRetriever:
    """Retrieves stored knowledge with hybrid search (semantic + text) + graph enrichment."""

    def __init__(self):
        self.store = KnowledgeStore()
        self._graph = None
        self._quality = None

    def _get_graph(self):
        if self._graph is None:
            from app.knowledge_engine.graph.knowledge_graph import KnowledgeGraph
            self._graph = KnowledgeGraph()
        return self._graph

    def _get_quality(self):
        if self._quality is None:
            from app.knowledge_engine.quality.quality_scorer import KnowledgeQualityScorer
            self._quality = KnowledgeQualityScorer()
        return self._quality

    async def retrieve(
        self,
        workspace_id: str,
        query: str,
        top_k: int = 5,
        min_score: float = 0.3,
        providers: list[str] | None = None,
        include_graph: bool = True,
    ) -> list[dict]:
        """Hybrid retrieval with optional graph enrichment."""
        # Text search (primary — embeddings stored as text, no pgvector)
        results = []
        try:
            results = await self.store.search_text(
                workspace_id=workspace_id,
                query=query,
                top_k=top_k,
            )
        except Exception as e:
            logger.debug("Text search failed: %s", e)

        # Filter by provider if specified
        if providers:
            results = [r for r in results if r.get("source_provider") in providers]

        # Format results
        formatted = self._format_results(results)

        # Record quality references
        try:
            quality = self._get_quality()
            await quality.ensure_table()
            for i, item in enumerate(formatted):
                item_id = item.get("id", "")
                if item_id:
                    await quality.record_reference(item_id, workspace_id, rank=i + 1)
                    await quality.update_composite_score(item_id, workspace_id)
        except Exception as e:
            logger.debug("Quality tracking failed: %s", e)

        # Enrich with graph context
        if include_graph and formatted:
            try:
                graph = self._get_graph()
                from app.knowledge_engine.graph.knowledge_graph import extract_entities
                entities = extract_entities(query)
                entity_names = [e["name"] for e in entities]
                if entity_names:
                    graph_context = await graph.get_entity_context(workspace_id, entity_names)
                    if graph_context:
                        formatted[0]["graph_context"] = graph_context
            except Exception as e:
                logger.debug("Graph enrichment failed: %s", e)

        return formatted

    async def retrieve_recent(
        self,
        workspace_id: str,
        limit: int = 10,
    ) -> list[dict]:
        """Get recently stored knowledge items."""
        items = await self.store.get_recent(workspace_id, limit)
        return [
            {
                "source": item["source_url"],
                "title": item["title"],
                "provider": item["source_provider"],
                "fetched_at": item["fetched_at"],
                "trust_score": item["trust_score"],
            }
            for item in items
        ]

    async def has_knowledge(self, workspace_id: str) -> bool:
        """Check if workspace has any stored knowledge."""
        stats = await self.store.get_stats(workspace_id)
        return stats["total_items"] > 0

    async def get_stats(self, workspace_id: str) -> dict:
        """Get knowledge store statistics."""
        return await self.store.get_stats(workspace_id)

    def _format_results(self, results: list[dict]) -> list[dict]:
        """Format retrieved knowledge for context injection."""
        formatted = []
        for item in results:
            # Truncate content for context window
            content = item.get("content", "")
            if len(content) > 2000:
                content = content[:2000] + "..."

            formatted.append({
                "source": item.get("source_url", ""),
                "title": item.get("title", "Untitled"),
                "provider": item.get("source_provider", "unknown"),
                "trust_score": item.get("trust_score", 0.5),
                "content": content,
                "summary": item.get("summary"),
                "similarity": item.get("similarity", item.get("rank", 0)),
                "metadata": item.get("metadata"),
            })

        return formatted
