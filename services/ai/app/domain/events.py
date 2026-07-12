from dataclasses import dataclass, field

from datetime import datetime


@dataclass
class DomainEvent:
    event_id: str = ""
    event_type: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AnalysisCompletedEvent(DomainEvent):
    event_type: str = "analysis.completed"
    analysis_id: str = ""
    repo_id: str = ""
    workspace_id: str = ""
    findings: list[dict] | None = None


@dataclass
class IndexJobCompletedEvent(DomainEvent):
    event_type: str = "indexing.completed"
    repo_id: str = ""
    workspace_id: str = ""
    files_indexed: int = 0
    chunks_created: int = 0
