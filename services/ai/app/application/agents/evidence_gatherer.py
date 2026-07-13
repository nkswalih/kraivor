"""EvidenceGathererNode — runs KnowledgeEngine.research() to ground responses in real information."""

import logging
import time

log = logging.getLogger(__name__)


class EvidenceGathererNode:
    """Gathers evidence from the Knowledge Engine before the explainer generates a response."""

    def __init__(self):
        self._engine = None

    def _get_engine(self):
        if self._engine is None:
            try:
                from app.knowledge_engine.engine import KnowledgeEngine
                self._engine = KnowledgeEngine()
            except Exception as e:
                log.warning("Failed to initialize KnowledgeEngine: %s", e)
                return None
        return self._engine

    async def _ensure_project_docs(self, workspace_id: str):
        """Seed Kraivor project docs if workspace has no project_docs yet."""
        try:
            from app.infrastructure.db.database import async_session_factory
            from sqlalchemy import text as sql_text

            async with async_session_factory() as session:
                result = await session.execute(
                    sql_text(
                        "SELECT 1 FROM ai.knowledge_embeddings "
                        "WHERE workspace_id = :wid AND source_provider = 'project_docs' LIMIT 1"
                    ),
                    {"wid": workspace_id},
                )
                if result.fetchone():
                    return

            from app.knowledge_engine.seed.kraivor_docs import KRAIVOR_DOCS
            from app.knowledge_engine.store.knowledge_indexer import KnowledgeIndexer
            indexer = KnowledgeIndexer()
            seeded = 0
            for doc in KRAIVOR_DOCS:
                try:
                    await indexer.index_knowledge(
                        workspace_id=workspace_id,
                        source_url=doc["source_url"],
                        source_provider=doc["source_provider"],
                        title=doc["title"],
                        content=doc["content"],
                        trust_score=doc["trust_score"],
                        metadata=doc.get("metadata"),
                    )
                    seeded += 1
                except Exception as e:
                    log.warning("Failed to seed doc '%s': %s", doc["title"], e)
            log.info("Seeded %d/%d project docs for workspace %s", seeded, len(KRAIVOR_DOCS), workspace_id)
        except Exception as e:
            log.warning("Project doc seeding failed: %s", e)

    async def __call__(self, state: dict) -> dict:
        message = state.get("message", "")
        workspace_id = state.get("workspace_id", "")

        if not message:
            return {"evidence": None, "evidence_sources": []}

        evidence_parts = []
        source_list = []

        engine = self._get_engine()

        if engine and workspace_id:
            await self._ensure_project_docs(workspace_id)

            try:
                stored = await engine.retrieve_knowledge(
                    workspace_id=workspace_id,
                    query=message,
                    top_k=5,
                )
                if stored:
                    for item in stored:
                        title = item.get("title", "Untitled")
                        provider = item.get("provider", "stored")
                        content = item.get("content", "")[:1500]
                        evidence_parts.append(
                            f"[Stored knowledge] {title} ({provider}):\n{content}"
                        )
                        source_list.append({
                            "title": title,
                            "url": item.get("source", ""),
                            "provider": provider,
                            "trust_score": item.get("trust_score", 0.8),
                            "snippet": item.get("content", "")[:200],
                        })
            except Exception as e:
                log.debug("Stored knowledge retrieval failed: %s", e)

        if engine and not evidence_parts:
            start = time.time()
            try:
                result = await engine.research_with_memory(
                    query=message,
                    workspace_id=workspace_id or "",
                    max_sources=5,
                )
                elapsed = time.time() - start
                log.info(
                    "Web evidence gathered for '%s' in %.1fs (%d sources)",
                    message[:50], elapsed, len(result.sources),
                )

                if result.context and result.context != "No relevant knowledge found for this query.":
                    evidence_parts.append(f"[Web research]\n{result.context}")

                for s in result.sources:
                    source_list.append({
                        "title": s.source.title if hasattr(s, "source") else str(s),
                        "url": s.source.url if hasattr(s, "source") else "",
                        "provider": s.source.source_provider if hasattr(s, "source") else "",
                        "trust_score": getattr(s.source, "trust_score", 0.5) if hasattr(s, "source") else 0.5,
                        "snippet": getattr(s.source, "snippet", "") if hasattr(s, "source") else "",
                    })

            except Exception as e:
                log.warning("Web research failed: %s", e)

        combined_evidence = "\n\n".join(evidence_parts) if evidence_parts else None

        return {
            "evidence": combined_evidence,
            "evidence_sources": source_list,
        }
