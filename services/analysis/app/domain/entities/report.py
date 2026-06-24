from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.domain.entities.finding import Finding
from app.domain.entities.score import Score


@dataclass(kw_only=True)
class Report:
    """Entity representing a complete analysis report."""

    job_id: UUID
    repo_id: UUID
    workspace_id: UUID
    branch: str = "main"
    languages_detected: list[str] = field(default_factory=list)
    total_files_analyzed: int = 0
    total_lines_of_code: int = 0

    scores: Score | None = None
    findings: list[Finding] = field(default_factory=list)

    duration_seconds: int | None = None
    completed_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    s3_key: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": {
                "job_id": str(self.job_id),
                "repo_id": str(self.repo_id),
                "workspace_id": str(self.workspace_id),
                "branch": self.branch,
                "languages_detected": self.languages_detected,
                "total_files_analyzed": self.total_files_analyzed,
                "total_lines_of_code": self.total_lines_of_code,
                "duration_seconds": self.duration_seconds,
                "completed_at": self.completed_at.isoformat(),
            },
            "scores": self.scores.to_dict() if self.scores else {},
            "findings": [f.to_dict() for f in self.findings],
            "findings_count": len(self.findings),
        }
