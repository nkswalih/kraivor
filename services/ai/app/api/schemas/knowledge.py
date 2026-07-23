"""Knowledge API schemas — request/response models for the knowledge endpoints."""

from pydantic import BaseModel, Field


class KnowledgeIndexRequest(BaseModel):
    """Index a single knowledge item into the persistent knowledge base."""

    workspace_id: str = Field(..., description="Workspace ID to store knowledge for")
    source_url: str = Field(..., description="The source URL of the knowledge")
    source_provider: str = Field("manual", description="Source provider (web, docs, github, manual)")
    title: str = Field(..., description="Descriptive title for this knowledge item")
    content: str = Field(..., description="The knowledge content to store")
    trust_score: float = Field(0.7, ge=0.0, le=1.0, description="Trust score for this source")
    summary: str | None = Field(None, description="Optional brief summary")
    metadata: dict | None = Field(None, description="Optional metadata")


class KnowledgeIndexResponse(BaseModel):
    """Response after indexing a knowledge item."""

    id: str = Field(..., description="The stored knowledge item ID")
    workspace_id: str
    source_url: str
    status: str = "indexed"


class KnowledgeBatchIndexRequest(BaseModel):
    """Index multiple knowledge items at once."""

    workspace_id: str = Field(..., description="Workspace ID to store knowledge for")
    items: list[KnowledgeIndexRequest] = Field(..., min_length=1, max_length=50, description="Knowledge items to index")


class KnowledgeBatchIndexResponse(BaseModel):
    """Response after batch indexing."""

    indexed_count: int
    workspace_id: str
    status: str = "batch_indexed"


class KnowledgeSearchRequest(BaseModel):
    """Search stored knowledge."""

    workspace_id: str = Field(..., description="Workspace ID to search within")
    query: str = Field(..., min_length=1, description="Search query")
    top_k: int = Field(5, ge=1, le=20, description="Number of results to return")
    providers: list[str] | None = Field(None, description="Filter by source providers")


class KnowledgeSearchResult(BaseModel):
    """A single search result."""

    source: str
    title: str
    provider: str
    trust_score: float
    content: str
    summary: str | None = None
    similarity: float
    metadata: dict | None = None


class KnowledgeSearchResponse(BaseModel):
    """Response from knowledge search."""

    query: str
    results: list[KnowledgeSearchResult]
    total: int


class KnowledgeStatsResponse(BaseModel):
    """Knowledge base statistics for a workspace."""

    workspace_id: str
    total_items: int
    unique_urls: int
    providers: int
    avg_trust: float
    oldest: str | None = None
    newest: str | None = None


class CanvasIndexRequest(BaseModel):
    """Index knowledge from a KnowledgeSpace canvas."""

    workspace_id: str = Field(..., description="Workspace ID")
    knowledge_space_id: str = Field(..., description="Knowledge space ID")
    canvas_data: dict = Field(..., description="The canvas_data JSON from the knowledge space")
    knowledge_space_name: str = Field("Untitled", description="Name of the knowledge space")


class CanvasIndexResponse(BaseModel):
    """Response after indexing canvas content."""

    workspace_id: str
    knowledge_space_id: str
    indexed_count: int
    elements_processed: int
    status: str = "canvas_indexed"


class ConversationKnowledgeRequest(BaseModel):
    """Extract and index knowledge from a conversation."""

    workspace_id: str = Field(..., description="Workspace ID")
    conversation_id: str = Field(..., description="Conversation ID to extract from")
    messages: list[dict] = Field(..., description="Conversation messages (role, content)")


class ConversationKnowledgeResponse(BaseModel):
    """Response after extracting conversation knowledge."""

    workspace_id: str
    conversation_id: str
    extracted_count: int
    facts: list[dict] = Field(default_factory=list)
    status: str = "extracted"


# ── Knowledge Graph Schemas ──────────────────────────────────────────────────


class GraphEntityResponse(BaseModel):
    """A single entity from the knowledge graph."""

    name: str
    type: str
    mentions: int
    first_seen: str | None = None
    last_seen: str | None = None


class GraphRelatedEntity(BaseModel):
    """A related entity in the graph."""

    entity: str
    relationship: str
    weight: float
    path_count: int


class GraphStatsResponse(BaseModel):
    """Knowledge graph statistics."""

    workspace_id: str
    entities: int
    entity_types: int
    relationships: int
    relationship_types: int


class GraphFindRelatedRequest(BaseModel):
    """Find entities related to a given entity."""

    workspace_id: str
    entity_name: str = Field(..., min_length=1, description="Entity to find relations for")
    max_depth: int = Field(2, ge=1, le=4, description="Max traversal depth")


class GraphFindRelatedResponse(BaseModel):
    """Response from graph relation query."""

    entity: str
    related: list[GraphRelatedEntity]
    total: int


# ── Knowledge Quality Schemas ────────────────────────────────────────────────


class QualityItem(BaseModel):
    """A quality-tracked knowledge item."""

    item_id: str
    title: str
    url: str
    provider: str
    trust_score: float
    references: int
    avg_rank: float
    quality_score: float


class QualityStatsResponse(BaseModel):
    """Quality statistics for a workspace."""

    workspace_id: str
    total_tracked: int
    avg_quality: float
    max_quality: float
    total_references: int
    avg_references: float


class QualityTopItemsResponse(BaseModel):
    """Top quality knowledge items."""

    workspace_id: str
    items: list[QualityItem]
    total: int


# ── Proactive Learning Schemas ──────────────────────────────────────────────


class ProactiveLearningResponse(BaseModel):
    """Response from proactive learning cycle."""

    workspace_id: str
    technologies: list[str]
    new_releases: int
    security_advisories: int
    stale_docs: int
    items_indexed: int
    status: str = "completed"


# ── Conflict Resolution Schemas ──────────────────────────────────────────────


class ConflictClaim(BaseModel):
    content: str
    source_url: str
    source_provider: str
    trust_score: float


class ConflictGroupResponse(BaseModel):
    topic: str
    conflict_type: str
    claims: list[ConflictClaim]
    resolution: str | None = None
    confidence: float = 0.0


class ConflictResolutionRequest(BaseModel):
    workspace_id: str
    topic: str = Field(..., min_length=1, description="Topic to check for conflicts")
    max_sources: int = Field(10, ge=2, le=20)


class ConflictResolutionResponse(BaseModel):
    topic: str
    conflicts_found: int
    groups: list[ConflictGroupResponse]
    resolution_summary: str
    sources_consulted: int


# ── Summarization Schemas ────────────────────────────────────────────────────


class SummarizeTopicRequest(BaseModel):
    workspace_id: str
    topic: str = Field(..., min_length=1)
    max_items: int = Field(10, ge=1, le=30)


class SummarizeWorkspaceRequest(BaseModel):
    workspace_id: str


class SummarizeSourceRequest(BaseModel):
    workspace_id: str
    provider: str = Field(..., min_length=1)
    max_items: int = Field(10, ge=1, le=30)


class SummaryResponse(BaseModel):
    summary: str
    sources_count: int = 0
    key_points: list[str] = Field(default_factory=list)
    sources: list[dict] = Field(default_factory=list)


# ── Feedback Schemas ─────────────────────────────────────────────────────────


class FeedbackRequest(BaseModel):
    workspace_id: str
    item_id: str = Field(..., min_length=1)
    rating: str = Field(..., pattern=r"^(helpful|not_helpful|partially_helpful|outdated|incorrect)$")
    conversation_id: str | None = None
    comment: str | None = None


class FeedbackResponse(BaseModel):
    status: str = "recorded"
    item_id: str
    rating: str


class FeedbackSummaryResponse(BaseModel):
    workspace_id: str
    total_feedback: int
    ratings: dict[str, int]
    helpful_rate: float
    most_helpful: list[dict] = Field(default_factory=list)
    needs_improvement: list[dict] = Field(default_factory=list)


# ── Deduplication Schemas ────────────────────────────────────────────────────


class DedupRequest(BaseModel):
    workspace_id: str
    threshold: float = Field(0.85, ge=0.5, le=1.0)
    dry_run: bool = Field(True, description="If true, only report duplicates without removing")


class DedupResponse(BaseModel):
    duplicate_groups: int
    items_to_remove: int
    items_removed: int
    dry_run: bool
    workspace_id: str


# ── Versioning Schemas ───────────────────────────────────────────────────────


class VersionHistoryResponse(BaseModel):
    workspace_id: str
    item_id: str
    versions: list[dict]
    total: int


class VersionStatsResponse(BaseModel):
    workspace_id: str
    versioned_items: int
    total_versions: int
    max_version: int
    oldest_snapshot: str | None = None
    newest_snapshot: str | None = None


class RevertRequest(BaseModel):
    workspace_id: str
    item_id: str = Field(..., min_length=1)
    version: int = Field(..., ge=1)


class RevertResponse(BaseModel):
    status: str
    item_id: str
    reverted_to_version: int


# ── Export Schemas ────────────────────────────────────────────────────────────


class ExportRequest(BaseModel):
    workspace_id: str
    include_embeddings: bool = False
    include_versions: bool = False
    include_feedback: bool = False
    include_graph: bool = False


class ExportResponse(BaseModel):
    version: str
    workspace_id: str
    exported_at: str
    item_count: int
    items: list[dict]
    stats: dict
    graph: dict | None = None
    versions: list[dict] | None = None
    feedback: list[dict] | None = None


# ── Health Dashboard Schemas ─────────────────────────────────────────────────


class HealthBreakdown(BaseModel):
    coverage: int
    freshness: int
    quality: int
    diversity: int


class HealthOverall(BaseModel):
    score: int
    grade: str
    breakdown: HealthBreakdown


class HealthReportResponse(BaseModel):
    workspace_id: str
    generated_at: str
    overall_health: HealthOverall
    stats: dict
    freshness: dict
    quality_distribution: dict
    provider_distribution: list[dict]
    gaps: list[dict]
    recommendations: list[str]


# ── Monitoring Schemas ───────────────────────────────────────────────────────


class QueryStatsResponse(BaseModel):
    workspace_id: str
    total_queries: int
    cache_hits: int
    cache_hit_rate: float
    errors: int
    error_rate: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    max_latency_ms: float
    total_sources_fetched: int
    period_hours: int


class SourceReliabilityResponse(BaseModel):
    workspace_id: str
    providers: list[dict]
    period_hours: int


class UsageTimelineResponse(BaseModel):
    workspace_id: str
    buckets: list[dict]
    period_hours: int


class TopQueriesResponse(BaseModel):
    workspace_id: str
    queries: list[dict]


# ── Cache Schemas ─────────────────────────────────────────────────────────────


class CacheStatsResponse(BaseModel):
    workspace_id: str
    total_entries: int
    active_entries: int
    expired_entries: int
    total_hits: int
    avg_hits: float
    total_size_kb: float


class CacheInvalidateRequest(BaseModel):
    workspace_id: str
    cache_type: str | None = None


class CacheInvalidateResponse(BaseModel):
    workspace_id: str
    entries_removed: int
    status: str = "invalidated"


# ── Refresh Pipeline Schemas ─────────────────────────────────────────────────


class RefreshStatsResponse(BaseModel):
    workspace_id: str
    total_items: int
    stale_items: int
    refreshed_today: int
    refreshed_this_week: int
    oldest_item: str | None = None
    newest_item: str | None = None
    stale_threshold_days: int


class RefreshRequest(BaseModel):
    workspace_id: str
    stale_days: int | None = Field(None, ge=7, le=365)
    max_items: int | None = Field(None, ge=1, le=50)


class RefreshResponse(BaseModel):
    workspace_id: str
    stale_found: int
    refreshed: int
    failed: int
    total_latency_ms: float
    status: str


# ── Advanced Search Schemas ──────────────────────────────────────────────────


class AdvancedSearchRequest(BaseModel):
    workspace_id: str
    query: str = Field(..., min_length=1)
    top_k: int = Field(10, ge=1, le=50)
    providers: list[str] | None = None
    min_trust: float = Field(0.0, ge=0.0, le=1.0)
    created_after: str | None = None
    created_before: str | None = None
    min_content_length: int = Field(0, ge=0)


class AdvancedSearchResult(BaseModel):
    id: str
    source_url: str
    provider: str
    trust_score: float
    title: str
    content: str
    summary: str | None = None
    text_rank: float
    recency_score: float
    composite_score: float
    fetched_at: str | None = None


class AdvancedSearchResponse(BaseModel):
    query: str
    results: list[AdvancedSearchResult]
    total: int
    filters_applied: dict


# ── Multi-Modal Ingestion Schemas ───────────────────────────────────────────


class MultiModalIngestFileRequest(BaseModel):
    """Ingest a file (PDF, image, or audio) into knowledge base."""
    workspace_id: str = Field(..., description="Workspace ID to store knowledge for")
    tags: list[str] = Field(default_factory=list, description="Optional tags")
    language: str | None = Field(None, description="Override language detection")


class MultiModalIngestFileResponse(BaseModel):
    """Response after ingesting a file."""
    success: bool
    source_type: str
    title: str | None = None
    total_characters: int = 0
    chunk_count: int = 0
    knowledge_ids: list[str] = Field(default_factory=list)
    language: str | None = None
    metadata: dict = Field(default_factory=dict)
    error: str | None = None


class MultiModalIngestUrlRequest(BaseModel):
    """Ingest content from a URL (auto-detects type)."""
    workspace_id: str = Field(..., description="Workspace ID")
    url: str = Field(..., description="URL to fetch and ingest")
    tags: list[str] = Field(default_factory=list, description="Optional tags")


class MultiModalIngestBatchRequest(BaseModel):
    """Batch ingestion is handled via multipart/form-data, but this defines the metadata."""
    workspace_id: str = Field(..., description="Workspace ID")
    tags: list[str] = Field(default_factory=list, description="Optional tags")


class MultiModalIngestTextRequest(BaseModel):
    """Ingest raw text content."""
    workspace_id: str = Field(..., description="Workspace ID")
    text: str = Field(..., min_length=1, description="Text content to ingest")
    title: str | None = Field(None, description="Title for the text")
    source_url: str | None = Field(None, description="Optional source URL")
    tags: list[str] = Field(default_factory=list, description="Optional tags")
    language: str | None = Field(None, description="Language override")


class MultiModalIngestTextResponse(BaseModel):
    """Response after ingesting text content."""
    success: bool
    source_type: str = "text"
    title: str | None = None
    total_characters: int = 0
    chunk_count: int = 0
    knowledge_ids: list[str] = Field(default_factory=list)
    language: str | None = None
    error: str | None = None


class MultiModalSupportedTypesResponse(BaseModel):
    """Response listing supported file types."""
    pdf: list[str]
    image: list[str]
    audio: list[str]


class KnowledgeListItemResponse(BaseModel):
    """A knowledge item in list view."""
    id: str
    source_url: str
    source_provider: str
    title: str | None = None
    content_preview: str = ""
    fetched_at: str | None = None
    created_at: str | None = None
    source_type: str | None = None
    original_filename: str | None = None
    language: str | None = None


class KnowledgeListResponse(BaseModel):
    """Response for listing knowledge items."""
    workspace_id: str
    items: list[KnowledgeListItemResponse]
    total: int
    offset: int
    limit: int


# ── Multi-Language Schemas ───────────────────────────────────────────────────


class LanguageDetectRequest(BaseModel):
    """Detect the language of text."""
    text: str = Field(..., min_length=1, max_length=5000, description="Text to detect language for")


class LanguageDetectionResult(BaseModel):
    """A single language detection result."""
    language: str
    language_name: str
    confidence: float


class LanguageDetectResponse(BaseModel):
    """Response from language detection."""
    detection: LanguageDetectionResult
    all_detections: list[dict] = Field(default_factory=list)


class TranslateRequest(BaseModel):
    """Translate text between languages."""
    text: str = Field(..., min_length=1, max_length=10000, description="Text to translate")
    target_language: str = Field(..., description="Target language code (e.g., 'en', 'es', 'fr')")
    source_language: str | None = Field(None, description="Source language code (auto-detected if None)")


class TranslateResponse(BaseModel):
    """Response from translation."""
    translated_text: str
    source_language: str
    target_language: str
    original_length: int
    translated_length: int
    success: bool
    error: str | None = None


class MultilingualEmbedRequest(BaseModel):
    """Generate multilingual embeddings for text."""
    texts: list[str] = Field(..., min_length=1, max_length=100, description="Texts to embed")
    model: str | None = Field(None, description="Model override")


class MultilingualEmbedResponse(BaseModel):
    """Response from multilingual embedding."""
    embeddings: list[list[float]]
    dimension: int
    model: str
    count: int


# ── Workflow Schemas ─────────────────────────────────────────────────────────


class WorkflowStepResult(BaseModel):
    """Result from a single workflow step."""
    step_id: str
    status: str
    output: dict = Field(default_factory=dict)
    error: str | None = None
    duration_ms: float = 0.0


class WorkflowDefinitionResponse(BaseModel):
    """A workflow definition."""
    name: str
    description: str
    category: str
    tags: list[str]
    step_count: int
    steps: list[dict]


class WorkflowRunRequest(BaseModel):
    """Run a workflow by name or custom definition."""
    workspace_id: str
    workflow_name: str | None = Field(None, description="Pre-built workflow name")
    topic: str | None = Field(None, description="Topic for research workflows")
    technologies: list[str] | None = Field(None, description="Technologies to compare")
    initial_inputs: dict | None = Field(None, description="Custom initial inputs")


class WorkflowRunResponse(BaseModel):
    """Response after running a workflow."""
    workflow_id: str
    workflow_name: str
    status: str
    step_results: dict[str, WorkflowStepResult]
    outputs: dict
    total_duration_ms: float
    error: str | None = None


class WorkflowStatusResponse(BaseModel):
    """Status of a running workflow."""
    workflow_id: str
    status: str
    step_results: dict[str, WorkflowStepResult]
    error: str | None = None


# ── Marketplace Schemas ──────────────────────────────────────────────────────


class BundleExportRequest(BaseModel):
    """Export workspace knowledge as a bundle."""
    workspace_id: str
    name: str | None = Field(None, description="Bundle name")
    description: str | None = Field(None, description="Bundle description")
    tags: list[str] = Field(default_factory=list)
    include_embeddings: bool = Field(False, description="Include vector embeddings")


class BundleExportResponse(BaseModel):
    """Response from bundle export."""
    bundle_id: str
    name: str
    description: str
    version: str
    item_count: int
    checksum: str
    bundle_json: str = Field(..., description="Serialized bundle as JSON string")


class BundleImportRequest(BaseModel):
    """Import a knowledge bundle into a workspace."""
    workspace_id: str
    bundle_json: str = Field(..., description="Serialized bundle JSON")
    skip_existing: bool = Field(True, description="Skip items that already exist")


class BundleImportResponse(BaseModel):
    """Response from bundle import."""
    success: bool
    bundle_id: str
    items_imported: int
    items_skipped: int
    errors: list[str] = Field(default_factory=list)


class TemplateSummary(BaseModel):
    """Summary of a knowledge template."""
    template_id: str
    name: str
    description: str
    category: str
    tags: list[str]
    item_count: int
    author: str


class TemplateListResponse(BaseModel):
    """List of available knowledge templates."""
    templates: list[TemplateSummary]


class TemplateImportRequest(BaseModel):
    """Import a template into a workspace."""
    workspace_id: str
    template_id: str = Field(..., description="Template ID to import")
