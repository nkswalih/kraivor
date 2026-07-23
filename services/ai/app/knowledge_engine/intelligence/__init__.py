"""Intelligence Layer — conflict resolution, summarization, feedback, dedup, versioning, export, health."""

from .conflict_resolver import ConflictResolver
from .summarizer import KnowledgeSummarizer
from .feedback import FeedbackTracker
from .deduplicator import SemanticDeduplicator
from .versioning import KnowledgeVersioning
from .exporter import KnowledgeExporter
from .health_dashboard import KnowledgeHealthDashboard

__all__ = [
    "ConflictResolver",
    "KnowledgeSummarizer",
    "FeedbackTracker",
    "SemanticDeduplicator",
    "KnowledgeVersioning",
    "KnowledgeExporter",
    "KnowledgeHealthDashboard",
]
