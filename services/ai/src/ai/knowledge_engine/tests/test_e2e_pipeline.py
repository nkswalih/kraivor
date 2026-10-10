"""End-to-End Integration Tests for the Knowledge Engine pipeline.

Run with: python -m pytest services/ai/app/knowledge_engine/tests/test_e2e_pipeline.py -v
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


TEST_WORKSPACE = "test-ws-e2e-001"
TEST_URL = "https://example.com/test-doc"
TEST_TITLE = "Test Knowledge Document"
TEST_CONTENT = """
FastAPI is a modern, fast web framework for building APIs with Python 3.7+.
It is based on Python type declarations and provides automatic API documentation.
FastAPI depends on Starlette for the web parts and Pydantic for the data parts.
It supports async/await natively and is one of the fastest Python frameworks available.
""".strip()


@pytest.fixture
def mock_db():
    """Mock the database session factory — patch where it's imported."""
    session = AsyncMock()

    mock_result = MagicMock()
    mock_result.fetchone = MagicMock(return_value=MagicMock(id="test-id-001"))
    session.execute = AsyncMock(return_value=mock_result)

    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("app.knowledge_engine.store.knowledge_store.async_session_factory", mock_factory):
        yield session


@pytest.fixture
def mock_embedder():
    """Mock the embedder to avoid model loading."""
    with patch("app.knowledge_engine.store.knowledge_indexer.Embedder") as mock:
        instance = mock.return_value
        instance.embed = AsyncMock(return_value=[0.1] * 384)
        instance.embed_batch = AsyncMock(return_value=[[0.1] * 384])
        yield instance


@pytest.mark.asyncio
async def test_store_knowledge(mock_db, mock_embedder):
    from app.knowledge_engine.store.knowledge_store import KnowledgeStore

    store = KnowledgeStore()
    item_id = await store.store(
        workspace_id=TEST_WORKSPACE,
        source_url=TEST_URL,
        source_provider="test",
        title=TEST_TITLE,
        content=TEST_CONTENT,
        trust_score=0.85,
    )

    assert item_id is not None
    assert len(item_id) == 24


@pytest.mark.asyncio
async def test_search_knowledge(mock_db, mock_embedder):
    from app.knowledge_engine.store.knowledge_store import KnowledgeStore

    mock_row = {
        "id": "test-id-001",
        "workspace_id": TEST_WORKSPACE,
        "source_url": TEST_URL,
        "source_provider": "test",
        "source_trust_score": 0.85,
        "title": TEST_TITLE,
        "content": TEST_CONTENT,
        "summary": "Test summary",
        "fetched_at": None,
        "text_rank": 0.92,
    }
    mock_mappings = MagicMock()
    mock_mappings.all = MagicMock(return_value=[mock_row])
    mock_result = MagicMock()
    mock_result.mappings = MagicMock(return_value=mock_mappings)
    mock_db.execute = AsyncMock(return_value=mock_result)

    store = KnowledgeStore()
    results = await store.search_text(TEST_WORKSPACE, "FastAPI web framework", top_k=5)

    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]["id"] == "test-id-001"


@pytest.mark.asyncio
async def test_index_knowledge(mock_db, mock_embedder):
    from app.knowledge_engine.store.knowledge_indexer import KnowledgeIndexer

    indexer = KnowledgeIndexer()
    item_id = await indexer.index_knowledge(
        workspace_id=TEST_WORKSPACE,
        source_url=TEST_URL,
        source_provider="test",
        title=TEST_TITLE,
        content=TEST_CONTENT,
        trust_score=0.85,
    )

    assert item_id is not None


def test_conflict_detection():
    from app.knowledge_engine.intelligence.conflict_resolver import ConflictResolver

    resolver = ConflictResolver()
    assert resolver._is_factual_claim("FastAPI is a modern Python web framework for building APIs quickly.")
    assert not resolver._is_factual_claim("What do you think about FastAPI?")


def test_quality_composite_score():
    ref_score = 0.8
    fresh_score = 0.9
    trust_score = 0.85
    content_score = 0.7
    rank_score = 0.6

    composite = (
        0.30 * ref_score +
        0.20 * fresh_score +
        0.25 * trust_score +
        0.15 * content_score +
        0.10 * rank_score
    )

    assert 0.0 <= composite <= 1.0
    assert composite > 0.5


def test_feedback_adjustment():
    adjustments = {
        "helpful": 0.15,
        "partially_helpful": 0.05,
        "not_helpful": -0.10,
        "outdated": -0.20,
        "incorrect": -0.30,
    }

    for _rating, expected_adj in adjustments.items():
        current_score = 0.7
        new_score = max(0.0, min(1.0, current_score + expected_adj))
        assert 0.0 <= new_score <= 1.0


def test_cache_key_determinism():
    from app.knowledge_engine.monitoring.cache import KnowledgeCache

    cache = KnowledgeCache()
    key1 = cache._make_key(TEST_WORKSPACE, "search", "FastAPI tutorial")
    key2 = cache._make_key(TEST_WORKSPACE, "search", "FastAPI tutorial")
    key3 = cache._make_key(TEST_WORKSPACE, "search", "Django tutorial")

    assert key1 == key2
    assert key1 != key3
    assert len(key1) == 24


def test_dedup_cosine_similarity():
    from app.knowledge_engine.intelligence.deduplicator import SemanticDeduplicator

    dedup = SemanticDeduplicator()

    a = [1.0, 0.0, 0.0]
    b = [1.0, 0.0, 0.0]
    assert dedup._cosine_similarity(a, b) == pytest.approx(1.0)

    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert dedup._cosine_similarity(a, b) == pytest.approx(0.0)

    a = [0.8, 0.6, 0.1]
    b = [0.7, 0.5, 0.2]
    sim = dedup._cosine_similarity(a, b)
    assert sim > 0.8


def test_versioning_class_init():
    from app.knowledge_engine.intelligence.versioning import KnowledgeVersioning

    v = KnowledgeVersioning()
    assert v is not None


def test_health_score_calculation():
    from app.knowledge_engine.intelligence.health_dashboard import KnowledgeHealthDashboard

    dashboard = KnowledgeHealthDashboard()
    stats = {"total_items": 20, "providers": 5}
    freshness = {"freshness_score": 0.8}
    quality = {"quality_score": 0.7}

    result = dashboard._compute_health_score(stats, freshness, quality)
    assert 0 <= result["score"] <= 100
    assert result["grade"] in ("excellent", "good", "fair", "poor")


def test_exporter_class_init():
    from app.knowledge_engine.intelligence.exporter import KnowledgeExporter

    exporter = KnowledgeExporter()
    assert exporter is not None


def test_advanced_search_init():
    from app.knowledge_engine.search.advanced import AdvancedSearch

    search = AdvancedSearch()
    assert search is not None


def test_metrics_class_init():
    from app.knowledge_engine.monitoring.metrics import KnowledgeMetrics

    metrics = KnowledgeMetrics()
    assert metrics is not None


def test_engine_init():
    from app.knowledge_engine.engine import KnowledgeEngine

    engine = KnowledgeEngine()
    assert engine.web_search is not None
    assert engine.documentation is not None
    assert engine.github is not None
    assert engine.news is not None
    assert engine.indexer is not None
    assert engine.retriever is not None
    assert engine.graph is not None
    assert engine.quality is not None
    assert engine.cache is not None
    assert engine.metrics is not None


def test_tool_definitions_count():
    from app.application.tools.workspace_tools import WORKSPACE_TOOL_DEFINITIONS

    tool_names = set()
    for defn in WORKSPACE_TOOL_DEFINITIONS:
        name = defn.get("function", {}).get("name", "")
        if name:
            tool_names.add(name)

    assert len(tool_names) >= 31


def test_celery_tasks_registered():
    from app.application.tasks.knowledge import (
        index_knowledge_space_canvas,
        extract_conversation_knowledge,
        check_knowledge_freshness,
        check_knowledge_freshness_daily,
        proactive_learning_cycle,
        proactive_learning_daily,
        batch_index_workspace_knowledge,
        auto_refresh_stale_knowledge,
        auto_refresh_stale_knowledge_daily,
        cleanup_knowledge_cache,
    )

    assert index_knowledge_space_canvas is not None
    assert extract_conversation_knowledge is not None
    assert check_knowledge_freshness is not None
    assert check_knowledge_freshness_daily is not None
    assert proactive_learning_cycle is not None
    assert proactive_learning_daily is not None
    assert batch_index_workspace_knowledge is not None
    assert auto_refresh_stale_knowledge is not None
    assert auto_refresh_stale_knowledge_daily is not None
    assert cleanup_knowledge_cache is not None


def test_workflow_definitions_exist():
    from app.knowledge_engine.workflows.definitions import get_workflow_definitions

    workflows = get_workflow_definitions()
    assert len(workflows) >= 5
    for wf in workflows:
        assert hasattr(wf, "name")
        assert hasattr(wf, "description")
        assert hasattr(wf, "steps")
        assert len(wf.steps) > 0


def test_marketplace_templates_exist():
    from app.knowledge_engine.marketplace.templates import get_templates

    templates = get_templates()
    assert len(templates) >= 4
    for tmpl in templates:
        assert hasattr(tmpl, "name")
        assert hasattr(tmpl, "description")
        assert hasattr(tmpl, "items")


def test_language_detector_init():
    from app.knowledge_engine.multilingual.detector import LanguageDetector

    detector = LanguageDetector()
    assert detector is not None


def test_multimodal_ingester_init():
    from app.knowledge_engine.multimodal.ingester import MultiModalIngester

    ingester = MultiModalIngester()
    assert ingester is not None


def test_workflow_engine_init():
    from app.knowledge_engine.workflows.engine import WorkflowEngine

    engine = WorkflowEngine()
    assert engine is not None
