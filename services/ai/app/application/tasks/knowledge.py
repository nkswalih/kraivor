"""Knowledge Celery tasks — auto-indexing, canvas ingestion, conversation learning, freshness checks."""

import asyncio
import logging

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async function from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ── Canvas Auto-Indexing ─────────────────────────────────────────────────────


@celery_app.task(bind=True, queue="ai.indexing", acks_late=True)
def index_knowledge_space_canvas(
    self,
    workspace_id: str,
    knowledge_space_id: str,
    canvas_data: dict,
    knowledge_space_name: str = "Untitled",
):
    """Index all text content from a KnowledgeSpace's canvas_data.

    Called by core service signal when a KnowledgeSpace is saved/updated.
    Extracts text from all canvas elements and stores as knowledge.
    """

    async def _run():
        from app.knowledge_engine.store.knowledge_indexer import KnowledgeIndexer

        indexer = KnowledgeIndexer()
        elements = canvas_data.get("elements", [])
        indexed = 0

        for element in elements:
            content = _extract_element_content(element)
            if not content or len(content.strip()) < 20:
                continue

            etype = element.get("type", "text")
            title = _build_title(element, etype, knowledge_space_name)

            try:
                await indexer.index_knowledge(
                    workspace_id=workspace_id,
                    source_url=f"canvas://{knowledge_space_id}/{element.get('id', 'unknown')}",
                    source_provider="canvas",
                    title=title,
                    content=content,
                    trust_score=0.8,
                    metadata={
                        "knowledge_space_id": knowledge_space_id,
                        "knowledge_space_name": knowledge_space_name,
                        "element_type": etype,
                        "element_id": element.get("id"),
                    },
                )
                indexed += 1
            except Exception as e:
                logger.warning("Failed to index canvas element: %s", e)
                continue

        logger.info(
            "Canvas indexing complete: workspace=%s, space=%s, indexed=%d/%d",
            workspace_id, knowledge_space_name, indexed, len(elements),
        )
        return {"indexed": indexed, "total": len(elements)}

    result = _run_async(_run())
    return {"status": "completed", **result}


# ── Conversation Knowledge Extraction ────────────────────────────────────────


@celery_app.task(bind=True, queue="ai.indexing", acks_late=True)
def extract_conversation_knowledge(
    self,
    workspace_id: str,
    conversation_id: str,
    messages: list[dict],
):
    """Extract and index knowledge from a completed conversation.

    Analyzes messages for factual statements, technical decisions,
    and key information that should be remembered.
    """

    async def _run():
        from app.knowledge_engine.store.knowledge_indexer import KnowledgeIndexer

        indexer = KnowledgeIndexer()
        extracted = _extract_from_messages(messages)
        stored = 0

        for item in extracted:
            try:
                await indexer.index_knowledge(
                    workspace_id=workspace_id,
                    source_url=f"conversation://{conversation_id}/{item['key']}",
                    source_provider="conversation",
                    title=item["title"],
                    content=item["content"],
                    trust_score=0.6,
                    metadata={
                        "conversation_id": conversation_id,
                        "extraction_type": item["type"],
                    },
                )
                stored += 1
            except Exception as e:
                logger.warning("Failed to store conversation knowledge: %s", e)
                continue

        logger.info(
            "Conversation knowledge extraction: ws=%s, conv=%s, stored=%d",
            workspace_id, conversation_id, stored,
        )
        return {"stored": stored, "extracted": len(extracted)}

    result = _run_async(_run())
    return {"status": "completed", **result}


# ── Knowledge Freshness Checker ──────────────────────────────────────────────


@celery_app.task(bind=True, queue="ai.maintenance", acks_late=True)
def check_knowledge_freshness(self, workspace_id: str, stale_days: int = 30):
    """Re-fetch and update stale knowledge items.

    Finds items older than stale_days and refreshes their content.
    """

    async def _run():
        from app.knowledge_engine.store.knowledge_store import KnowledgeStore
        from app.knowledge_engine.engine import KnowledgeEngine

        store = KnowledgeStore()
        engine = KnowledgeEngine()

        recent = await store.get_recent(workspace_id, limit=100)

        refreshed = 0
        for item in recent:
            url = item.get("source_url", "")
            if not url or url.startswith("canvas://") or url.startswith("conversation://"):
                continue

            try:
                content = await engine.fetch(url)
                if content and content.text and len(content.text) > 100:
                    await store.store(
                        workspace_id=workspace_id,
                        source_url=url,
                        source_provider=item.get("source_provider", "web"),
                        title=content.title or item.get("title", ""),
                        content=content.text[:5000],
                        trust_score=item.get("trust_score", 0.5),
                    )
                    refreshed += 1
            except Exception as e:
                logger.debug("Failed to refresh %s: %s", url, e)
                continue

        logger.info(
            "Knowledge freshness check: ws=%s, refreshed=%d",
            workspace_id, refreshed,
        )
        return {"refreshed": refreshed}

    result = _run_async(_run())
    return {"status": "completed", **result}


@celery_app.task(bind=True, queue="ai.maintenance", acks_late=True)
def check_knowledge_freshness_daily(self):
    """Daily task: check freshness for all workspaces with stored knowledge."""

    async def _run():
        from app.knowledge_engine.store.knowledge_store import KnowledgeStore

        KnowledgeStore()

        # Get all workspaces that have knowledge
        from sqlalchemy import text
        from app.infrastructure.db.database import async_session_factory

        async with async_session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT DISTINCT workspace_id
                    FROM ai.knowledge_embeddings
                    WHERE source_provider NOT IN ('canvas', 'conversation')
                    LIMIT 100
                """)
            )
            rows = result.fetchall()

        workspaces = [row.workspace_id for row in rows]
        logger.info("Daily freshness check: %d workspaces", len(workspaces))

        for ws_id in workspaces:
            try:
                check_knowledge_freshness.delay(ws_id, stale_days=30)
            except Exception as e:
                logger.warning("Failed to queue freshness check for %s: %s", ws_id, e)

        return {"workspaces_queued": len(workspaces)}

    result = _run_async(_run())
    return {"status": "completed", **result}


# ── Proactive Learning ───────────────────────────────────────────────────────


@celery_app.task(bind=True, queue="ai.indexing", acks_late=True)
def proactive_learning_cycle(self, workspace_id: str):
    """Run a proactive learning cycle for a single workspace.

    Detects technologies used, checks for new releases and security advisories,
    and auto-indexes relevant updates.
    """

    async def _run():
        from app.knowledge_engine.learning.proactive_agent import ProactiveLearningPipeline

        pipeline = ProactiveLearningPipeline()
        return await pipeline.run_full_cycle(workspace_id)

    result = _run_async(_run())
    return {"status": "completed", **result}


@celery_app.task(bind=True, queue="ai.maintenance", acks_late=True)
def proactive_learning_daily(self):
    """Daily task: run proactive learning for all active workspaces."""

    async def _run():
        from sqlalchemy import text
        from app.infrastructure.db.database import async_session_factory

        async with async_session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT DISTINCT workspace_id
                    FROM ai.knowledge_embeddings
                    WHERE fetched_at > NOW() - INTERVAL '30 days'
                    LIMIT 50
                """)
            )
            rows = result.fetchall()

        workspaces = [row.workspace_id for row in rows]
        logger.info("Daily proactive learning: %d active workspaces", len(workspaces))

        for ws_id in workspaces:
            try:
                proactive_learning_cycle.delay(ws_id)
            except Exception as e:
                logger.warning("Failed to queue proactive learning for %s: %s", ws_id, e)

        return {"workspaces_queued": len(workspaces)}

    result = _run_async(_run())
    return {"status": "completed", **result}


# ── Batch Workspace Indexing ─────────────────────────────────────────────────


@celery_app.task(bind=True, queue="ai.indexing", acks_late=True)
def batch_index_workspace_knowledge(self, workspace_id: str):
    """Index all knowledge spaces in a workspace.

    Called during workspace setup or manual refresh.
    Fetches all knowledge spaces from core and indexes their canvas data.
    """

    async def _run():
        import httpx
        from app.core.config import settings
        from app.knowledge_engine.store.knowledge_indexer import KnowledgeIndexer

        indexer = KnowledgeIndexer()
        core_url = settings.core_api_url

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{core_url}/workspaces/{workspace_id}/knowledge/",
                headers={
                    "X-Internal-Request": settings.internal_request_secret,
                    "X-Workspace-IDs": workspace_id,
                },
            )
            if resp.status_code != 200:
                return {"error": f"Failed to fetch knowledge spaces: {resp.status_code}"}

            data = resp.json()
            spaces = data.get("results", data) if isinstance(data, dict) else data

        total_indexed = 0
        for space in spaces:
            canvas_data = space.get("canvas_data", {})
            elements = canvas_data.get("elements", [])

            for element in elements:
                content = _extract_element_content(element)
                if not content or len(content.strip()) < 20:
                    continue

                etype = element.get("type", "text")
                title = _build_title(element, etype, space.get("name", "Untitled"))

                try:
                    await indexer.index_knowledge(
                        workspace_id=workspace_id,
                        source_url=f"canvas://{space['id']}/{element.get('id', 'unknown')}",
                        source_provider="canvas",
                        title=title,
                        content=content,
                        trust_score=0.8,
                        metadata={
                            "knowledge_space_id": space.get("id"),
                            "knowledge_space_name": space.get("name"),
                            "element_type": etype,
                        },
                    )
                    total_indexed += 1
                except Exception:
                    continue

        logger.info(
            "Batch workspace indexing: ws=%s, total=%d",
            workspace_id, total_indexed,
        )
        return {"total_indexed": total_indexed, "spaces_processed": len(spaces)}

    result = _run_async(_run())
    return {"status": "completed", **result}


# ── Helpers ──────────────────────────────────────────────────────────────────


def _extract_element_content(element: dict) -> str:
    """Extract text content from a canvas element based on its type."""
    etype = element.get("type", "")
    data = element.get("data", {})

    if etype == "text":
        return data.get("text", "")
    elif etype == "markdown":
        return data.get("source", "")
    elif etype == "code":
        lang = data.get("language", "")
        code = data.get("code", "")
        return f"```{lang}\n{code}\n```" if code else ""
    elif etype == "sticky_note":
        return data.get("text", "")
    elif etype == "diagram":
        definition = data.get("definition", "")
        return f"Diagram definition:\n{definition}" if definition else ""
    elif etype == "mindmap":
        return _flatten_mindmap(data.get("root", {}))
    elif etype == "callout":
        return data.get("text", "")
    else:
        return data.get("text", data.get("content", ""))


def _flatten_mindmap(node: dict, depth: int = 0) -> str:
    """Flatten a mindmap node into readable text."""
    lines = []
    label = node.get("label", "")
    if label:
        indent = "  " * depth
        lines.append(f"{indent}- {label}")
    for child in node.get("children", []):
        lines.append(_flatten_mindmap(child, depth + 1))
    return "\n".join(lines)


def _build_title(element: dict, etype: str, space_name: str) -> str:
    """Build a descriptive title for a canvas element."""
    data = element.get("data", {})
    if etype == "text":
        text = data.get("text", "")[:80]
        return f"{space_name}: {text}" if text else f"{space_name}: Text"
    elif etype == "markdown":
        source = data.get("source", "")[:80]
        return f"{space_name}: {source}" if source else f"{space_name}: Markdown"
    elif etype == "code":
        lang = data.get("language", "code")
        return f"{space_name}: Code ({lang})"
    elif etype == "mindmap":
        root_label = data.get("root", {}).get("label", "Mindmap")
        return f"{space_name}: {root_label}"
    elif etype == "diagram":
        return f"{space_name}: Diagram"
    else:
        return f"{space_name}: {etype}"


def _extract_from_messages(messages: list[dict]) -> list[dict]:
    """Extract knowledge-worthy items from conversation messages."""
    import re

    knowledge = []
    seen_keys = set()

    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if not content or role not in ("user", "assistant"):
            continue

        # Facts
        fact_patterns = [
            (r"(?:I use|We use|I prefer|I like)\s+(.+?)(?:\s+for\s+(.+?))?(?:\.|$)", "preference"),
            (r"(?:The|This)\s+(.+?)\s+(?:is|are)\s+(.+?)(?:\.|$)", "definition"),
            (r"(?:I(?:'m| am))\s+(.+?)(?:\.|$)", "identity"),
        ]
        for pattern, ftype in fact_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                groups = match.groups()
                fact = " ".join(g for g in groups if g).strip()
                key = f"{ftype}:{fact[:50]}"
                if fact and len(fact) > 10 and key not in seen_keys:
                    seen_keys.add(key)
                    knowledge.append({
                        "type": ftype,
                        "title": fact[:100],
                        "content": fact,
                        "key": key,
                    })

        # Decisions
        dec_patterns = [
            r"(?:we(?:'ll| will| should)|I(?:'ll| will))\s+(?:use|go with|choose|implement)\s+(.+?)(?:\.|$)",
        ]
        for pattern in dec_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                decision = match.group(1).strip()
                key = f"decision:{decision[:50]}"
                if decision and len(decision) > 10 and key not in seen_keys:
                    seen_keys.add(key)
                    knowledge.append({
                        "type": "decision",
                        "title": decision[:100],
                        "content": decision,
                        "key": key,
                    })

    return knowledge[:10]


# ── Auto-Refresh Pipeline ─────────────────────────────────────────────────────


@celery_app.task(bind=True, queue="ai.maintenance", acks_late=True)
def auto_refresh_stale_knowledge(self, workspace_id: str, stale_days: int = 30, max_items: int = 20):
    """Auto-refresh stale knowledge items for a workspace.

    Uses the KnowledgeRefreshPipeline to identify and re-fetch stale content.
    """

    async def _run():
        from app.knowledge_engine.monitoring.refresh import KnowledgeRefreshPipeline

        pipeline = KnowledgeRefreshPipeline()
        return await pipeline.run_refresh_cycle(workspace_id, stale_days, max_items)

    result = _run_async(_run())
    return {"status": "completed", **result}


@celery_app.task(bind=True, queue="ai.maintenance", acks_late=True)
def auto_refresh_stale_knowledge_daily(self):
    """Daily task: auto-refresh stale knowledge for all active workspaces."""

    async def _run():
        from sqlalchemy import text
        from app.infrastructure.db.database import async_session_factory

        async with async_session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT DISTINCT workspace_id
                    FROM ai.knowledge_embeddings
                    WHERE fetched_at > NOW() - INTERVAL '90 days'
                    LIMIT 50
                """)
            )
            rows = result.fetchall()

        workspaces = [row.workspace_id for row in rows]
        logger.info("Daily auto-refresh: %d active workspaces", len(workspaces))

        for ws_id in workspaces:
            try:
                auto_refresh_stale_knowledge.delay(ws_id, stale_days=30, max_items=20)
            except Exception as e:
                logger.warning("Failed to queue auto-refresh for %s: %s", ws_id, e)

        return {"workspaces_queued": len(workspaces)}

    result = _run_async(_run())
    return {"status": "completed", **result}


# ── Cache Maintenance ─────────────────────────────────────────────────────────


@celery_app.task(bind=True, queue="ai.maintenance", acks_late=True)
def cleanup_knowledge_cache(self):
    """Clean up expired knowledge cache entries and old metrics."""

    async def _run():
        from app.knowledge_engine.monitoring.cache import KnowledgeCache
        from app.knowledge_engine.monitoring.metrics import KnowledgeMetrics

        cache = KnowledgeCache()
        metrics = KnowledgeMetrics()

        cache_removed = await cache.cleanup_expired()
        metrics_cleaned = await metrics.cleanup_old_metrics(days=30)

        return {
            "cache_entries_removed": cache_removed,
            "metrics_cleaned": metrics_cleaned,
        }

    result = _run_async(_run())
    return {"status": "completed", **result}


# ── Kraivor Project Docs Seeding ─────────────────────────────────────────────


@celery_app.task(bind=True, queue="ai.indexing", acks_late=True)
def seed_kraivor_project_docs(self, workspace_id: str):
    """Seed Kraivor project documentation into the knowledge engine.

    Called when a workspace is created so the AI always knows what Kraivor is.
    Reads curated project docs and indexes them with high trust scores.
    """

    async def _run():
        from app.knowledge_engine.seed.kraivor_docs import KRAIVOR_DOCS
        from app.knowledge_engine.store.knowledge_indexer import KnowledgeIndexer

        indexer = KnowledgeIndexer()
        indexed = 0

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
                indexed += 1
            except Exception as e:
                logger.warning("Failed to seed doc '%s': %s", doc["title"], e)

        logger.info("Seeded %d Kraivor docs for workspace %s", indexed, workspace_id)
        return {"indexed": indexed, "total": len(KRAIVOR_DOCS)}

    result = _run_async(_run())
    return {"status": "completed", **result}
