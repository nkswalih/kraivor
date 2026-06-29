from dataclasses import dataclass, field
from uuid import UUID, uuid4

from app.core.constants import Category, FindingStatus, Severity


@dataclass(kw_only=True)
class Finding:
    """Aggregate root representing a single analysis finding.

    This is the core entity of the analysis domain. Every code issue,
    dead code detection, error pattern, or performance bottleneck
    is represented as a Finding.
    """

    id: UUID = field(default_factory=uuid4)
    job_id: UUID
    repo_id: UUID
    workspace_id: UUID
    rule_id: str
    category: Category
    severity: Severity

    title: str
    description: str = ""
    recommendation: str = ""
    enterprise_pattern: str = ""
    ai_explanation: str = ""

    file_path: str = ""
    line_start: int | None = None
    line_end: int | None = None
    code_snippet: str = ""
    fix_snippet: str = ""

    score_impact: float = 0.0
    rpm_impact: int = 0
    breaks_at_users: int | None = None

    status: FindingStatus = FindingStatus.ACTIVE
    is_ai_enriched: bool = False
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": str(self.id),
            "job_id": str(self.job_id),
            "repo_id": str(self.repo_id),
            "workspace_id": str(self.workspace_id),
            "rule_id": self.rule_id,
            "category": str(self.category),
            "severity": str(self.severity),
            "title": self.title,
            "description": self.description,
            "recommendation": self.recommendation,
            "enterprise_pattern": self.enterprise_pattern,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "code_snippet": self.code_snippet,
            "fix_snippet": self.fix_snippet,
            "status": str(self.status),
            "score_impact": self.score_impact,
            "rpm_impact": self.rpm_impact,
            "breaks_at_users": self.breaks_at_users,
        }
