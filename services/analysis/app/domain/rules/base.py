from abc import ABC, abstractmethod
from dataclasses import dataclass, field


from app.core.constants import Category, Severity


@dataclass(kw_only=True)
class RuleViolation:
    """Output of a single rule execution.

    Rules produce these; the rule runner aggregates and
    converts them into domain Finding entities.
    """

    rule_id: str
    category: Category
    severity: Severity
    title: str
    description: str = ""
    file_path: str = ""
    line_start: int | None = None
    line_end: int | None = None
    code_snippet: str = ""
    recommendation: str = ""
    enterprise_pattern: str = ""
    score_impact: float = 0.0
    rpm_impact: int = 0
    breaks_at_users: int | None = None
    metadata: dict[str, object] = field(default_factory=dict)


class BaseRule(ABC):
    """Base class for all analysis rules.

    Rules analyze source code and produce violations.
    Each rule focuses on a single concern (e.g., cyclomatic complexity,
    hardcoded secrets, missing auth).

    Rules are stateless, thread-safe, and should be safe to run
    concurrently across multiple files.
    """

    rule_id: str = ""
    category: Category = Category.QUALITY
    severity: Severity = Severity.MEDIUM
    languages: list[str] = []
    file_patterns: list[str] = ["*"]
    description: str = ""

    @abstractmethod
    async def analyze(
        self, file_path: str, content: str, ast_data: dict[str, object]
    ) -> list[RuleViolation]:
        """Analyze a single file and return violations.

        Args:
            file_path: Path relative to repo root.
            content: Raw file content.
            ast_data: Pre-parsed AST data (functions, classes, imports, etc.).

        Returns:
            List of RuleViolation instances. Empty list if no issues found.
        """
