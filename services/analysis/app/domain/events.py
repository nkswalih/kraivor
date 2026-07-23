from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(kw_only=True)
class DomainEvent:
    """Base domain event."""

    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    event_type: str = ""
    version: int = 1

    def to_dict(self) -> dict[str, object]:
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
            "version": self.version,
        }


@dataclass(kw_only=True)
class AnalysisRequested(DomainEvent):
    event_type: str = "analysis.requested"
    job_id: UUID
    repo_id: UUID
    workspace_id: UUID
    triggered_by: UUID
    trigger_type: str
    branch: str
    deep_scan: bool

    def to_dict(self) -> dict[str, object]:
        base = super().to_dict()
        base.update(
            {
                "job_id": str(self.job_id),
                "repo_id": str(self.repo_id),
                "workspace_id": str(self.workspace_id),
                "triggered_by": str(self.triggered_by),
                "trigger_type": self.trigger_type,
                "branch": self.branch,
                "deep_scan": self.deep_scan,
            }
        )
        return base


@dataclass(kw_only=True)
class AnalysisProgressed(DomainEvent):
    event_type: str = "analysis.progressed"
    job_id: UUID
    status: str
    progress_pct: int
    message: str = ""

    def to_dict(self) -> dict[str, object]:
        base = super().to_dict()
        base.update(
            {
                "job_id": str(self.job_id),
                "status": self.status,
                "progress_pct": self.progress_pct,
                "message": self.message,
            }
        )
        return base


@dataclass(kw_only=True)
class AnalysisCompleted(DomainEvent):
    event_type: str = "analysis.completed"
    job_id: UUID
    repo_id: UUID
    workspace_id: UUID
    overall_score: int | None = None
    findings_count: int = 0
    duration_seconds: int | None = None
    engine_statuses: dict[str, str] | None = None
    blocked_by: list[str] | None = None

    def to_dict(self) -> dict[str, object]:
        base = super().to_dict()
        base.update(
            {
                "job_id": str(self.job_id),
                "repo_id": str(self.repo_id),
                "workspace_id": str(self.workspace_id),
                "overall_score": self.overall_score,
                "findings_count": self.findings_count,
                "duration_seconds": self.duration_seconds,
                "engine_statuses": self.engine_statuses or {},
                "blocked_by": self.blocked_by or [],
            }
        )
        return base


@dataclass(kw_only=True)
class EngineStarted(DomainEvent):
    event_type: str = "engine.started"
    job_id: UUID
    engine_name: str
    current_step: str = "starting"

    def to_dict(self) -> dict[str, object]:
        base = super().to_dict()
        base.update(
            {
                "job_id": str(self.job_id),
                "engine_name": self.engine_name,
                "status": "running",
                "current_step": self.current_step,
            }
        )
        return base


@dataclass(kw_only=True)
class EngineProgressed(DomainEvent):
    event_type: str = "engine.progressed"
    job_id: UUID
    engine_name: str
    progress: int = 0
    current_step: str = ""
    processed_files: int = 0
    total_files: int = 0
    elapsed_time: float = 0.0

    def to_dict(self) -> dict[str, object]:
        base = super().to_dict()
        base.update(
            {
                "job_id": str(self.job_id),
                "engine_name": self.engine_name,
                "status": "running",
                "progress": self.progress,
                "current_step": self.current_step,
                "processed_files": self.processed_files,
                "total_files": self.total_files,
                "elapsed_time": self.elapsed_time,
            }
        )
        return base


@dataclass(kw_only=True)
class EngineCompleted(DomainEvent):
    event_type: str = "engine.completed"
    job_id: UUID
    engine_name: str
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, object]:
        base = super().to_dict()
        base.update(
            {
                "job_id": str(self.job_id),
                "engine_name": self.engine_name,
                "status": "completed",
                "duration_seconds": self.duration_seconds,
            }
        )
        return base


@dataclass(kw_only=True)
class EngineFailed(DomainEvent):
    event_type: str = "engine.failed"
    job_id: UUID
    engine_name: str
    error_message: str = ""

    def to_dict(self) -> dict[str, object]:
        base = super().to_dict()
        base.update(
            {
                "job_id": str(self.job_id),
                "engine_name": self.engine_name,
                "status": "failed",
                "error_message": self.error_message,
            }
        )
        return base


@dataclass(kw_only=True)
class AnalysisFailed(DomainEvent):
    event_type: str = "analysis.failed"
    job_id: UUID
    repo_id: UUID
    error_message: str
    stage: str = ""

    def to_dict(self) -> dict[str, object]:
        base = super().to_dict()
        base.update(
            {
                "job_id": str(self.job_id),
                "repo_id": str(self.repo_id),
                "error_message": self.error_message,
                "stage": self.stage,
            }
        )
        return base
