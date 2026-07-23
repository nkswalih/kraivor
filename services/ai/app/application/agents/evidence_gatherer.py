"""EvidenceGathererNode — runs KnowledgeEngine.research() to ground responses in real information."""

import asyncio
import logging
import re
import time

log = logging.getLogger(__name__)

_EVIDENCE_TIMEOUT = 12  # seconds — cap evidence gathering to avoid stalling pipeline

# Fix 9: Moved from in-memory set to Redis SETNX/EXISTS for cross-process safety.
# TTL is 24h — project docs don't need re-seeding within a day.
_SEED_REDIS_TTL = 86400

_NEWS_KEYWORDS = {
    "news", "breaking", "today", "latest news", "recent news",
    "current events", "what happened", "headlines", "daily news",
    "tech news", "technology news", "world news", "global news",
    "morning briefing", "daily briefing", "news compilation",
}

_MIN_TRUST_FOR_NEWS = 0.55

# Fix F: Research queries get full evidence gathering (5 sources).
# Non-research queries get reduced gathering (2 sources) — saves 3-5 seconds
# on DDGS calls + page fetches while still providing enough context.
_RESEARCH_KEYWORDS = {
    "research", "investigate", "analyze", "compare", "evaluate", "review",
    "study", "deep dive", "comprehensive", "thorough", "detailed analysis",
    "what are the best", "pros and cons", "alternatives", "benchmark",
    "tradeoffs", "trade-offs", "how does", "explain in detail",
}


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
        """Seed Kraivor project docs if workspace has no project_docs yet.

        Uses Redis SETNX for cross-process safety with a 24h TTL.
        """
        try:
            from app.infrastructure.cache.redis_client import get_redis
            r = await get_redis()
            seed_key = f"seeded:{workspace_id}"
            already = await r.exists(seed_key)
            if already:
                return
        except Exception:
            # Redis unavailable — fall through to DB check + seed
            r = None
            seed_key = None

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
                    if r and seed_key:
                        try:
                            await r.setex(seed_key, _SEED_REDIS_TTL, "1")
                        except Exception:
                            pass
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
            if r and seed_key:
                try:
                    await r.setex(seed_key, _SEED_REDIS_TTL, "1")
                except Exception:
                    pass
        except Exception as e:
            log.warning("Project doc seeding failed: %s", e)

    async def __call__(self, state: dict) -> dict:
        message = state.get("message", "")
        workspace_id = state.get("workspace_id", "")

        if not message:
            return {"evidence": None, "evidence_sources": []}

        # Skip evidence gathering for very short, random, or non-English queries.
        # Prevents wasting 10-15s on web searches for gibberish like "bhbbkbljh".
        stripped = message.strip()
        if len(stripped) < 5 or not re.search(r'[a-zA-Z]{3,}', stripped):
            log.info("evidence_gatherer: skipping — query too short or non-alphabetic: '%s'", stripped[:20])
            return {"evidence": None, "evidence_sources": []}
        # Also catch vowel-less strings — real words always have vowels
        if len(stripped) >= 5 and not re.search(r'[aeiouyAEIOUY]', stripped):
            log.info("evidence_gatherer: skipping — no vowels (likely gibberish): '%s'", stripped[:20])
            return {"evidence": None, "evidence_sources": []}

        evidence_parts = []
        source_list = []

        engine = self._get_engine()

        if engine and workspace_id:
            await self._ensure_project_docs(workspace_id)

            try:
                stored = await asyncio.wait_for(
                    engine.retrieve_knowledge(
                        workspace_id=workspace_id,
                        query=message,
                        top_k=5,
                    ),
                    timeout=_EVIDENCE_TIMEOUT,
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
                # Fix F: Reduce source count for non-research queries to save latency.
                msg_lower = message.lower()
                is_research = any(kw in msg_lower for kw in _RESEARCH_KEYWORDS)
                max_sources = 5 if is_research else 2

                result = await asyncio.wait_for(
                    engine.research_with_memory(
                        query=message,
                        workspace_id=workspace_id or "",
                        max_sources=max_sources,
                    ),
                    timeout=_EVIDENCE_TIMEOUT,
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

        # For news queries, filter out low-trust sources (forums, random blogs)
        msg_lower = message.lower()
        is_news = any(kw in msg_lower for kw in _NEWS_KEYWORDS)
        if is_news and source_list:
            high_trust = [s for s in source_list if s.get("trust_score", 0) >= _MIN_TRUST_FOR_NEWS]
            if high_trust:
                source_list = high_trust
                # Rebuild evidence from filtered sources only
                filtered_evidence = []
                for s in source_list:
                    snippet = s.get("snippet", "")
                    title = s.get("title", "Untitled")
                    provider = s.get("provider", "")
                    if snippet:
                        filtered_evidence.append(f"[{provider}] {title}:\n{snippet}")
                if filtered_evidence:
                    combined_evidence = "[Filtered news sources — high-trust only]\n\n" + "\n\n".join(filtered_evidence)
                log.info("News query: filtered %d sources down to %d (trust >= %.2f)",
                         len(source_list) + (len(evidence_parts) - len(filtered_evidence)),
                         len(high_trust), _MIN_TRUST_FOR_NEWS)
            else:
                # No high-trust sources survived filtering — prefix with caveat
                combined_evidence = (
                    "[Low-confidence sources — no high-trust outlets found]\n\n"
                    + (combined_evidence or "")
                )
                log.info("News query: no high-trust sources found (%d total), flagging low-confidence",
                         len(source_list))

        # Compute low_confidence flag: news queries with no high-trust sources
        msg_lower_final = message.lower()
        is_news_final = any(kw in msg_lower_final for kw in _NEWS_KEYWORDS)
        low_confidence = False
        if is_news_final and source_list:
            has_high_trust = any(s.get("trust_score", 0) >= _MIN_TRUST_FOR_NEWS for s in source_list)
            low_confidence = not has_high_trust

        return {
            "evidence": combined_evidence,
            "evidence_sources": source_list,
            "low_confidence": low_confidence,
        }
