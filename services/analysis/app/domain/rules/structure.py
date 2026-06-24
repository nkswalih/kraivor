from typing import Any

from app.core.constants import Category, Severity
from app.domain.rules.base import BaseRule, RuleViolation


class StructureDeepNestingRule(BaseRule):
    """Detects excessive nested directory depth (>4 levels)."""

    rule_id: str = "STRUCT-DEEP"
    category: Category = Category.MAINTAINABILITY
    severity: Severity = Severity.LOW
    description: str = "Detects directory structures deeper than 4 levels"
    languages: list[str] = []
    file_patterns: list[str] = ["*"]
    _MAX_DEPTH: int = 4

    async def analyze(
        self, file_path: str, content: str, ast_data: dict[str, Any]
    ) -> list[RuleViolation]:
        violations: list[RuleViolation] = []
        depth = file_path.count("/")

        if depth > self._MAX_DEPTH:
            violations.append(
                RuleViolation(
                    rule_id=self.rule_id,
                    category=self.category,
                    severity=Severity.MEDIUM
                    if depth > 6
                    else self.severity,
                    title=(
                        f"Deep directory nesting "
                        f"({depth} levels): {file_path}"
                    ),
                    description=(
                        f"File is nested {depth} levels deep. "
                        f"Maximum recommended is {self._MAX_DEPTH}. "
                        f"Deep nesting increases cognitive load "
                        f"and makes navigation harder."
                    ),
                    file_path=file_path,
                    recommendation=(
                        "Flatten the directory structure. "
                        "Use feature-based organization instead "
                        "of type-based."
                    ),
                    enterprise_pattern=(
                        "Organize by feature, not by type — "
                        "group related files together"
                    ),
                    score_impact=-0.5,
                )
            )
        return violations
