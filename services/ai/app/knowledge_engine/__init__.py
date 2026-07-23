"""Knowledge Engine — retrieves, ranks, and delivers verified knowledge to agents."""

from .engine import KnowledgeEngine, ResearchResult
from .store import KnowledgeStore, KnowledgeIndexer, KnowledgeRetriever
from .graph import KnowledgeGraph
from .quality import KnowledgeQualityScorer
from .learning import ProactiveLearningPipeline
from .intelligence import (
    ConflictResolver,
    KnowledgeSummarizer,
    FeedbackTracker,
    SemanticDeduplicator,
    KnowledgeVersioning,
    KnowledgeExporter,
    KnowledgeHealthDashboard,
)
from .monitoring import KnowledgeMetrics, KnowledgeCache, KnowledgeRefreshPipeline
from .search import AdvancedSearch

__all__ = [
    "KnowledgeEngine",
    "ResearchResult",
    "KnowledgeStore",
    "KnowledgeIndexer",
    "KnowledgeRetriever",
    "KnowledgeGraph",
    "KnowledgeQualityScorer",
    "ProactiveLearningPipeline",
    "ConflictResolver",
    "KnowledgeSummarizer",
    "FeedbackTracker",
    "SemanticDeduplicator",
    "KnowledgeVersioning",
    "KnowledgeExporter",
    "KnowledgeHealthDashboard",
    "KnowledgeMetrics",
    "KnowledgeCache",
    "KnowledgeRefreshPipeline",
    "AdvancedSearch",
]
