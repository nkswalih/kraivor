from dataclasses import dataclass, field


@dataclass
class MaintainabilityMetrics:
    maintainability_index: float = 100.0
    technical_debt_hours: float = 0.0
    complexity_score: float = 100.0
    total_findings: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "maintainability_index": self.maintainability_index,
            "technical_debt_hours": self.technical_debt_hours,
            "complexity_score": self.complexity_score,
            "total_findings": self.total_findings,
        }


class MaintainabilityFinding:
    def __init__(
        self,
        maintainability_type: str,
        severity: str,
        title: str,
        description: str,
        file_path: str,
        line_start: int | None = None,
        line_end: int | None = None,
        code_snippet: str | None = None,
        recommendation: str | None = None,
        confidence: float = 0.8,
        estimated_effort_hours: float = 0.0,
    ) -> None:
        self.maintainability_type = maintainability_type
        self.severity = severity
        self.title = title
        self.description = description
        self.file_path = file_path
        self.line_start = line_start
        self.line_end = line_end
        self.code_snippet = code_snippet
        self.recommendation = recommendation
        self.confidence = confidence
        self.estimated_effort_hours = estimated_effort_hours

    def to_dict(self) -> dict[str, object]:
        return {
            "maintainability_type": self.maintainability_type,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "code_snippet": self.code_snippet,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
            "estimated_effort_hours": self.estimated_effort_hours,
        }
