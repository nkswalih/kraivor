"""Knowledge Indexer — chunks, embeds, and stores retrieved knowledge."""

from __future__ import annotations

import logging
import re

from app.infrastructure.rag.embedder import Embedder
from app.knowledge_engine.store.knowledge_store import KnowledgeStore

logger = logging.getLogger(__name__)

_embedder = Embedder()

# Chunking config for knowledge content
CHUNK_SIZE = 500  # tokens
CHUNK_OVERLAP = 100


def _split_into_chunks(text: str, max_tokens: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks by token count (approximate)."""
    if not text or not text.strip():
        return []

    # Approximate tokens as words * 1.3 (rough tokenizer approximation)
    words = text.split()
    approx_tokens_per_word = 1.3
    max_words = int(max_tokens / approx_tokens_per_word)
    overlap_words = int(overlap / approx_tokens_per_word)

    if len(words) <= max_words:
        return [text.strip()]

    chunks = []
    start = 0
    while start < len(words):
        end = min(start + max_words, len(words))
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk.strip())
        if end >= len(words):
            break
        start = end - overlap_words

    return chunks


def _chunk_knowledge(
    content: str,
    title: str | None = None,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[dict]:
    """Split knowledge content into embeddable chunks with metadata."""
    # Build full text: title + content
    full_text = ""
    if title:
        full_text = f"{title}\n\n"
    full_text += content

    raw_chunks = _split_into_chunks(full_text, chunk_size, chunk_overlap)
    if not raw_chunks:
        return []

    # Add title prefix for context in each chunk
    chunks = []
    for i, chunk in enumerate(raw_chunks):
        chunks.append({
            "text": chunk,
            "chunk_index": i,
            "total_chunks": len(raw_chunks),
        })

    return chunks


class KnowledgeIndexer:
    """Indexes knowledge content into the knowledge store with embeddings."""

    def __init__(self):
        self.store = KnowledgeStore()
        self._graph = None
        self._quality = None
        self._versioning = None

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

    def _get_versioning(self):
        if self._versioning is None:
            from app.knowledge_engine.intelligence.versioning import KnowledgeVersioning
            self._versioning = KnowledgeVersioning()
        return self._versioning

    async def index_knowledge(
        self,
        workspace_id: str,
        source_url: str,
        source_provider: str,
        title: str,
        content: str,
        trust_score: float = 0.5,
        author: str | None = None,
        published_at=None,
        summary: str | None = None,
        metadata: dict | None = None,
        source_type: str | None = None,
        original_filename: str | None = None,
        language: str | None = None,
    ) -> str:
        """Index a single knowledge item with embedding, entities, and quality tracking."""
        # Generate embedding for full content
        embedding_text = f"{title or ''} {content[:2000]}"
        try:
            embedding = await _embedder.embed(embedding_text)
        except Exception as e:
            logger.warning("Failed to generate embedding for %s: %s", source_url, e)
            embedding = None

        # Snapshot existing version before upsert (non-blocking)
        try:
            versioning = self._get_versioning()
            import hashlib
            candidate_id = hashlib.sha256(f"{workspace_id}:{source_url}".encode()).hexdigest()[:24]
            await versioning.snapshot_before_update(workspace_id, candidate_id, reason="auto_update")
        except Exception:
            pass

        # Store the full document
        item_id = await self.store.store(
            workspace_id=workspace_id,
            source_url=source_url,
            source_provider=source_provider,
            title=title,
            content=content,
            trust_score=trust_score,
            author=author,
            published_at=published_at,
            summary=summary,
            embedding=embedding,
            metadata=metadata,
            source_type=source_type,
            original_filename=original_filename,
            language=language,
        )

        # Auto-extract entities and build graph (non-blocking)
        try:
            graph = self._get_graph()
            await graph.ensure_tables()
            entities = await graph.index_entities(workspace_id, item_id, f"{title} {content}")
            if entities:
                await graph.index_relationships(workspace_id, f"{title} {content}")
        except Exception as e:
            logger.debug("Graph indexing failed for %s: %s", item_id, e)

        # Initialize quality tracking (non-blocking)
        try:
            quality = self._get_quality()
            await quality.ensure_table()
            await quality.initialize_item(item_id, workspace_id, f"{title} {content}")
        except Exception as e:
            logger.debug("Quality init failed for %s: %s", item_id, e)

        logger.info("Indexed knowledge: %s → %s (%s)", title[:50], item_id, source_provider)
        return item_id

    async def index_research_result(
        self,
        workspace_id: str,
        research_result: dict,
        top_k: int = 5,
    ) -> int:
        """Index sources from a research result. Returns count of indexed items."""
        sources = research_result.get("sources", [])[:top_k]
        if not sources:
            return 0

        items = []
        for source in sources:
            # Skip low-trust sources
            trust = source.get("trust_score", 0.3)
            if trust < 0.3:
                continue

            # Build content from available fields
            content_parts = []
            if source.get("title"):
                content_parts.append(f"Title: {source['title']}")
            if source.get("content"):
                content_parts.append(f"Content:\n{source['content'][:3000]}")
            elif source.get("summary"):
                content_parts.append(f"Summary:\n{source['summary']}")

            if not content_parts:
                continue

            content = "\n\n".join(content_parts)

            # Generate embedding
            embedding_text = f"{source.get('title', '')} {content[:2000]}"
            try:
                embedding = await _embedder.embed(embedding_text)
            except Exception:
                embedding = None

            items.append({
                "source_url": source.get("url", source.get("source_url", "")),
                "source_provider": source.get("provider", source.get("source_provider", "unknown")),
                "title": source.get("title", ""),
                "content": content,
                "trust_score": trust,
                "author": source.get("author"),
                "summary": source.get("summary"),
                "embedding": embedding,
                "metadata": {
                    "research_query": research_result.get("query", ""),
                    "rank": source.get("rank", 0),
                },
            })

        if not items:
            return 0

        ids = await self.store.store_batch(workspace_id, items)
        logger.info("Indexed %d sources from research for workspace %s", len(ids), workspace_id)
        return len(ids)

    async def index_url_content(
        self,
        workspace_id: str,
        url: str,
        title: str,
        content: str,
        provider: str = "web_fetch",
        trust_score: float = 0.5,
    ) -> str:
        """Index a fetched URL's content."""
        return await self.index_knowledge(
            workspace_id=workspace_id,
            source_url=url,
            source_provider=provider,
            title=title,
            content=content,
            trust_score=trust_score,
        )
