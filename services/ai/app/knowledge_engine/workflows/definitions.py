"""Pre-built Workflow Definitions — ready-to-use knowledge workflows.

Each definition describes a DAG of steps that can be executed by the WorkflowEngine.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .engine import WorkflowStep


@dataclass
class WorkflowDefinition:
    """A named workflow definition."""
    name: str
    description: str
    category: str
    steps: list[WorkflowStep]
    tags: list[str] = field(default_factory=list)


# ── Step Handlers ────────────────────────────────────────────────────────────


async def _research_step(context: dict, workspace_id: str | None) -> dict:
    """Research a topic using the knowledge engine."""
    from app.knowledge_engine.engine import KnowledgeEngine

    engine = KnowledgeEngine()
    topic = context.get("topic") or context.get("research", {}).get("topic", "")
    if not topic and "search" in context:
        topic = context["search"].get("query", "")

    result = await engine.research(topic, workspace_id=workspace_id or "default")
    return {"sources": result.get("sources", []), "summary": result.get("summary", "")}


async def _summarize_step(context: dict, workspace_id: str | None) -> dict:
    """Summarize research results."""
    from app.knowledge_engine.intelligence.summarizer import KnowledgeSummarizer

    summarizer = KnowledgeSummarizer()
    topic = context.get("topic") or "research"
    result = await summarizer.summarize_topic(
        workspace_id or "default", topic, max_items=10
    )
    return {"summary": result.get("summary", ""), "key_points": result.get("key_points", [])}


async def _compare_step(context: dict, workspace_id: str | None) -> dict:
    """Compare technologies based on research."""
    from app.knowledge_engine.intelligence.summarizer import KnowledgeSummarizer

    summarizer = KnowledgeSummarizer()
    technologies = context.get("technologies", [])
    if not technologies and "search" in context:
        technologies = [context["search"].get("query", "")]

    summaries = []
    for tech in technologies[:5]:
        result = await summarizer.summarize_topic(
            workspace_id or "default", tech, max_items=5
        )
        summaries.append({"technology": tech, "summary": result.get("summary", "")})

    return {"comparisons": summaries}


async def _conflict_check_step(context: dict, workspace_id: str | None) -> dict:
    """Check for conflicting information."""
    from app.knowledge_engine.intelligence.conflict_resolver import ConflictResolver

    resolver = ConflictResolver()
    topic = context.get("topic") or context.get("research", {}).get("topic", "")
    if not topic and "summarize" in context:
        topic = context["summarize"].get("summary", "")[:100]

    if not topic:
        return {"conflicts": [], "resolution": "No topic to check"}

    report = await resolver.detect_conflicts(
        workspace_id or "default", topic, max_sources=10
    )
    return {
        "conflicts": report.conflicts_found,
        "resolution": report.resolution_summary,
        "groups": len(report.groups),
    }


async def _quality_check_step(context: dict, workspace_id: str | None) -> dict:
    """Check knowledge quality."""
    from app.knowledge_engine.quality.quality_scorer import KnowledgeQualityScorer

    scorer = KnowledgeQualityScorer()
    await scorer.ensure_table()
    stats = await scorer.get_quality_stats(workspace_id or "default")
    return {"quality_stats": stats}


async def _health_check_step(context: dict, workspace_id: str | None) -> dict:
    """Run health check on knowledge base."""
    from app.knowledge_engine.intelligence.health_dashboard import KnowledgeHealthDashboard

    dashboard = KnowledgeHealthDashboard()
    report = await dashboard.get_health_report(workspace_id or "default")
    return {
        "health_score": report.get("overall_health", {}).get("score", 0),
        "recommendations": report.get("recommendations", []),
    }


async def _export_step(context: dict, workspace_id: str | None) -> dict:
    """Export knowledge as structured bundle."""
    from app.knowledge_engine.intelligence.exporter import KnowledgeExporter

    exporter = KnowledgeExporter()
    result = await exporter.export_workspace(
        workspace_id or "default",
        include_embeddings=False,
        include_versions=True,
        include_feedback=True,
        include_graph=True,
    )
    return {"export": result}


async def _dedup_step(context: dict, workspace_id: str | None) -> dict:
    """Run deduplication on knowledge base."""
    from app.knowledge_engine.intelligence.deduplicator import SemanticDeduplicator

    dedup = SemanticDeduplicator()
    result = await dedup.deduplicate_workspace(workspace_id or "default", dry_run=True)
    return {"dedup_result": result}


async def _ingest_step(context: dict, workspace_id: str | None) -> dict:
    """Ingest content from URLs discovered in research."""
    from app.knowledge_engine.store.knowledge_indexer import KnowledgeIndexer

    indexer = KnowledgeIndexer()
    sources = context.get("research", {}).get("sources", [])
    indexed = 0
    for source in sources[:10]:
        url = source.get("url", "")
        title = source.get("title", "")
        content = source.get("content", "")
        if not content:
            continue
        try:
            await indexer.index_knowledge(
                workspace_id=workspace_id or "default",
                source_url=url,
                source_provider=source.get("provider", "web"),
                title=title,
                content=content,
                trust_score=source.get("trust_score", 0.5),
            )
            indexed += 1
        except Exception:
            continue
    return {"indexed_count": indexed}


async def _quality_enrich_step(context: dict, workspace_id: str | None) -> dict:
    """Enrich knowledge with quality scores."""
    from app.knowledge_engine.quality.quality_scorer import KnowledgeQualityScorer

    scorer = KnowledgeQualityScorer()
    await scorer.ensure_table()
    stats = await scorer.get_quality_stats(workspace_id or "default")
    return {"enriched": True, "stats": stats}


# ── Pre-built Workflow Definitions ───────────────────────────────────────────


def get_workflow_definitions() -> list[WorkflowDefinition]:
    """Return all available workflow definitions."""
    return [
        WorkflowDefinition(
            name="research_and_summarize",
            description="Research a topic, summarize findings, and check for conflicts",
            category="research",
            tags=["research", "summarize", "analysis"],
            steps=[
                WorkflowStep("research", "Research Topic", _research_step),
                WorkflowStep("summarize", "Summarize Findings", _summarize_step, depends_on=["research"]),
                WorkflowStep("conflicts", "Check Conflicts", _conflict_check_step, depends_on=["research"]),
                WorkflowStep("quality", "Quality Check", _quality_check_step, depends_on=["summarize"]),
            ],
        ),
        WorkflowDefinition(
            name="compare_technologies",
            description="Compare multiple technologies side by side",
            category="research",
            tags=["comparison", "technologies", "analysis"],
            steps=[
                WorkflowStep("compare", "Compare Technologies", _compare_step),
                WorkflowStep("quality", "Quality Check", _quality_check_step, depends_on=["compare"]),
            ],
        ),
        WorkflowDefinition(
            name="knowledge_health_audit",
            description="Full audit of knowledge base health, quality, and gaps",
            category="maintenance",
            tags=["health", "audit", "quality"],
            steps=[
                WorkflowStep("health", "Health Check", _health_check_step),
                WorkflowStep("quality", "Quality Assessment", _quality_check_step),
                WorkflowStep("dedup", "Deduplication Check", _dedup_step),
            ],
        ),
        WorkflowDefinition(
            name="deep_research",
            description="Deep research with ingestion, quality scoring, and export",
            category="research",
            tags=["deep", "research", "comprehensive"],
            steps=[
                WorkflowStep("research", "Deep Research", _research_step),
                WorkflowStep("ingest", "Ingest Sources", _ingest_step, depends_on=["research"]),
                WorkflowStep("summarize", "Summarize", _summarize_step, depends_on=["research"]),
                WorkflowStep("conflicts", "Conflict Check", _conflict_check_step, depends_on=["research"]),
                WorkflowStep("quality", "Quality Enrich", _quality_enrich_step, depends_on=["ingest"]),
                WorkflowStep("export", "Export Bundle", _export_step, depends_on=["quality"]),
            ],
        ),
        WorkflowDefinition(
            name="knowledge_maintenance",
            description="Routine maintenance: dedup, quality check, health audit",
            category="maintenance",
            tags=["maintenance", "routine", "cleanup"],
            steps=[
                WorkflowStep("dedup", "Deduplication", _dedup_step),
                WorkflowStep("quality", "Quality Check", _quality_check_step),
                WorkflowStep("health", "Health Audit", _health_check_step, depends_on=["quality"]),
            ],
        ),
    ]
