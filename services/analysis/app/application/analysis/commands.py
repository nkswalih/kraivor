from dataclasses import dataclass, field
from uuid import UUID


@dataclass(kw_only=True)
class StartAnalysisCommand:
    repo_id: UUID
    workspace_id: UUID
    triggered_by: UUID
    trigger_type: str
    repo_url: str
    branch: str = "main"
    deep_scan: bool = False
    simulate_users: list[int] | None = None


@dataclass(kw_only=True)
class ProcessStageCommand:
    job_id: UUID
    stage: str
    repo_path: str | None = None
