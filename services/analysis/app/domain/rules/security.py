import math
import re
from typing import cast

from app.core.constants import Category, Severity
from app.domain.rules.base import BaseRule, RuleViolation
from app.domain.rules.patterns.security_patterns import (
    COMMAND_INJECTION_PATTERNS,
    CORS_PATTERNS,
    CSRF_PATTERNS,
    DESERIALIZATION_PATTERNS,
    JWT_PATTERNS,
    PATH_TRAVERSAL_PATTERNS,
    SQL_INJECTION_PATTERNS,
    SSRF_PATTERNS,
    WEAK_CRYPTO_PATTERNS,
    XSS_PATTERNS,
    XXE_PATTERNS,
)


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

    async def analyze(
        self, file_path: str, content: str, ast_data: dict[str, object]
    ) -> list[RuleViolation]:
        violations: list[RuleViolation] = []
        routes: list[dict[str, object]] = cast(
            list[dict[str, object]], ast_data.get("routes", [])
        )

        for route in routes:
            if not route.get("has_auth"):
                method = route.get("method", "GET")
                path = route.get("path", "/unknown")
                violations.append(
                    RuleViolation(
                        rule_id=self.rule_id,
                        category=self.category,
                        severity=(
                            Severity.CRITICAL
                            if method in ("POST", "PUT", "DELETE", "PATCH")
                            else Severity.HIGH
                        ),
                        title=f"Missing authentication on {method} {path}",
                        description=(
                            "This endpoint requires no authentication. "
                            "Any user can access it without credentials."
                        ),
                        file_path=file_path,
                        line_start=cast(int | None, route.get("line_start")),
                        line_end=cast(int | None, route.get("line_end")),
                        code_snippet=cast(str, route.get("snippet", "")),
                        recommendation=(
                            "Add @login_required or equivalent authentication decorator"
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
    """Detects potential hardcoded secrets using entropy analysis."""

    rule_id: str = "SEC-SECRET"
    category: Category = Category.SECURITY
    severity: Severity = Severity.CRITICAL
    description: str = "Detects hardcoded secrets and credentials"
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
    exclude_patterns: list[str] = [
        "*fixture*",
        "*mock*",
        "*seed*",
        "*sqlite_data*",
        "*.sql",
    ]

    _SECRET_PATTERNS: list[re.Pattern[str]] = [
        re.compile(
            r'(["\'])(api[_-]?key)\1\s*[:=]\s*(["\'])([^"\']+)\3', re.IGNORECASE
        ),
        re.compile(r'(["\'])password\1\s*[:=]\s*(["\'])([^"\']+)\2', re.IGNORECASE),
        re.compile(r'(["\'])secret\1\s*[:=]\s*(["\'])([^"\']+)\2', re.IGNORECASE),
        re.compile(r'(["\'])token\1\s*[:=]\s*(["\'])([^"\']+)\2', re.IGNORECASE),
        re.compile(
            r'(["\'])(access[_-]?key|secret[_-]?key)\1\s*[:=]\s*(["\'])([^"\']+)\3',
            re.IGNORECASE,
        ),
        re.compile(r'\b(api[_-]?key)\s*=\s*(["\'])([^"\']+)\2', re.IGNORECASE),
        re.compile(r'\bpassword\s*=\s*(["\'])([^"\']+)\1', re.IGNORECASE),
        re.compile(r'\b(secret)\s*=\s*(["\'])([^"\']+)\2', re.IGNORECASE),
        re.compile(r'\b(token)\s*=\s*(["\'])([^"\']+)\2', re.IGNORECASE),
        re.compile(
            r'\b(access[_-]?key|secret[_-]?key)\s*=\s*(["\'])([^"\']+)\2', re.IGNORECASE
        ),
    ]
    _ENTROPY_THRESHOLD: float = 3.0

    async def analyze(
        self, file_path: str, content: str, ast_data: dict[str, object]
    ) -> list[RuleViolation]:
        violations: list[RuleViolation] = []
        lines = content.split("\n")
        effective_severity = (
            Severity.INFO if self.matches_exclude_pattern(file_path) else self.severity
        )

        for line_num, line in enumerate(lines, 1):
            for pattern in self._SECRET_PATTERNS:
                match = pattern.search(line)
                if match:
                    value = (
                        match.group(match.lastindex)
                        if match.lastindex
                        else match.group(0)
                    )
                    if self._entropy(value) > self._ENTROPY_THRESHOLD:
                        violations.append(
                            RuleViolation(
                                rule_id=self.rule_id,
                                category=self.category,
                                severity=effective_severity,
                                title="Hardcoded secret detected",
                                description="High-entropy string found — potential API key, password, or secret token",
                                file_path=file_path,
                                line_start=line_num,
                                line_end=line_num,
                                code_snippet=line.strip(),
                                recommendation="Move to environment variables or secrets manager. Never commit secrets.",
                                enterprise_pattern="Use HashiCorp Vault, AWS Secrets Manager, or environment variable injection",
                                score_impact=-15.0,
                            )
                        )
        return violations

    @staticmethod
    def _entropy(s: str) -> float:
        if not s or len(s) < 6:
            return 0.0
        entropy = 0.0
        for c in set(s):
            p = s.count(c) / len(s)
            if p > 0:
                entropy -= p * math.log2(p)
        return entropy


class SecuritySQLInjectionRule(BaseRule):
    """Detects SQL injection vulnerabilities."""

    rule_id: str = "SEC-SQLI"
    category: Category = Category.SECURITY
    severity: Severity = Severity.CRITICAL
    description: str = "Detects SQL injection vulnerabilities from unsanitized input"
    file_patterns: list[str] = [
        "*.py",
        "*.js",
        "*.ts",
        "*.java",
        "*.go",
        "*.rb",
        "*.php",
    ]

    async def analyze(
        self, file_path: str, content: str, ast_data: dict[str, object]
    ) -> list[RuleViolation]:
        violations: list[RuleViolation] = []
        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            for pattern in SQL_INJECTION_PATTERNS:
                if pattern.search(line):
                    violations.append(
                        RuleViolation(
                            rule_id=self.rule_id,
                            category=self.category,
                            severity=self.severity,
                            title="SQL Injection vulnerability",
                            description="User input is concatenated into a SQL query without parameterization",
                            file_path=file_path,
                            line_start=line_num,
                            line_end=line_num,
                            code_snippet=line.strip(),
                            recommendation="Use parameterized queries or ORM. Never concatenate user input into SQL.",
                            enterprise_pattern="Use parameterized statements or an ORM with query builder validation",
                            score_impact=-15.0,
                        )
                    )
                    break
        return violations


class SecurityCommandInjectionRule(BaseRule):
    """Detects command injection vulnerabilities."""

    rule_id: str = "SEC-CMDI"
    category: Category = Category.SECURITY
    severity: Severity = Severity.CRITICAL
    description: str = (
        "Detects command injection from unsanitized input in system commands"
    )
    file_patterns: list[str] = [
        "*.py",
        "*.js",
        "*.ts",
        "*.java",
        "*.go",
        "*.rb",
        "*.php",
    ]

    async def analyze(
        self, file_path: str, content: str, ast_data: dict[str, object]
    ) -> list[RuleViolation]:
        violations: list[RuleViolation] = []
        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            for pattern in COMMAND_INJECTION_PATTERNS:
                if pattern.search(line):
                    violations.append(
                        RuleViolation(
                            rule_id=self.rule_id,
                            category=self.category,
                            severity=self.severity,
                            title="Command Injection vulnerability",
                            description="User input is passed to a system/shell command without sanitization",
                            file_path=file_path,
                            line_start=line_num,
                            line_end=line_num,
                            code_snippet=line.strip(),
                            recommendation="Use subprocess with list arguments, never shell=True. Validate and sanitize input.",
                            enterprise_pattern="Avoid shell commands. Use language-native APIs. Apply strict input validation.",
                            score_impact=-15.0,
                        )
                    )
                    break
        return violations


class SecurityPathTraversalRule(BaseRule):
    """Detects path traversal vulnerabilities."""

    rule_id: str = "SEC-PATH"
    category: Category = Category.SECURITY
    severity: Severity = Severity.HIGH
    description: str = "Detects path traversal from unsanitized file path operations"
    file_patterns: list[str] = [
        "*.py",
        "*.js",
        "*.ts",
        "*.java",
        "*.go",
        "*.rb",
        "*.php",
    ]

    async def analyze(
        self, file_path: str, content: str, ast_data: dict[str, object]
    ) -> list[RuleViolation]:
        violations: list[RuleViolation] = []
        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            for pattern in PATH_TRAVERSAL_PATTERNS:
                if pattern.search(line):
                    violations.append(
                        RuleViolation(
                            rule_id=self.rule_id,
                            category=self.category,
                            severity=self.severity,
                            title="Path Traversal vulnerability",
                            description="User input is used in file path operations without validation",
                            file_path=file_path,
                            line_start=line_num,
                            line_end=line_num,
                            code_snippet=line.strip(),
                            recommendation="Validate and sanitize file paths. Use allowlists, reject '../' patterns.",
                            enterprise_pattern="Use a restricted file access layer with path canonicalization",
                            score_impact=-10.0,
                        )
                    )
                    break
        return violations


class SecuritySSRFRule(BaseRule):
    """Detects Server-Side Request Forgery vulnerabilities."""

    rule_id: str = "SEC-SSRF"
    category: Category = Category.SECURITY
    severity: Severity = Severity.HIGH
    description: str = "Detects SSRF from user-controlled URLs in HTTP clients"
    file_patterns: list[str] = [
        "*.py",
        "*.js",
        "*.ts",
        "*.java",
        "*.go",
        "*.rb",
        "*.php",
    ]

    async def analyze(
        self, file_path: str, content: str, ast_data: dict[str, object]
    ) -> list[RuleViolation]:
        violations: list[RuleViolation] = []
        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            for pattern in SSRF_PATTERNS:
                if pattern.search(line):
                    violations.append(
                        RuleViolation(
                            rule_id=self.rule_id,
                            category=self.category,
                            severity=self.severity,
                            title="Server-Side Request Forgery (SSRF)",
                            description="A user-controlled URL is passed to an HTTP client without validation",
                            file_path=file_path,
                            line_start=line_num,
                            line_end=line_num,
                            code_snippet=line.strip(),
                            recommendation="Validate URLs against an allowlist. Block internal IP ranges.",
                            enterprise_pattern="Implement a URL validation gateway. Use a dedicated outbound proxy with allowlists.",
                            score_impact=-10.0,
                        )
                    )
                    break
        return violations


class SecurityXXERule(BaseRule):
    """Detects XML External Entity (XXE) vulnerabilities."""

    rule_id: str = "SEC-XXE"
    category: Category = Category.SECURITY
    severity: Severity = Severity.HIGH
    description: str = "Detects insecure XML parsers vulnerable to XXE attacks"
    file_patterns: list[str] = [
        "*.py",
        "*.js",
        "*.ts",
        "*.java",
        "*.go",
        "*.rb",
        "*.php",
        "*.xml",
    ]

    async def analyze(
        self, file_path: str, content: str, ast_data: dict[str, object]
    ) -> list[RuleViolation]:
        violations: list[RuleViolation] = []
        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            for pattern in XXE_PATTERNS:
                if pattern.search(line):
                    has_defensive = any(
                        kw in line.lower()
                        for kw in (
                            "defusedxml",
                            "resolveentity",
                            "setfeatur",
                            "disallow",
                            "secure",
                            "xxe",
                            "external_entity",
                        )
                    )
                    if not has_defensive:
                        violations.append(
                            RuleViolation(
                                rule_id=self.rule_id,
                                category=self.category,
                                severity=self.severity,
                                title="XML External Entity (XXE) vulnerability",
                                description="XML parser detected without external entity protection",
                                file_path=file_path,
                                line_start=line_num,
                                line_end=line_num,
                                code_snippet=line.strip(),
                                recommendation="Disable external entity resolution. Use defusedxml or secure parser settings.",
                                enterprise_pattern="Disable DOCTYPE and external entities globally. Use JSON where possible.",
                                score_impact=-10.0,
                            )
                        )
                    break
        return violations


class SecurityWeakCryptoRule(BaseRule):
    """Detects use of weak or deprecated cryptographic algorithms."""

    rule_id: str = "SEC-WCRYPTO"
    category: Category = Category.SECURITY
    severity: Severity = Severity.HIGH
    description: str = "Detects weak or deprecated cryptographic algorithms"
    file_patterns: list[str] = [
        "*.py",
        "*.js",
        "*.ts",
        "*.java",
        "*.go",
        "*.rb",
        "*.php",
        "*.kt",
    ]

    async def analyze(
        self, file_path: str, content: str, ast_data: dict[str, object]
    ) -> list[RuleViolation]:
        violations: list[RuleViolation] = []
        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            for pattern in WEAK_CRYPTO_PATTERNS:
                if pattern.search(line):
                    violations.append(
                        RuleViolation(
                            rule_id=self.rule_id,
                            category=self.category,
                            severity=self.severity,
                            title="Weak cryptographic algorithm detected",
                            description="Use of MD5, SHA-1, DES, ECB mode, or RC4 detected",
                            file_path=file_path,
                            line_start=line_num,
                            line_end=line_num,
                            code_snippet=line.strip(),
                            recommendation="Use SHA-256/SHA-512, AES-GCM, or bcrypt/Argon2 for passwords.",
                            enterprise_pattern="Enforce FIPS 140-2 compliant algorithms. Use a crypto agility layer.",
                            score_impact=-10.0,
                        )
                    )
                    break
        return violations


class SecurityJWTRule(BaseRule):
    """Detects JWT implementation mistakes."""

    rule_id: str = "SEC-JWT"
    category: Category = Category.SECURITY
    severity: Severity = Severity.CRITICAL
    description: str = "Detects JWT security misconfigurations"
    file_patterns: list[str] = ["*.py", "*.js", "*.ts", "*.java", "*.go", "*.rb"]

    async def analyze(
        self, file_path: str, content: str, ast_data: dict[str, object]
    ) -> list[RuleViolation]:
        violations: list[RuleViolation] = []
        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            for pattern in JWT_PATTERNS:
                if pattern.search(line):
                    if "none" in line.lower() and "algorithm" in line.lower():
                        violations.append(
                            RuleViolation(
                                rule_id=self.rule_id,
                                category=self.category,
                                severity=self.severity,
                                title="JWT 'none' algorithm detected",
                                description="JWT library configured to accept 'none' algorithm — attackers can forge tokens",
                                file_path=file_path,
                                line_start=line_num,
                                line_end=line_num,
                                code_snippet=line.strip(),
                                recommendation="Explicitly set algorithms to ['HS256'] or ['RS256']. Never allow 'none'.",
                                enterprise_pattern="Enforce algorithm allowlist at JWT verification layer",
                                score_impact=-15.0,
                            )
                        )
                    else:
                        violations.append(
                            RuleViolation(
                                rule_id=self.rule_id,
                                category=self.category,
                                severity=Severity.HIGH,
                                title="JWT verification in progress",
                                description="JWT verification detected — verify algorithm allowlist and secret strength",
                                file_path=file_path,
                                line_start=line_num,
                                line_end=line_num,
                                code_snippet=line.strip(),
                                recommendation="Verify algorithm allowlist, secret rotation, and expiration are configured",
                                enterprise_pattern="Use JWKS endpoints for key rotation. Short token TTLs. Refresh token rotation.",
                                score_impact=-10.0,
                            )
                        )
                    break
        return violations


class SecurityDeserializationRule(BaseRule):
    """Detects unsafe deserialization patterns."""

    rule_id: str = "SEC-DESER"
    category: Category = Category.SECURITY
    severity: Severity = Severity.CRITICAL
    description: str = "Detects unsafe deserialization of untrusted data"
    file_patterns: list[str] = [
        "*.py",
        "*.js",
        "*.ts",
        "*.java",
        "*.go",
        "*.rb",
        "*.php",
    ]

    async def analyze(
        self, file_path: str, content: str, ast_data: dict[str, object]
    ) -> list[RuleViolation]:
        violations: list[RuleViolation] = []
        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            for pattern in DESERIALIZATION_PATTERNS:
                if pattern.search(line):
                    violations.append(
                        RuleViolation(
                            rule_id=self.rule_id,
                            category=self.category,
                            severity=self.severity,
                            title="Unsafe deserialization detected",
                            description="Unsafe deserialization of potentially untrusted data detected",
                            file_path=file_path,
                            line_start=line_num,
                            line_end=line_num,
                            code_snippet=line.strip(),
                            recommendation="Use safe serialization formats (JSON). Avoid pickle/yaml.load on untrusted data.",
                            enterprise_pattern="Use structured validation schemas. Never deserialize untrusted data with unsafe formats.",
                            score_impact=-15.0,
                        )
                    )
                    break
        return violations


class SecurityXSSRule(BaseRule):
    """Detects Cross-Site Scripting (XSS) vulnerabilities."""

    rule_id: str = "SEC-XSS"
    category: Category = Category.SECURITY
    severity: Severity = Severity.CRITICAL
    description: str = (
        "Detects Cross-Site Scripting from unsanitized user input in output/execution contexts"
    )
    file_patterns: list[str] = [
        "*.py",
        "*.js",
        "*.ts",
        "*.java",
        "*.go",
        "*.rb",
        "*.php",
    ]

    async def analyze(
        self, file_path: str, content: str, ast_data: dict[str, object]
    ) -> list[RuleViolation]:
        violations: list[RuleViolation] = []
        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            for pattern in XSS_PATTERNS:
                if pattern.search(line):
                    violations.append(
                        RuleViolation(
                            rule_id=self.rule_id,
                            category=self.category,
                            severity=self.severity,
                            title="Cross-Site Scripting (XSS) vulnerability",
                            description="User input is written to HTML output, eval, or DOM APIs without sanitization",
                            file_path=file_path,
                            line_start=line_num,
                            line_end=line_num,
                            code_snippet=line.strip(),
                            recommendation="Use context-appropriate encoding (HTML entity, JS string, CSS). Never trust user input.",
                            enterprise_pattern="Apply strict CSP headers and output encoding. Use template engines with auto-escaping.",
                            score_impact=-15.0,
                        )
                    )
                    break
        return violations


class SecurityMissingAuthzRule(BaseRule):
    """Detects missing authorization checks on API endpoints."""

    rule_id: str = "SEC-NO-AUTHZ"
    category: Category = Category.SECURITY
    severity: Severity = Severity.HIGH
    description: str = "Detects API endpoints missing authorization checks"
    file_patterns: list[str] = [
        "*route*",
        "*view*",
        "*controller*",
        "*api*",
        "*handler*",
        "*endpoint*",
    ]

    _AUTHZ_KEYWORDS: set[str] = {
        "role",
        "permission",
        "authorize",
        "authz",
        "allow",
        "access",
        "can_",
        "has_",
        "is_admin",
        "is_owner",
        "is_member",
    }

    async def analyze(
        self, file_path: str, content: str, ast_data: dict[str, object]
    ) -> list[RuleViolation]:
        violations: list[RuleViolation] = []
        routes: list[dict[str, object]] = cast(
            list[dict[str, object]], ast_data.get("routes", [])
        )

        for route in routes:
            if route.get("has_auth") is True:
                method = route.get("method", "GET")
                path = route.get("path", "/unknown")
                snippet = cast(str, route.get("snippet", ""))
                has_authz = any(kw in snippet.lower() for kw in self._AUTHZ_KEYWORDS)
                if not has_authz:
                    violations.append(
                        RuleViolation(
                            rule_id=self.rule_id,
                            category=self.category,
                            severity=(
                                Severity.CRITICAL
                                if method in ("POST", "PUT", "DELETE", "PATCH")
                                else Severity.HIGH
                            ),
                            title=f"Missing authorization check on {method} {path}",
                            description="Endpoint has authentication but no authorization check for role or permissions",
                            file_path=file_path,
                            line_start=cast(int | None, route.get("line_start")),
                            line_end=cast(int | None, route.get("line_end")),
                            code_snippet=snippet,
                            recommendation="Add role/permission checks after authentication. Use RBAC or attribute-based access control.",
                            enterprise_pattern="Implement centralized authorization with policy engine. Enforce least privilege.",
                            score_impact=-10.0,
                        )
                    )
        return violations


class SecurityCSRFRule(BaseRule):
    """Detects missing CSRF protection on state-changing endpoints."""

    rule_id: str = "SEC-CSRF"
    category: Category = Category.SECURITY
    severity: Severity = Severity.HIGH
    description: str = "Detects endpoints missing CSRF protection"
    file_patterns: list[str] = [
        "*route*",
        "*view*",
        "*controller*",
        "*api*",
        "*handler*",
        "*middleware*",
        "*.py",
        "*.js",
        "*.ts",
    ]

    async def analyze(
        self, file_path: str, content: str, ast_data: dict[str, object]
    ) -> list[RuleViolation]:
        violations: list[RuleViolation] = []
        has_csrf_protection = any(pattern.search(content) for pattern in CSRF_PATTERNS)

        routes: list[dict[str, object]] = cast(
            list[dict[str, object]], ast_data.get("routes", [])
        )
        mutating_routes = [
            r
            for r in routes
            if r.get("method", "GET") in ("POST", "PUT", "DELETE", "PATCH")
        ]

        if mutating_routes and not has_csrf_protection:
            for route in mutating_routes:
                method = route.get("method", "POST")
                path = route.get("path", "/unknown")
                violations.append(
                    RuleViolation(
                        rule_id=self.rule_id,
                        category=self.category,
                        severity=self.severity,
                        title=f"Missing CSRF protection on {method} {path}",
                        description="State-changing endpoint without CSRF protection",
                        file_path=file_path,
                        line_start=cast(int | None, route.get("line_start")),
                        line_end=cast(int | None, route.get("line_end")),
                        code_snippet=cast(str, route.get("snippet", "")),
                        recommendation="Enable CSRF middleware or add CSRF tokens to forms. Use SameSite cookies.",
                        enterprise_pattern="Use anti-CSRF tokens, SameSite=Strict cookies, and double-submit cookie pattern",
                        score_impact=-8.0,
                    )
                )
        return violations


class SecurityCORSMisconfigRule(BaseRule):
    """Detects CORS misconfiguration that allows any origin."""

    rule_id: str = "SEC-CORS"
    category: Category = Category.SECURITY
    severity: Severity = Severity.HIGH
    description: str = "Detects permissive CORS configurations"
    file_patterns: list[str] = [
        "*.py",
        "*.js",
        "*.ts",
        "*.yml",
        "*.yaml",
        "*.json",
        "*.toml",
    ]

    async def analyze(
        self, file_path: str, content: str, ast_data: dict[str, object]
    ) -> list[RuleViolation]:
        violations: list[RuleViolation] = []
        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            for pattern in CORS_PATTERNS:
                if pattern.search(line):
                    violations.append(
                        RuleViolation(
                            rule_id=self.rule_id,
                            category=self.category,
                            severity=Severity.HIGH,
                            title="Permissive CORS configuration",
                            description="CORS allows any origin ('*'), exposing the API to cross-origin attacks",
                            file_path=file_path,
                            line_start=line_num,
                            line_end=line_num,
                            code_snippet=line.strip(),
                            recommendation="Restrict CORS to specific trusted origins. Never use '*' in production.",
                            enterprise_pattern="Use an API gateway for CORS policy. Whitelist specific origins only.",
                            score_impact=-8.0,
                        )
                    )
                    break
        return violations
