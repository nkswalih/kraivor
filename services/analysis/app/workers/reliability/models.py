class ReliabilityFinding:
    def __init__(
        self,
        reliability_type: str,
        severity: str,
        title: str,
        description: str,
        file_path: str,
        line_start: int | None = None,
        line_end: int | None = None,
        code_snippet: str | None = None,
        recommendation: str | None = None,
        confidence: float = 0.8,
    ) -> None:
        self.reliability_type = reliability_type
        self.severity = severity
        self.title = title
        self.description = description
        self.file_path = file_path
        self.line_start = line_start
        self.line_end = line_end
        self.code_snippet = code_snippet
        self.recommendation = recommendation
        self.confidence = confidence

    def to_dict(self) -> dict[str, object]:
        return {
            "reliability_type": self.reliability_type,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "code_snippet": self.code_snippet,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
        }
