import re
from typing import Any

from app.core.constants import Category, Severity
from app.domain.rules.base import BaseRule, RuleViolation


class QualityHighComplexityRule(BaseRule):
    """Flags functions with cyclomatic complexity > 15.

    High complexity means hard to test, hard to maintain,
    and likely to contain bugs.
    """

    rule_id: str = "QUAL-COMPLEX"
    category: Category = Category.MAINTAINABILITY
    severity: Severity = Severity.MEDIUM
    description: str = (
        "Flags functions with cyclomatic complexity above threshold"
    )

    _COMPLEXITY_THRESHOLD: int = 15
    _HIGH_COMPLEXITY_THRESHOLD: int = 30

    async def analyze(
        self, file_path: str, content: str, ast_data: dict[str, Any]
    ) -> list[RuleViolation]:
        violations: list[RuleViolation] = []
        functions = ast_data.get("functions", [])

        for func in functions:
            complexity = self._calculate_complexity(func)
            if complexity > self._COMPLEXITY_THRESHOLD:
                is_high = complexity > self._HIGH_COMPLEXITY_THRESHOLD
                violations.append(
                    RuleViolation(
                        rule_id=self.rule_id,
                        category=self.category,
                        severity=Severity.HIGH if is_high else Severity.MEDIUM,
                        title=(
                            f"High cyclomatic complexity ({complexity}) "
                            f"in {func.get('name', 'unknown')}"
                        ),
                        description=(
                            f"Function has {complexity} independent paths. "
                            f"Threshold is {self._COMPLEXITY_THRESHOLD}. "
                            f"Above {self._HIGH_COMPLEXITY_THRESHOLD} is "
                            f"considered untestable."
                        ),
                        file_path=file_path,
                        line_start=func.get("line_start"),
                        line_end=func.get("line_end"),
                        code_snippet=func.get("snippet", ""),
                        recommendation=(
                            "Break into smaller functions. "
                            "Extract conditional logic into separate "
                            "methods. Use early returns to reduce nesting."
                        ),
                        enterprise_pattern=(
                            "Single Responsibility Principle — "
                            "each function should do exactly one thing"
                        ),
                        score_impact=-3.0 if is_high else -1.5,
                        rpm_impact=-100 if is_high else 0,
                    )
                )
        return violations

    def _calculate_complexity(self, func: dict) -> int:
        """Calculate McCabe cyclomatic complexity from AST data."""
        complexity = 1
        code = func.get("snippet", func.get("code", ""))
        if not code:
            return complexity

        patterns = [
            r"\bif\b",
            r"\belif\b",
            r"\belse\b",
            r"\bfor\b",
            r"\bwhile\b",
            r"\band\b",
            r"\bor\b",
            r"\bexcept\b",
            r"\bwith\b",
            r"\bassert\b",
            r"\bcase\b",
            r"\bdefault\b",
        ]
        for pattern in patterns:
            complexity += len(re.findall(pattern, code))
        return complexity


class QualityLongFunctionRule(BaseRule):
    """Flags functions longer than 50 lines."""

    rule_id: str = "QUAL-LONG-FUNC"
    category: Category = Category.MAINTAINABILITY
    severity: Severity = Severity.LOW
    description: str = "Flags functions that exceed maximum line count"
    _MAX_LINES: int = 50
    _HIGH_LINES: int = 100

    async def analyze(
        self, file_path: str, content: str, ast_data: dict[str, Any]
    ) -> list[RuleViolation]:
        violations: list[RuleViolation] = []
        functions = ast_data.get("functions", [])

        for func in functions:
            start = func.get("line_start", 0)
            end = func.get("line_end", 0)
            line_count = end - start + 1

            if line_count > self._MAX_LINES:
                over_limit = line_count > self._HIGH_LINES
                violations.append(
                    RuleViolation(
                        rule_id=self.rule_id,
                        category=self.category,
                        severity=Severity.MEDIUM if over_limit else Severity.LOW,
                        title=(
                            f"Long function ({line_count} lines) "
                            f"in {func.get('name', 'unknown')}"
                        ),
                        description=(
                            f"Function is {line_count} lines long. "
                            f"Maximum recommended is {self._MAX_LINES}."
                        ),
                        file_path=file_path,
                        line_start=func.get("line_start"),
                        line_end=func.get("line_end"),
                        code_snippet=func.get("snippet", ""),
                        recommendation=(
                            "Split into smaller helper functions. "
                            "Each function should be readable without scrolling."
                        ),
                        enterprise_pattern=(
                            "Keep functions small and focused — "
                            "the Single Responsibility Principle"
                        ),
                        score_impact=-1.0 if over_limit else -0.5,
                    )
                )
        return violations
