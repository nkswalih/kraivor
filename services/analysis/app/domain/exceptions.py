class DomainError(Exception):
    """Base exception for domain-level errors."""

    def __init__(
        self,
        message: str = "Domain error occurred",
        code: str = "domain_error",
        details: dict[str, object] | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class InvalidFindingError(DomainError):
    def __init__(
        self,
        message: str = "Invalid finding data",
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message=message, code="invalid_finding", details=details)


class InvalidScoreError(DomainError):
    def __init__(
        self,
        message: str = "Invalid score calculation",
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message=message, code="invalid_score", details=details)


class RuleExecutionError(DomainError):
    def __init__(
        self,
        message: str = "Rule execution failed",
        rule_id: str = "",
        details: dict[str, object] | None = None,
    ) -> None:
        detail = {"rule_id": rule_id, **(details or {})}
        super().__init__(message=message, code="rule_execution_error", details=detail)


class ParserError(DomainError):
    def __init__(
        self,
        message: str = "Code parsing failed",
        language: str = "",
        file_path: str = "",
        details: dict[str, object] | None = None,
    ) -> None:
        detail = {"language": language, "file_path": file_path, **(details or {})}
        super().__init__(message=message, code="parser_error", details=detail)
