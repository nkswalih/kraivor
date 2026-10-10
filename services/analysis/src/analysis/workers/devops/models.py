class DevOpsFinding:
    def __init__(
        self,
        devops_type: str,
        severity: str,
        title: str,
        description: str,
        file_path: str,
        line_start: int | None = None,
        line_end: int | None = None,
        code_snippet: str | None = None,
        recommendation: str | None = None,
        confidence: float = 0.8,
        category: str = "",
        devops_score: dict[str, float | int] | None = None,
    ) -> None:
        self.devops_type = devops_type
        self.severity = severity
        self.title = title
        self.description = description
        self.file_path = file_path
        self.line_start = line_start
        self.line_end = line_end
        self.code_snippet = code_snippet
        self.recommendation = recommendation
        self.confidence = confidence
        self.category = category
        self.devops_score = devops_score

    def to_dict(self) -> dict[str, object]:
        d: dict[str, object] = {
            "devops_type": self.devops_type,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "code_snippet": self.code_snippet,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
            "category": self.category,
        }
        if self.devops_score is not None:
            d["devops_score"] = self.devops_score
        return d
