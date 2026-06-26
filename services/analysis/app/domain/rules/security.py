import math
import re
from typing import cast

from app.core.constants import Category, Severity
from app.domain.rules.base import BaseRule, RuleViolation


class SecurityNoAuthRule(BaseRule):
    """Detects API routes missing authentication decorators."""

    rule_id: str = "SEC-NO-AUTH"
    category: Category = Category.SECURITY
    severity: Severity = Severity.HIGH
    description: str = "Detects API endpoints without authentication"
    file_patterns: list[str] = [
        "*route*",
        "*view*",
        "*controller*",
        "*api*",
        "*handler*",
        "*endpoint*",
    ]

    _AUTH_DECORATORS: set[str] = {
        "login_required",
        "auth_required",
        "authenticate",
        "require_auth",
        "jwt_required",
        "token_required",
        "permission_required",
        "roles_required",
        "loginrequired",
        "authenticated",
    }

    async def analyze(
        self, file_path: str, content: str, ast_data: dict[str, object]
    ) -> list[RuleViolation]:
        violations: list[RuleViolation] = []
        routes: list[dict[str, object]] = cast(list[dict[str, object]], ast_data.get("routes", []))

        for route in routes:
            if not route.get("has_auth"):
                method = route.get("method", "GET")
                path = route.get("path", "/unknown")
                violations.append(
                    RuleViolation(
                        rule_id=self.rule_id,
                        category=self.category,
                        severity=Severity.CRITICAL
                        if method in ("POST", "PUT", "DELETE", "PATCH")
                        else Severity.HIGH,
                        title=(
                            f"Missing authentication on "
                            f"{method} {path}"
                        ),
                        description=(
                            "This endpoint requires no authentication. "
                            "Any user can access it without credentials."
                        ),
                        file_path=file_path,
                        line_start=cast(int | None, route.get("line_start")),
                        line_end=cast(int | None, route.get("line_end")),
                        code_snippet=cast(str, route.get("snippet", "")),
                        recommendation=(
                            "Add @login_required or equivalent "
                            "authentication decorator"
                        ),
                        enterprise_pattern=(
                            "Defense in depth — authenticate at "
                            "gateway AND application level"
                        ),
                        score_impact=-15.0,
                        rpm_impact=-200,
                    )
                )
        return violations


class SecurityHardcodedSecretRule(BaseRule):
    """Detects potential hardcoded secrets using entropy analysis.

    Flags high-entropy strings that look like API keys, passwords,
    or tokens hardcoded in source files.
    """

    rule_id: str = "SEC-SECRET"
    category: Category = Category.SECURITY
    severity: Severity = Severity.CRITICAL
    description: str = "Detects hardcoded secrets and credentials"
    languages: list[str] = []
    file_patterns: list[str] = [
        "*.py",
        "*.js",
        "*.ts",
        "*.go",
        "*.java",
        "*.rb",
        "*.rs",
        "*.yml",
        "*.yaml",
        "*.env*",
        "*.json",
        "*.toml",
        "*.cfg",
        "*.ini",
        "*.conf",
        "*.config",
    ]

    _SECRET_PATTERNS: list[re.Pattern[str]] = [
        re.compile(r'(["\'])(api[_-]?key)\1\s*[:=]\s*(["\'])([^"\']+)\3', re.IGNORECASE),
        re.compile(r'(["\'])password\1\s*[:=]\s*(["\'])([^"\']+)\2', re.IGNORECASE),
        re.compile(r'(["\'])secret\1\s*[:=]\s*(["\'])([^"\']+)\2', re.IGNORECASE),
        re.compile(r'(["\'])token\1\s*[:=]\s*(["\'])([^"\']+)\2', re.IGNORECASE),
        re.compile(r'(["\'])(access[_-]?key|secret[_-]?key)\1\s*[:=]\s*(["\'])([^"\']+)\3', re.IGNORECASE),
        re.compile(r'\b(api[_-]?key)\s*=\s*(["\'])([^"\']+)\2', re.IGNORECASE),
        re.compile(r'\bpassword\s*=\s*(["\'])([^"\']+)\1', re.IGNORECASE),
        re.compile(r'\b(secret)\s*=\s*(["\'])([^"\']+)\2', re.IGNORECASE),
        re.compile(r'\b(token)\s*=\s*(["\'])([^"\']+)\2', re.IGNORECASE),
        re.compile(r'\b(access[_-]?key|secret[_-]?key)\s*=\s*(["\'])([^"\']+)\2', re.IGNORECASE),
    ]
    _ENTROPY_THRESHOLD: float = 3.0

    async def analyze(
        self, file_path: str, content: str, ast_data: dict[str, object]
    ) -> list[RuleViolation]:
        violations: list[RuleViolation] = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            for pattern in self._SECRET_PATTERNS:
                match = pattern.search(line)
                if match:
                    value = match.group(match.lastindex) if match.lastindex else match.group(0)
                    if self._entropy(value) > self._ENTROPY_THRESHOLD:
                        violations.append(
                            RuleViolation(
                                rule_id=self.rule_id,
                                category=self.category,
                                severity=self.severity,
                                title="Hardcoded secret detected",
                                description=(
                                    "High-entropy string found — "
                                    "potential API key, password, "
                                    "or secret token"
                                ),
                                file_path=file_path,
                                line_start=line_num,
                                line_end=line_num,
                                code_snippet=line.strip(),
                                recommendation=(
                                    "Move to environment variables "
                                    "or secrets manager. "
                                    "Never commit secrets to version control."
                                ),
                                enterprise_pattern=(
                                    "Use HashiCorp Vault, AWS Secrets Manager, "
                                    "or environment variable injection"
                                ),
                                score_impact=-15.0,
                            )
                        )
        return violations

    @staticmethod
    def _entropy(s: str) -> float:
        """Calculate Shannon entropy of a string.

        Higher entropy = more random-looking = more likely a real secret.
        """
        if not s or len(s) < 6:
            return 0.0
        entropy = 0.0
        for c in set(s):
            p = s.count(c) / len(s)
            if p > 0:
                entropy -= p * math.log2(p)
        return entropy
