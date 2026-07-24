"""Knowledge API router — endpoints for knowledge ingestion, search, and stats."""

import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies.auth import JWTPayload, get_current_user
from app.api.dependencies.rate_limiter import check_rate_limit
from app.api.schemas.knowledge import (
    KnowledgeIndexRequest,
    KnowledgeIndexResponse,
    KnowledgeBatchIndexRequest,
    KnowledgeBatchIndexResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeStatsResponse,
    CanvasIndexRequest,
    CanvasIndexResponse,
    ConversationKnowledgeRequest,
    ConversationKnowledgeResponse,
    GraphStatsResponse,
    GraphEntityResponse,
    GraphFindRelatedRequest,
    GraphFindRelatedResponse,
    GraphRelatedEntity,
    QualityStatsResponse,
    QualityTopItemsResponse,
    QualityItem,
    ProactiveLearningResponse,
    ConflictResolutionRequest,
    ConflictResolutionResponse,
    ConflictGroupResponse,
    ConflictClaim,
    SummarizeTopicRequest,
    SummarizeWorkspaceRequest,
    SummarizeSourceRequest,
    SummaryResponse,
    FeedbackRequest,
    FeedbackResponse,
    FeedbackSummaryResponse,
    DedupRequest,
    DedupResponse,
    VersionHistoryResponse,
    VersionStatsResponse,
    RevertRequest,
    RevertResponse,
    ExportRequest,
    ExportResponse,
    HealthReportResponse,
    HealthOverall,
    HealthBreakdown,
    QueryStatsResponse,
    SourceReliabilityResponse,
    UsageTimelineResponse,
    TopQueriesResponse,
    CacheStatsResponse,
    CacheInvalidateRequest,
    CacheInvalidateResponse,
    RefreshStatsResponse,
    RefreshRequest,
    RefreshResponse,
    AdvancedSearchRequest,
    AdvancedSearchResponse,
    AdvancedSearchResult,
    MultiModalIngestFileResponse,
    MultiModalIngestUrlRequest,
    MultiModalIngestTextRequest,
    MultiModalIngestTextResponse,
    MultiModalSupportedTypesResponse,
    KnowledgeListItemResponse,
    KnowledgeListResponse,
    LanguageDetectRequest,
    LanguageDetectResponse,
    LanguageDetectionResult,
    TranslateRequest,
    TranslateResponse,
    MultilingualEmbedRequest,
    MultilingualEmbedResponse,
    WorkflowDefinitionResponse,
    WorkflowRunRequest,
    WorkflowRunResponse,
    WorkflowStatusResponse,
    WorkflowStepResult,
    BundleExportRequest,
    BundleExportResponse,
    BundleImportRequest,
    BundleImportResponse,
    TemplateListResponse,
    TemplateSummary,
    TemplateImportRequest,
)

CurrentUser = Annotated[JWTPayload, Depends(get_current_user)]
RateLimit = Annotated[None, Depends(check_rate_limit)]

router = APIRouter(tags=["knowledge"])


@router.post("/knowledge/index", response_model=KnowledgeIndexResponse)
async def index_knowledge(
    request: KnowledgeIndexRequest,
    user: CurrentUser,
    _: RateLimit = None,
):
    """Index a single knowledge item into the persistent knowledge base."""
    from app.knowledge_engine.engine import KnowledgeEngine

    engine = KnowledgeEngine()

    item_id = await engine.store_knowledge(
        workspace_id=request.workspace_id,
        source_url=request.source_url,
        source_provider=request.source_provider,
        title=request.title,
        content=request.content,
        trust_score=request.trust_score,
        summary=request.summary,
        metadata=request.metadata,
    )

    return KnowledgeIndexResponse(
        id=item_id,
        workspace_id=request.workspace_id,
        source_url=request.source_url,
    )


@router.post("/knowledge/index-batch", response_model=KnowledgeBatchIndexResponse)
async def index_knowledge_batch(
    request: KnowledgeBatchIndexRequest,
    user: CurrentUser,
    _: RateLimit = None,
):
    """Index multiple knowledge items at once."""
    from app.knowledge_engine.store.knowledge_indexer import KnowledgeIndexer

    indexer = KnowledgeIndexer()
    ws = request.workspace_id

    count = 0
    for item in request.items:
        if item.workspace_id != ws:
            continue
        try:
            await indexer.index_knowledge(
                workspace_id=ws,
                source_url=item.source_url,
                source_provider=item.source_provider,
                title=item.title,
                content=item.content,
                trust_score=item.trust_score,
                summary=item.summary,
                metadata=item.metadata,
            )
            count += 1
        except Exception:
            continue

    return KnowledgeBatchIndexResponse(indexed_count=count, workspace_id=ws)


@router.post("/knowledge/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(
    request: KnowledgeSearchRequest,
    user: CurrentUser,
    _: RateLimit = None,
):
    """Search stored knowledge by semantic or text similarity."""
    from app.knowledge_engine.store.knowledge_retriever import KnowledgeRetriever

    retriever = KnowledgeRetriever()

    results = await retriever.retrieve(
        workspace_id=request.workspace_id,
        query=request.query,
        top_k=request.top_k,
        providers=request.providers,
    )

    return KnowledgeSearchResponse(
        query=request.query,
        results=results,
        total=len(results),
    )


@router.get("/knowledge/stats/{workspace_id}", response_model=KnowledgeStatsResponse)
async def get_knowledge_stats(
    workspace_id: str,
    user: CurrentUser,
    _: RateLimit = None,
):
    """Get knowledge base statistics for a workspace."""
    from app.knowledge_engine.store.knowledge_store import KnowledgeStore

    store = KnowledgeStore()
    stats = await store.get_stats(workspace_id)

    return KnowledgeStatsResponse(
        workspace_id=workspace_id,
        total_items=stats["total_items"],
        unique_urls=stats["unique_urls"],
        providers=stats["providers"],
        avg_trust=stats["avg_trust"],
        oldest=stats.get("oldest"),
        newest=stats.get("newest"),
    )


@router.post("/knowledge/index-canvas", response_model=CanvasIndexResponse)
async def index_canvas(
    request: CanvasIndexRequest,
    user: CurrentUser,
    _: RateLimit = None,
):
    """Index knowledge from a KnowledgeSpace canvas (canvas_data JSON).

    Extracts text content from canvas elements and stores them as knowledge.
    """
    from app.knowledge_engine.store.knowledge_indexer import KnowledgeIndexer

    indexer = KnowledgeIndexer()
    canvas_data = request.canvas_data
    elements = canvas_data.get("elements", [])
    indexed_count = 0

    for element in elements:
        content = _extract_element_content(element)
        if not content or len(content.strip()) < 20:
            continue

        element_type = element.get("type", "text")
        title = _build_element_title(element, element_type, request.knowledge_space_name)

        try:
            await indexer.index_knowledge(
                workspace_id=request.workspace_id,
                source_url=f"canvas://{request.knowledge_space_id}/{element.get('id', 'unknown')}",
                source_provider="canvas",
                title=title,
                content=content,
                trust_score=0.8,
                summary=None,
                metadata={
                    "knowledge_space_id": request.knowledge_space_id,
                    "knowledge_space_name": request.knowledge_space_name,
                    "element_type": element_type,
                    "element_id": element.get("id"),
                },
            )
            indexed_count += 1
        except Exception:
            continue

    return CanvasIndexResponse(
        workspace_id=request.workspace_id,
        knowledge_space_id=request.knowledge_space_id,
        indexed_count=indexed_count,
        elements_processed=len(elements),
    )


@router.post("/knowledge/index-conversation", response_model=ConversationKnowledgeResponse)
async def index_conversation_knowledge(
    request: ConversationKnowledgeRequest,
    user: CurrentUser,
    _: RateLimit = None,
):
    """Extract and index knowledge from a conversation.

    Analyzes messages for factual statements, decisions, and key information
    that should be remembered for future sessions.
    """
    from app.knowledge_engine.store.knowledge_indexer import KnowledgeIndexer

    indexer = KnowledgeIndexer()
    extracted = _extract_knowledge_from_messages(request.messages)

    for item in extracted:
        try:
            await indexer.index_knowledge(
                workspace_id=request.workspace_id,
                source_url=f"conversation://{request.conversation_id}/{item['key']}",
                source_provider="conversation",
                title=item["title"],
                content=item["content"],
                trust_score=0.6,
                summary=item.get("summary"),
                metadata={
                    "conversation_id": request.conversation_id,
                    "extraction_type": item["type"],
                },
            )
        except Exception:
            continue

    return ConversationKnowledgeResponse(
        workspace_id=request.workspace_id,
        conversation_id=request.conversation_id,
        extracted_count=len(extracted),
        facts=[{"type": e["type"], "title": e["title"]} for e in extracted],
    )


# ── Knowledge Graph Endpoints ────────────────────────────────────────────────


@router.get("/knowledge/graph/stats/{workspace_id}", response_model=GraphStatsResponse)
async def get_graph_stats(
    workspace_id: str,
    user: CurrentUser,
    _: RateLimit = None,
):
    """Get knowledge graph statistics for a workspace."""
    from app.knowledge_engine.graph.knowledge_graph import KnowledgeGraph

    graph = KnowledgeGraph()
    await graph.ensure_tables()
    stats = await graph.get_entity_stats(workspace_id)

    return GraphStatsResponse(
        workspace_id=workspace_id,
        entities=stats["entities"],
        entity_types=stats["entity_types"],
        relationships=stats["relationships"],
        relationship_types=stats["relationship_types"],
    )


@router.get("/knowledge/graph/entities/{workspace_id}", response_model=list[GraphEntityResponse])
async def get_graph_entities(
    workspace_id: str,
    entity_type: str | None = None,
    top_n: int = 20,
    user: CurrentUser = None,
    _: RateLimit = None,
):
    """Get the most mentioned entities in a workspace's knowledge graph."""
    from app.knowledge_engine.graph.knowledge_graph import KnowledgeGraph

    graph = KnowledgeGraph()
    await graph.ensure_tables()
    entities = await graph.get_workspace_entities(workspace_id, entity_type, top_n)

    return [
        GraphEntityResponse(
            name=e["name"],
            type=e["type"],
            mentions=e["mentions"],
            first_seen=e["first_seen"],
            last_seen=e["last_seen"],
        )
        for e in entities
    ]


@router.post("/knowledge/graph/related", response_model=GraphFindRelatedResponse)
async def find_related_entities(
    request: GraphFindRelatedRequest,
    user: CurrentUser,
    _: RateLimit = None,
):
    """Find entities related to a given entity via the knowledge graph."""
    from app.knowledge_engine.graph.knowledge_graph import KnowledgeGraph

    graph = KnowledgeGraph()
    await graph.ensure_tables()
    related = await graph.find_related(
        request.workspace_id,
        request.entity_name,
        request.max_depth,
    )

    return GraphFindRelatedResponse(
        entity=request.entity_name,
        related=[
            GraphRelatedEntity(
                entity=r["entity"],
                relationship=r["relationship"],
                weight=r["weight"],
                path_count=r["path_count"],
            )
            for r in related
        ],
        total=len(related),
    )


# ── Knowledge Quality Endpoints ──────────────────────────────────────────────


@router.get("/knowledge/quality/stats/{workspace_id}", response_model=QualityStatsResponse)
async def get_quality_stats(
    workspace_id: str,
    user: CurrentUser,
    _: RateLimit = None,
):
    """Get knowledge quality statistics for a workspace."""
    from app.knowledge_engine.quality.quality_scorer import KnowledgeQualityScorer

    scorer = KnowledgeQualityScorer()
    await scorer.ensure_table()
    stats = await scorer.get_quality_stats(workspace_id)

    return QualityStatsResponse(
        workspace_id=workspace_id,
        total_tracked=stats["total_tracked"],
        avg_quality=stats["avg_quality"],
        max_quality=stats["max_quality"],
        total_references=stats["total_references"],
        avg_references=stats["avg_references"],
    )


@router.get("/knowledge/quality/top/{workspace_id}", response_model=QualityTopItemsResponse)
async def get_top_quality_items(
    workspace_id: str,
    limit: int = 10,
    user: CurrentUser = None,
    _: RateLimit = None,
):
    """Get the highest quality knowledge items for a workspace."""
    from app.knowledge_engine.quality.quality_scorer import KnowledgeQualityScorer

    scorer = KnowledgeQualityScorer()
    await scorer.ensure_table()
    items = await scorer.get_top_quality(workspace_id, limit)

    return QualityTopItemsResponse(
        workspace_id=workspace_id,
        items=[
            QualityItem(
                item_id=i["item_id"],
                title=i["title"],
                url=i["url"],
                provider=i["provider"],
                trust_score=i["trust_score"],
                references=i["references"],
                avg_rank=i["avg_rank"],
                quality_score=i["quality_score"],
            )
            for i in items
        ],
        total=len(items),
    )


# ── Proactive Learning Endpoints ────────────────────────────────────────────


@router.post("/knowledge/learn/{workspace_id}", response_model=ProactiveLearningResponse)
async def trigger_proactive_learning(
    workspace_id: str,
    user: CurrentUser,
    _: RateLimit = None,
):
    """Trigger a proactive learning cycle for a workspace.

    Detects technologies used, checks for new releases and security advisories,
    and auto-indexes relevant updates.
    """
    from app.knowledge_engine.learning.proactive_agent import ProactiveLearningPipeline

    pipeline = ProactiveLearningPipeline()
    result = await pipeline.run_full_cycle(workspace_id)

    return ProactiveLearningResponse(
        workspace_id=workspace_id,
        technologies=result["technologies"],
        new_releases=result["new_releases"],
        security_advisories=result["security_advisories"],
        stale_docs=result["stale_docs"],
        items_indexed=result["items_indexed"],
    )


# ── Conflict Resolution Endpoints ────────────────────────────────────────────


@router.post("/knowledge/conflicts", response_model=ConflictResolutionResponse)
async def detect_conflicts(
    request: ConflictResolutionRequest,
    user: CurrentUser,
    _: RateLimit = None,
):
    """Detect and resolve conflicting claims across knowledge sources for a topic."""
    from app.knowledge_engine.intelligence.conflict_resolver import ConflictResolver

    resolver = ConflictResolver()
    report = await resolver.detect_conflicts(
        request.workspace_id, request.topic, request.max_sources
    )

    return ConflictResolutionResponse(
        topic=report.topic,
        conflicts_found=report.conflicts_found,
        groups=[
            ConflictGroupResponse(
                topic=g.topic,
                conflict_type=g.conflict_type,
                claims=[
                    ConflictClaim(
                        content=c.content,
                        source_url=c.source_url,
                        source_provider=c.source_provider,
                        trust_score=c.trust_score,
                    )
                    for c in g.claims
                ],
                resolution=g.resolution,
                confidence=g.confidence,
            )
            for g in report.groups
        ],
        resolution_summary=report.resolution_summary,
        sources_consulted=report.sources_consulted,
    )


# ── Summarization Endpoints ──────────────────────────────────────────────────


@router.post("/knowledge/summarize/topic", response_model=SummaryResponse)
async def summarize_topic(
    request: SummarizeTopicRequest,
    user: CurrentUser,
    _: RateLimit = None,
):
    """Summarize all knowledge about a specific topic using LLM."""
    from app.knowledge_engine.intelligence.summarizer import KnowledgeSummarizer

    summarizer = KnowledgeSummarizer()
    result = await summarizer.summarize_topic(
        request.workspace_id, request.topic, request.max_items
    )

    return SummaryResponse(
        summary=result["summary"],
        sources_count=result["sources_count"],
        key_points=result.get("key_points", []),
        sources=result.get("sources", []),
    )


@router.post("/knowledge/summarize/workspace", response_model=SummaryResponse)
async def summarize_workspace(
    request: SummarizeWorkspaceRequest,
    user: CurrentUser,
    _: RateLimit = None,
):
    """Generate an overview summary of all knowledge in a workspace."""
    from app.knowledge_engine.intelligence.summarizer import KnowledgeSummarizer

    summarizer = KnowledgeSummarizer()
    result = await summarizer.summarize_workspace(request.workspace_id)

    return SummaryResponse(
        summary=result["summary"],
        sources_count=result.get("total_items", 0),
        key_points=result.get("key_points", []),
    )


@router.post("/knowledge/summarize/source", response_model=SummaryResponse)
async def summarize_source(
    request: SummarizeSourceRequest,
    user: CurrentUser,
    _: RateLimit = None,
):
    """Summarize all knowledge from a specific source/provider."""
    from app.knowledge_engine.intelligence.summarizer import KnowledgeSummarizer

    summarizer = KnowledgeSummarizer()
    result = await summarizer.summarize_source(
        request.workspace_id, request.provider, request.max_items
    )

    return SummaryResponse(
        summary=result["summary"],
        sources_count=result.get("count", 0),
        key_points=result.get("key_points", []),
    )


# ── Feedback Endpoints ───────────────────────────────────────────────────────


@router.post("/knowledge/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    user: CurrentUser,
    _: RateLimit = None,
):
    """Record user feedback on a knowledge item's quality."""
    from app.knowledge_engine.intelligence.feedback import FeedbackTracker

    tracker = FeedbackTracker()
    await tracker.record_feedback(
        workspace_id=request.workspace_id,
        item_id=request.item_id,
        rating=request.rating,
        conversation_id=request.conversation_id,
        comment=request.comment,
    )

    return FeedbackResponse(item_id=request.item_id, rating=request.rating)


@router.get("/knowledge/feedback/{workspace_id}", response_model=FeedbackSummaryResponse)
async def get_feedback_summary(
    workspace_id: str,
    user: CurrentUser,
    _: RateLimit = None,
):
    """Get overall feedback summary for a workspace."""
    from app.knowledge_engine.intelligence.feedback import FeedbackTracker

    tracker = FeedbackTracker()
    result = await tracker.get_workspace_feedback_summary(workspace_id)

    return FeedbackSummaryResponse(
        workspace_id=workspace_id,
        total_feedback=result["total_feedback"],
        ratings=result["ratings"],
        helpful_rate=result["helpful_rate"],
        most_helpful=result.get("most_helpful", []),
        needs_improvement=result.get("needs_improvement", []),
    )


# ── Deduplication Endpoints ──────────────────────────────────────────────────


@router.post("/knowledge/dedup", response_model=DedupResponse)
async def deduplicate_knowledge(
    request: DedupRequest,
    user: CurrentUser,
    _: RateLimit = None,
):
    """Find and optionally remove near-duplicate knowledge items."""
    from app.knowledge_engine.intelligence.deduplicator import SemanticDeduplicator

    dedup = SemanticDeduplicator()
    result = await dedup.deduplicate_workspace(
        request.workspace_id, dry_run=request.dry_run
    )

    return DedupResponse(
        duplicate_groups=result["duplicate_groups"],
        items_to_remove=result["items_to_remove"],
        items_removed=result["items_removed"],
        dry_run=result["dry_run"],
        workspace_id=request.workspace_id,
    )


# ── Versioning Endpoints ─────────────────────────────────────────────────────


@router.get("/knowledge/versions/{workspace_id}/{item_id}", response_model=VersionHistoryResponse)
async def get_version_history(
    workspace_id: str,
    item_id: str,
    limit: int = 10,
    user: CurrentUser = None,
    _: RateLimit = None,
):
    """Get version history for a knowledge item."""
    from app.knowledge_engine.intelligence.versioning import KnowledgeVersioning

    versioning = KnowledgeVersioning()
    versions = await versioning.get_version_history(workspace_id, item_id, limit)

    return VersionHistoryResponse(
        workspace_id=workspace_id,
        item_id=item_id,
        versions=versions,
        total=len(versions),
    )


@router.get("/knowledge/versions/stats/{workspace_id}", response_model=VersionStatsResponse)
async def get_version_stats(
    workspace_id: str,
    user: CurrentUser,
    _: RateLimit = None,
):
    """Get versioning statistics for a workspace."""
    from app.knowledge_engine.intelligence.versioning import KnowledgeVersioning

    versioning = KnowledgeVersioning()
    stats = await versioning.get_version_stats(workspace_id)

    return VersionStatsResponse(
        workspace_id=workspace_id,
        versioned_items=stats["versioned_items"],
        total_versions=stats["total_versions"],
        max_version=stats["max_version"],
        oldest_snapshot=stats.get("oldest_snapshot"),
        newest_snapshot=stats.get("newest_snapshot"),
    )


@router.post("/knowledge/versions/revert", response_model=RevertResponse)
async def revert_version(
    request: RevertRequest,
    user: CurrentUser,
    _: RateLimit = None,
):
    """Revert a knowledge item to a previous version."""
    from app.knowledge_engine.intelligence.versioning import KnowledgeVersioning

    versioning = KnowledgeVersioning()
    success = await versioning.revert_to_version(
        request.workspace_id, request.item_id, request.version
    )

    if not success:
        raise HTTPException(status_code=404, detail="Version not found")

    return RevertResponse(
        status="reverted",
        item_id=request.item_id,
        reverted_to_version=request.version,
    )


# ── Export Endpoints ──────────────────────────────────────────────────────────


@router.post("/knowledge/export", response_model=ExportResponse)
async def export_knowledge(
    request: ExportRequest,
    user: CurrentUser,
    _: RateLimit = None,
):
    """Export all knowledge for a workspace as structured JSON."""
    from app.knowledge_engine.intelligence.exporter import KnowledgeExporter

    exporter = KnowledgeExporter()
    result = await exporter.export_workspace(
        request.workspace_id,
        include_embeddings=request.include_embeddings,
        include_versions=request.include_versions,
        include_feedback=request.include_feedback,
        include_graph=request.include_graph,
    )

    return ExportResponse(
        version=result["version"],
        workspace_id=result["workspace_id"],
        exported_at=result["exported_at"],
        item_count=result["item_count"],
        items=result["items"],
        stats=result["stats"],
        graph=result.get("graph"),
        versions=result.get("versions"),
        feedback=result.get("feedback"),
    )


# ── Health Dashboard Endpoints ───────────────────────────────────────────────


@router.get("/knowledge/health/{workspace_id}", response_model=HealthReportResponse)
async def get_knowledge_health(
    workspace_id: str,
    user: CurrentUser,
    _: RateLimit = None,
):
    """Get a comprehensive health report for the workspace's knowledge base."""
    from app.knowledge_engine.intelligence.health_dashboard import KnowledgeHealthDashboard

    dashboard = KnowledgeHealthDashboard()
    result = await dashboard.get_health_report(workspace_id)

    return HealthReportResponse(
        workspace_id=result["workspace_id"],
        generated_at=result["generated_at"],
        overall_health=HealthOverall(
            score=result["overall_health"]["score"],
            grade=result["overall_health"]["grade"],
            breakdown=HealthBreakdown(**result["overall_health"]["breakdown"]),
        ),
        stats=result["stats"],
        freshness=result["freshness"],
        quality_distribution=result["quality_distribution"],
        provider_distribution=result["provider_distribution"],
        gaps=result["gaps"],
        recommendations=result["recommendations"],
    )


# ── Monitoring Endpoints ─────────────────────────────────────────────────────


@router.get("/knowledge/monitoring/stats/{workspace_id}", response_model=QueryStatsResponse)
async def get_query_stats(
    workspace_id: str,
    hours: int = 24,
    user: CurrentUser = None,
    _: RateLimit = None,
):
    """Get query performance statistics for a workspace."""
    from app.knowledge_engine.monitoring.metrics import KnowledgeMetrics

    metrics = KnowledgeMetrics()
    result = await metrics.get_query_stats(workspace_id, hours)

    return QueryStatsResponse(
        workspace_id=workspace_id,
        total_queries=result["total_queries"],
        cache_hits=result["cache_hits"],
        cache_hit_rate=result["cache_hit_rate"],
        errors=result["errors"],
        error_rate=result["error_rate"],
        avg_latency_ms=result["avg_latency_ms"],
        p50_latency_ms=result["p50_latency_ms"],
        p95_latency_ms=result["p95_latency_ms"],
        max_latency_ms=result["max_latency_ms"],
        total_sources_fetched=result["total_sources_fetched"],
        period_hours=result["period_hours"],
    )


@router.get("/knowledge/monitoring/sources/{workspace_id}", response_model=SourceReliabilityResponse)
async def get_source_reliability(
    workspace_id: str,
    hours: int = 168,
    user: CurrentUser = None,
    _: RateLimit = None,
):
    """Get reliability stats per source provider."""
    from app.knowledge_engine.monitoring.metrics import KnowledgeMetrics

    metrics = KnowledgeMetrics()
    providers = await metrics.get_source_reliability(workspace_id, hours)

    return SourceReliabilityResponse(
        workspace_id=workspace_id,
        providers=providers,
        period_hours=hours,
    )


@router.get("/knowledge/monitoring/timeline/{workspace_id}", response_model=UsageTimelineResponse)
async def get_usage_timeline(
    workspace_id: str,
    hours: int = 24,
    bucket_minutes: int = 60,
    user: CurrentUser = None,
    _: RateLimit = None,
):
    """Get query volume over time in time buckets."""
    from app.knowledge_engine.monitoring.metrics import KnowledgeMetrics

    metrics = KnowledgeMetrics()
    buckets = await metrics.get_usage_timeline(workspace_id, hours, bucket_minutes)

    return UsageTimelineResponse(
        workspace_id=workspace_id,
        buckets=buckets,
        period_hours=hours,
    )


@router.get("/knowledge/monitoring/top-queries/{workspace_id}", response_model=TopQueriesResponse)
async def get_top_queries(
    workspace_id: str,
    limit: int = 10,
    hours: int = 168,
    user: CurrentUser = None,
    _: RateLimit = None,
):
    """Get most frequently asked queries."""
    from app.knowledge_engine.monitoring.metrics import KnowledgeMetrics

    metrics = KnowledgeMetrics()
    queries = await metrics.get_top_queries(workspace_id, limit, hours)

    return TopQueriesResponse(workspace_id=workspace_id, queries=queries)


# ── Cache Endpoints ───────────────────────────────────────────────────────────


@router.get("/knowledge/cache/stats/{workspace_id}", response_model=CacheStatsResponse)
async def get_cache_stats(
    workspace_id: str,
    user: CurrentUser = None,
    _: RateLimit = None,
):
    """Get cache statistics for a workspace."""
    from app.knowledge_engine.monitoring.cache import KnowledgeCache

    cache = KnowledgeCache()
    stats = await cache.get_stats(workspace_id)

    return CacheStatsResponse(**stats, workspace_id=workspace_id)


@router.post("/knowledge/cache/invalidate", response_model=CacheInvalidateResponse)
async def invalidate_cache(
    request: CacheInvalidateRequest,
    user: CurrentUser,
    _: RateLimit = None,
):
    """Invalidate cache entries for a workspace."""
    from app.knowledge_engine.monitoring.cache import KnowledgeCache

    cache = KnowledgeCache()
    removed = await cache.invalidate(request.workspace_id, request.cache_type)

    return CacheInvalidateResponse(
        workspace_id=request.workspace_id,
        entries_removed=removed,
    )


# ── Refresh Pipeline Endpoints ───────────────────────────────────────────────


@router.get("/knowledge/refresh/stats/{workspace_id}", response_model=RefreshStatsResponse)
async def get_refresh_stats(
    workspace_id: str,
    user: CurrentUser = None,
    _: RateLimit = None,
):
    """Get knowledge refresh pipeline statistics."""
    from app.knowledge_engine.monitoring.refresh import KnowledgeRefreshPipeline

    pipeline = KnowledgeRefreshPipeline()
    stats = await pipeline.get_refresh_stats(workspace_id)

    return RefreshStatsResponse(**stats, workspace_id=workspace_id)


@router.post("/knowledge/refresh/run", response_model=RefreshResponse)
async def trigger_refresh(
    request: RefreshRequest,
    user: CurrentUser,
    _: RateLimit = None,
):
    """Run a knowledge refresh cycle — re-index stale items."""
    from app.knowledge_engine.monitoring.refresh import KnowledgeRefreshPipeline

    pipeline = KnowledgeRefreshPipeline()
    result = await pipeline.run_refresh_cycle(
        request.workspace_id,
        stale_days=request.stale_days,
        max_items=request.max_items,
    )

    return RefreshResponse(
        workspace_id=result["workspace_id"],
        stale_found=result["stale_found"],
        refreshed=result["refreshed"],
        failed=result["failed"],
        total_latency_ms=result["total_latency_ms"],
        status=result["status"],
    )


# ── Advanced Search Endpoints ────────────────────────────────────────────────


@router.post("/knowledge/search/advanced", response_model=AdvancedSearchResponse)
async def advanced_search(
    request: AdvancedSearchRequest,
    user: CurrentUser,
    _: RateLimit = None,
):
    """Search knowledge with advanced filters and composite ranking."""
    from app.knowledge_engine.search.advanced import AdvancedSearch

    search = AdvancedSearch()
    result = await search.search(
        workspace_id=request.workspace_id,
        query=request.query,
        top_k=request.top_k,
        providers=request.providers,
        min_trust=request.min_trust,
        created_after=request.created_after,
        created_before=request.created_before,
        min_content_length=request.min_content_length,
    )

    return AdvancedSearchResponse(
        query=result["query"],
        results=[
            AdvancedSearchResult(**r) for r in result["results"]
        ],
        total=result["total"],
        filters_applied=result["filters_applied"],
    )


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
    elif etype == "divider":
        return ""
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


def _build_element_title(element: dict, element_type: str, space_name: str) -> str:
    """Build a descriptive title for a canvas element."""
    data = element.get("data", {})
    if element_type == "text":
        text = data.get("text", "")[:80]
        return f"{space_name}: {text}" if text else f"{space_name}: Text element"
    elif element_type == "markdown":
        source = data.get("source", "")[:80]
        return f"{space_name}: {source}" if source else f"{space_name}: Markdown"
    elif element_type == "code":
        lang = data.get("language", "code")
        return f"{space_name}: Code ({lang})"
    elif element_type == "mindmap":
        root_label = data.get("root", {}).get("label", "Mindmap")
        return f"{space_name}: {root_label}"
    elif element_type == "diagram":
        return f"{space_name}: Diagram"
    else:
        return f"{space_name}: {element_type}"


def _extract_knowledge_from_messages(messages: list[dict]) -> list[dict]:
    """Extract knowledge-worthy items from conversation messages.

    Looks for factual statements, technical decisions, and key information.
    """
    knowledge = []

    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if not content or role not in ("user", "assistant"):
            continue

        # Look for factual patterns
        facts = _extract_facts(content)
        knowledge.extend(facts)

        # Look for technical decisions
        decisions = _extract_decisions(content)
        knowledge.extend(decisions)

    return knowledge


# ── Multi-Modal Ingestion Endpoints ──────────────────────────────────────────


@router.post("/knowledge/ingest/file", response_model=MultiModalIngestFileResponse)
async def ingest_file(
    workspace_id: str,
    tags: str | None = None,
    language: str | None = None,
    file: bytes = None,
    filename: str | None = None,
    content_type: str | None = None,
    user: CurrentUser = None,
    _: RateLimit = None,
):
    """Ingest a file (PDF, image, or audio) into the knowledge base.

    Accepts multipart/form-data with a file upload.
    Auto-detects file type and extracts text content.
    """
    from app.knowledge_engine.multimodal.ingester import MultiModalIngester

    if file is None:
        raise HTTPException(status_code=400, detail="No file provided")

    ingester = MultiModalIngester()
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    result = await ingester.ingest_file(
        file_bytes=file,
        filename=filename,
        mime_type=content_type,
        workspace_id=workspace_id,
        user_id=user.sub if user else None,
        tags=tag_list,
        language=language,
    )

    return MultiModalIngestFileResponse(
        success=result.success,
        source_type=result.source_type,
        title=result.title,
        total_characters=result.total_characters,
        chunk_count=result.chunk_count,
        knowledge_ids=result.knowledge_ids,
        language=result.language,
        metadata=result.metadata,
        error=result.error,
    )


@router.post("/knowledge/ingest/url", response_model=MultiModalIngestFileResponse)
async def ingest_url(
    request: MultiModalIngestUrlRequest,
    user: CurrentUser,
    _: RateLimit = None,
):
    """Ingest content from a URL — auto-detects type and extracts text."""
    from app.knowledge_engine.multimodal.ingester import MultiModalIngester

    ingester = MultiModalIngester()

    result = await ingester.ingest_url(
        url=request.url,
        workspace_id=request.workspace_id,
        user_id=user.sub if user else None,
        tags=request.tags,
    )

    return MultiModalIngestFileResponse(
        success=result.success,
        source_type=result.source_type,
        title=result.title,
        total_characters=result.total_characters,
        chunk_count=result.chunk_count,
        knowledge_ids=result.knowledge_ids,
        language=result.language,
        metadata=result.metadata,
        error=result.error,
    )


@router.post("/knowledge/ingest/text", response_model=MultiModalIngestTextResponse)
async def ingest_text(
    request: MultiModalIngestTextRequest,
    user: CurrentUser,
    _: RateLimit = None,
):
    """Ingest raw text content into the knowledge base."""
    from app.knowledge_engine.multimodal.ingester import MultiModalIngester

    ingester = MultiModalIngester()

    result = await ingester.ingest_text(
        text=request.text,
        title=request.title,
        source_url=request.source_url,
        workspace_id=request.workspace_id,
        user_id=user.sub if user else None,
        tags=request.tags,
        language=request.language,
    )

    return MultiModalIngestTextResponse(
        success=result.success,
        source_type=result.source_type,
        title=result.title,
        total_characters=result.total_characters,
        chunk_count=result.chunk_count,
        knowledge_ids=result.knowledge_ids,
        language=result.language,
        error=result.error,
    )


@router.get("/knowledge/ingest/supported-types", response_model=MultiModalSupportedTypesResponse)
async def get_supported_types(
    user: CurrentUser = None,
    _: RateLimit = None,
):
    """List all supported file types for multi-modal ingestion."""
    from app.knowledge_engine.multimodal.ingester import MultiModalIngester

    ingester = MultiModalIngester()
    types = ingester.get_supported_types()

    return MultiModalSupportedTypesResponse(**types)


@router.get("/knowledge/list/{workspace_id}", response_model=KnowledgeListResponse)
async def list_knowledge_items(
    workspace_id: str,
    limit: int = 20,
    offset: int = 0,
    source_type: str | None = None,
    user: CurrentUser = None,
    _: RateLimit = None,
):
    """List knowledge items for a workspace with optional filtering."""
    from app.knowledge_engine.store.knowledge_store import KnowledgeStore

    store = KnowledgeStore()
    items = await store.list_items(workspace_id, limit, offset, source_type)
    total = await store.get_item_count(workspace_id)

    return KnowledgeListResponse(
        workspace_id=workspace_id,
        items=[
            KnowledgeListItemResponse(
                id=i["id"],
                source_url=i["source_url"],
                source_provider=i["source_provider"],
                title=i.get("title"),
                content_preview=(i.get("content") or "")[:200],
                fetched_at=str(i.get("fetched_at")) if i.get("fetched_at") else None,
                created_at=str(i.get("created_at")) if i.get("created_at") else None,
                source_type=i.get("source_type"),
                original_filename=i.get("original_filename"),
                language=i.get("language"),
            )
            for i in items
        ],
        total=total,
        offset=offset,
        limit=limit,
    )


# ── Multi-Language Endpoints ─────────────────────────────────────────────────


@router.post("/knowledge/language/detect", response_model=LanguageDetectResponse)
async def detect_language(
    request: LanguageDetectRequest,
    user: CurrentUser = None,
    _: RateLimit = None,
):
    """Detect the language of text using langdetect."""
    from app.knowledge_engine.multilingual.detector import LanguageDetector

    detector = LanguageDetector()
    result = detector.detect(request.text)

    return LanguageDetectResponse(
        detection=LanguageDetectionResult(
            language=result.language,
            language_name=result.language_name,
            confidence=result.confidence,
        ),
        all_detections=result.all_detections or [],
    )


@router.post("/knowledge/language/translate", response_model=TranslateResponse)
async def translate_text(
    request: TranslateRequest,
    user: CurrentUser = None,
    _: RateLimit = None,
):
    """Translate text between languages using argostranslate."""
    from app.knowledge_engine.multilingual.translator import LanguageTranslator

    translator = LanguageTranslator()
    result = translator.translate(
        text=request.text,
        target_language=request.target_language,
        source_language=request.source_language,
    )

    return TranslateResponse(
        translated_text=result.translated_text,
        source_language=result.source_language,
        target_language=result.target_language,
        original_length=result.original_length,
        translated_length=result.translated_length,
        success=result.success,
        error=result.error,
    )


@router.post("/knowledge/language/embed", response_model=MultilingualEmbedResponse)
async def multilingual_embed(
    request: MultilingualEmbedRequest,
    user: CurrentUser = None,
    _: RateLimit = None,
):
    """Generate multilingual embeddings for cross-lingual semantic search."""
    from app.knowledge_engine.multilingual.multilingual_embedder import MultilingualEmbedder

    embedder = MultilingualEmbedder(model_name=request.model)
    results = embedder.embed_batch(request.texts)

    return MultilingualEmbedResponse(
        embeddings=[r.embedding for r in results],
        dimension=results[0].dimension if results else 0,
        model=results[0].model if results else "",
        count=len(results),
    )


# ── Workflow Endpoints ───────────────────────────────────────────────────────


@router.get("/knowledge/workflows/definitions", response_model=list[WorkflowDefinitionResponse])
async def list_workflow_definitions(
    user: CurrentUser = None,
    _: RateLimit = None,
):
    """List all available workflow definitions."""
    from app.knowledge_engine.workflows.definitions import get_workflow_definitions

    defs = get_workflow_definitions()
    return [
        WorkflowDefinitionResponse(
            name=d.name,
            description=d.description,
            category=d.category,
            tags=d.tags,
            step_count=len(d.steps),
            steps=[{"id": s.step_id, "name": s.name, "depends_on": s.depends_on} for s in d.steps],
        )
        for d in defs
    ]


@router.post("/knowledge/workflows/run", response_model=WorkflowRunResponse)
async def run_workflow(
    request: WorkflowRunRequest,
    user: CurrentUser,
    _: RateLimit = None,
):
    """Run a knowledge workflow by name."""
    import uuid
    from app.knowledge_engine.workflows.engine import WorkflowEngine
    from app.knowledge_engine.workflows.definitions import get_workflow_definitions

    engine = WorkflowEngine()
    defs = {d.name: d for d in get_workflow_definitions()}

    if request.workflow_name not in defs:
        raise HTTPException(status_code=404, detail=f"Workflow '{request.workflow_name}' not found")

    wf_def = defs[request.workflow_name]

    # Build initial inputs
    initial = request.initial_inputs or {}
    if request.topic:
        initial["topic"] = request.topic
    if request.technologies:
        initial["technologies"] = request.technologies

    workflow_id = str(uuid.uuid4())

    result = await engine.execute(
        workflow_id=workflow_id,
        workflow_name=wf_def.name,
        steps=wf_def.steps,
        initial_inputs=initial,
        workspace_id=request.workspace_id,
    )

    return WorkflowRunResponse(
        workflow_id=result.workflow_id,
        workflow_name=result.workflow_name,
        status=result.status.value,
        step_results={
            k: WorkflowStepResult(
                step_id=v.step_id,
                status=v.status.value,
                output=v.output,
                error=v.error,
                duration_ms=v.duration_ms,
            )
            for k, v in result.step_results.items()
        },
        outputs=result.outputs,
        total_duration_ms=result.total_duration_ms,
        error=result.error,
    )


@router.get("/knowledge/workflows/status/{workflow_id}", response_model=WorkflowStatusResponse)
async def get_workflow_status(
    workflow_id: str,
    user: CurrentUser = None,
    _: RateLimit = None,
):
    """Get the status of a running workflow."""
    from app.knowledge_engine.workflows.engine import WorkflowEngine

    engine = WorkflowEngine()
    result = await engine.get_status(workflow_id)

    if not result:
        raise HTTPException(status_code=404, detail="Workflow not found or already completed")

    return WorkflowStatusResponse(
        workflow_id=result.workflow_id,
        status=result.status.value,
        step_results={
            k: WorkflowStepResult(
                step_id=v.step_id,
                status=v.status.value,
                output=v.output,
                error=v.error,
                duration_ms=v.duration_ms,
            )
            for k, v in result.step_results.items()
        },
        error=result.error,
    )


# ── Marketplace Endpoints ────────────────────────────────────────────────────


@router.post("/knowledge/marketplace/export", response_model=BundleExportResponse)
async def export_bundle(
    request: BundleExportRequest,
    user: CurrentUser,
    _: RateLimit = None,
):
    """Export workspace knowledge as a portable bundle."""
    from app.knowledge_engine.marketplace.bundle import BundleManager

    manager = BundleManager()
    bundle = await manager.export_bundle(
        workspace_id=request.workspace_id,
        name=request.name,
        description=request.description,
        tags=request.tags,
        include_embeddings=request.include_embeddings,
    )

    return BundleExportResponse(
        bundle_id=bundle.bundle_id,
        name=bundle.name,
        description=bundle.description,
        version=bundle.version,
        item_count=bundle.item_count,
        checksum=bundle.checksum,
        bundle_json=manager.serialize_bundle(bundle),
    )


@router.post("/knowledge/marketplace/import", response_model=BundleImportResponse)
async def import_bundle(
    request: BundleImportRequest,
    user: CurrentUser,
    _: RateLimit = None,
):
    """Import a knowledge bundle into a workspace."""
    from app.knowledge_engine.marketplace.bundle import BundleManager

    manager = BundleManager()
    bundle = manager.deserialize_bundle(request.bundle_json)
    result = await manager.import_bundle(
        workspace_id=request.workspace_id,
        bundle=bundle,
        skip_existing=request.skip_existing,
    )

    return BundleImportResponse(
        success=result.success,
        bundle_id=result.bundle_id,
        items_imported=result.items_imported,
        items_skipped=result.items_skipped,
        errors=result.errors,
    )


@router.get("/knowledge/marketplace/templates", response_model=TemplateListResponse)
async def list_templates(
    user: CurrentUser = None,
    _: RateLimit = None,
):
    """List available knowledge templates."""
    from app.knowledge_engine.marketplace.templates import get_templates

    templates = get_templates()
    return TemplateListResponse(
        templates=[
            TemplateSummary(
                template_id=t.template_id,
                name=t.name,
                description=t.description,
                category=t.category,
                tags=t.tags,
                item_count=len(t.items),
                author=t.author,
            )
            for t in templates
        ]
    )


@router.post("/knowledge/marketplace/templates/import", response_model=BundleImportResponse)
async def import_template(
    request: TemplateImportRequest,
    user: CurrentUser,
    _: RateLimit = None,
):
    """Import a knowledge template into a workspace."""
    from app.knowledge_engine.marketplace.bundle import BundleManager
    from app.knowledge_engine.marketplace.templates import get_templates

    templates = {t.template_id: t for t in get_templates()}
    template = templates.get(request.template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template '{request.template_id}' not found")

    # Convert template to bundle
    from app.knowledge_engine.marketplace.bundle import KnowledgeBundle
    bundle = KnowledgeBundle(
        bundle_id=f"template-{template.template_id}",
        name=template.name,
        description=template.description,
        version=template.version,
        author=template.author,
        created_at=time.time(),
        items=template.items,
        metadata={"template_id": template.template_id, "category": template.category},
        tags=template.tags,
        item_count=len(template.items),
        checksum="",
    )

    manager = BundleManager()
    result = await manager.import_bundle(
        workspace_id=request.workspace_id,
        bundle=bundle,
    )

    return BundleImportResponse(
        success=result.success,
        bundle_id=result.bundle_id,
        items_imported=result.items_imported,
        items_skipped=result.items_skipped,
        errors=result.errors,
    )


def _extract_facts(text: str) -> list[dict]:
    """Extract factual statements from text."""
    import re
    facts = []

    patterns = [
        (r"(?:The|This|That)\s+(.+?)\s+(?:is|are|was|were)\s+(.+?)(?:\.|$)", "definition"),
        (r"(?:I(?:'m| am)|My name is)\s+(.+?)(?:\.|$)", "identity"),
        (r"(?:I use|We use|I prefer|I like)\s+(.+?)(?:\s+for\s+(.+?))?(?:\.|$)", "preference"),
        (r"(?:The (?:version|latest version) of .+? is)\s+(.+?)(?:\.|$)", "version"),
    ]

    for pattern, fact_type in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            groups = match.groups()
            fact_content = " ".join(g for g in groups if g).strip()
            if len(fact_content) > 10:
                facts.append({
                    "type": fact_type,
                    "title": fact_content[:100],
                    "content": fact_content,
                    "key": f"{fact_type}:{fact_content[:50]}",
                })

    return facts[:5]


def _extract_decisions(text: str) -> list[dict]:
    """Extract technical decisions from text."""
    import re
    decisions = []

    patterns = [
        r"(?:we(?:'ll| will| should)|I(?:'ll| will| would))\s+(?:use|go with|choose|implement|build)\s+(.+?)(?:\.|$)",
        r"(?:decided|decision)\s+(?:to|on)\s+(.+?)(?:\.|$)",
        r"(?:recommended|suggest)\s+(?:using|to use)\s+(.+?)(?:\.|$)",
    ]

    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            decision = match.group(1).strip()
            if len(decision) > 10:
                decisions.append({
                    "type": "decision",
                    "title": decision[:100],
                    "content": decision,
                    "key": f"decision:{decision[:50]}",
                })

    return decisions[:3]


# ── Project Docs Seeding ─────────────────────────────────────────────────────


@router.post("/seed-project-docs", response_model=dict)
async def seed_project_docs(
    workspace_id: str,
    user: JWTPayload = Depends(get_current_user),  # noqa: B008
):
    """Seed Kraivor project documentation into the knowledge engine.

    Call this when a workspace is first created so the AI always knows
    what Kraivor is. Safe to call multiple times (idempotent).
    """
    check_rate_limit(user.sub, "knowledge.seed", max_requests=5, window_seconds=60)

    try:
        from app.application.tasks.knowledge import seed_kraivor_project_docs
        result = seed_kraivor_project_docs.delay(workspace_id=workspace_id)
        return {
            "status": "queued",
            "task_id": result.id,
            "workspace_id": workspace_id,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "workspace_id": workspace_id,
        }
