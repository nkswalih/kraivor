from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean, stdev
from types import SimpleNamespace as _SimpleNamespace

from app.core.constants import Category, Severity, Tiers
from app.core.logging import get_logger
from app.domain.entities.finding import Finding
from app.domain.entities.score import Score
from app.domain.rules.base import RuleViolation
from app.workers.dead_code.detector import DeadCodeFinding
from app.workers.devops.models import DevOpsFinding
from app.workers.errors.scanner import ErrorFinding
from app.workers.maintainability.models import MaintainabilityFinding
from app.workers.perf.load_sim import SimulationResult
from app.workers.perf.rpm_calculator import PerformanceMetrics
from app.workers.reliability.models import ReliabilityFinding

logger = get_logger(__name__)

GRADE_THRESHOLDS: list[tuple[float, str]] = [
    (90, "A"),
    (80, "B"),
    (65, "C"),
    (50, "D"),
    (0, "F"),
]


def score_to_grade(score: int | None) -> str | None:
    if score is None:
        return None
    for threshold, grade in GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "F"


def score_to_status(score: int | None) -> str:
    if score is None:
        return "not_assessed"
    if score >= 90:
        return "excellent"
    if score >= 75:
        return "good"
    if score >= 60:
        return "needs_work"
    if score >= 40:
        return "needs_attention"
    return "critical"


SEVERITY_WEIGHTS: dict[str, int] = {
    Severity.CRITICAL: 5,
    Severity.HIGH: 4,
    Severity.MEDIUM: 3,
    Severity.LOW: 2,
    Severity.INFO: 1,
}


# ── Cluster catalog: known rule patterns → enterprise taxonomy ─────
CLUSTER_CATALOG: dict[str, dict[str, object]] = {
    "sql_injection": {
        "cluster_id": "sql_injection",
        "title": "SQL Injection",
        "severity": Severity.CRITICAL,
        "cwe": ["CWE-89"],
        "owasp": ["A03:2021"],
        "standards_reference": ["OWASP ASVS 5.3.4", "CWE-89"],
    },
    "xss": {
        "cluster_id": "xss",
        "title": "Cross-Site Scripting (XSS)",
        "severity": Severity.CRITICAL,
        "cwe": ["CWE-79"],
        "owasp": ["A03:2021"],
        "standards_reference": ["OWASP ASVS 5.1.1", "CWE-79"],
    },
    "ssrf": {
        "cluster_id": "ssrf",
        "title": "Server-Side Request Forgery (SSRF)",
        "severity": Severity.HIGH,
        "cwe": ["CWE-918"],
        "owasp": ["A10:2021"],
        "standards_reference": ["CWE-918"],
    },
    "hardcoded_secret": {
        "cluster_id": "hardcoded_secrets",
        "title": "Hardcoded Secrets",
        "severity": Severity.CRITICAL,
        "cwe": ["CWE-798", "CWE-259"],
        "owasp": ["A07:2021"],
        "standards_reference": ["OWASP ASVS 4.0.1-003", "CWE-798"],
    },
    "weak_crypto": {
        "cluster_id": "weak_cryptography",
        "title": "Weak Cryptography",
        "severity": Severity.HIGH,
        "cwe": ["CWE-327", "CWE-326"],
        "owasp": ["A02:2021"],
        "standards_reference": ["NIST SP 800-175B", "CWE-327"],
    },
    "jwt": {
        "cluster_id": "jwt_issues",
        "title": "JWT Security Issues",
        "severity": Severity.HIGH,
        "cwe": ["CWE-347"],
        "owasp": ["A07:2021"],
        "standards_reference": ["CWE-347", "OWASP ASVS 4.0.1-003"],
    },
    "unsafe_deserialize": {
        "cluster_id": "unsafe_deserialization",
        "title": "Unsafe Deserialization",
        "severity": Severity.CRITICAL,
        "cwe": ["CWE-502"],
        "owasp": ["A08:2021"],
        "standards_reference": ["CWE-502", "OWASP ASVS 4.0.1-003"],
    },
    "missing_auth": {
        "cluster_id": "missing_authentication",
        "title": "Missing Authentication",
        "severity": Severity.CRITICAL,
        "cwe": ["CWE-306", "CWE-287"],
        "owasp": ["A01:2021", "A07:2021"],
        "standards_reference": ["CWE-306", "OWASP ASVS 2.1.1"],
    },
    "authorization": {
        "cluster_id": "missing_authorization",
        "title": "Missing Authorization",
        "severity": Severity.HIGH,
        "cwe": ["CWE-862", "CWE-863"],
        "owasp": ["A01:2021"],
        "standards_reference": ["CWE-862", "OWASP ASVS 4.0.1-003"],
    },
    "race_condition": {
        "cluster_id": "race_conditions",
        "title": "Race Conditions",
        "severity": Severity.HIGH,
        "cwe": ["CWE-362", "CWE-366"],
        "standards_reference": ["CWE-362"],
    },
    "missing_rollback": {
        "cluster_id": "missing_rollbacks",
        "title": "Missing Transaction Rollbacks",
        "severity": Severity.HIGH,
        "cwe": ["CWE-754"],
        "standards_reference": ["CWE-754"],
    },
    "n_plus_one": {
        "cluster_id": "n_plus_one_queries",
        "title": "N+1 Query Pattern",
        "severity": Severity.MEDIUM,
        "cwe": [],
        "owasp": [],
        "standards_reference": ["SQLAlchemy Best Practices"],
    },
    "sync_in_async": {
        "cluster_id": "sync_in_async",
        "title": "Synchronous Calls in Async Context",
        "severity": Severity.MEDIUM,
        "cwe": [],
        "standards_reference": ["Async Best Practices"],
    },
    "unbounded_query": {
        "cluster_id": "unbounded_queries",
        "title": "Unbounded Database Queries",
        "severity": Severity.MEDIUM,
        "cwe": [],
        "standards_reference": [],
    },
    "high_complexity": {
        "cluster_id": "high_complexity",
        "title": "High Cyclomatic Complexity",
        "severity": Severity.MEDIUM,
        "cwe": [],
        "standards_reference": ["SOLID Principles"],
    },
    "duplicate_code": {
        "cluster_id": "duplicate_code",
        "title": "Code Duplication",
        "severity": Severity.LOW,
        "cwe": [],
        "standards_reference": ["DRY Principle"],
    },
    "long_method": {
        "cluster_id": "long_methods",
        "title": "Long Methods / Functions",
        "severity": Severity.LOW,
        "cwe": [],
        "standards_reference": ["SOLID - Single Responsibility"],
    },
    "missing_timeout": {
        "cluster_id": "missing_timeouts",
        "title": "Missing Timeouts",
        "severity": Severity.HIGH,
        "cwe": ["CWE-1088"],
        "standards_reference": ["CWE-1088", "Twelve-Factor App"],
    },
    "missing_resource_limit": {
        "cluster_id": "missing_resource_limits",
        "title": "Missing Resource Limits",
        "severity": Severity.MEDIUM,
        "cwe": ["CWE-770"],
        "standards_reference": ["CWE-770"],
    },
    "bare_except": {
        "cluster_id": "bare_except",
        "title": "Bare Exception Handlers",
        "severity": Severity.MEDIUM,
        "cwe": ["CWE-755"],
        "standards_reference": ["CWE-755"],
    },
    "swallowed": {
        "cluster_id": "swallowed_exceptions",
        "title": "Swallowed Exceptions",
        "severity": Severity.MEDIUM,
        "cwe": ["CWE-778"],
        "standards_reference": ["CWE-778"],
    },
    "thread_safety": {
        "cluster_id": "thread_safety",
        "title": "Thread Safety Issues",
        "severity": Severity.HIGH,
        "cwe": ["CWE-366", "CWE-413"],
        "standards_reference": ["CWE-366"],
    },
    "hardcoded_config": {
        "cluster_id": "hardcoded_config",
        "title": "Hardcoded Configuration",
        "severity": Severity.MEDIUM,
        "cwe": [],
        "standards_reference": ["Twelve-Factor App - Config"],
    },
    "missing_validation": {
        "cluster_id": "missing_input_validation",
        "title": "Missing Input Validation",
        "severity": Severity.HIGH,
        "cwe": ["CWE-20"],
        "owasp": ["A03:2021", "A04:2023"],
        "standards_reference": ["CWE-20", "OWASP ASVS 5.1.1"],
    },
    "no_caching": {
        "cluster_id": "no_caching",
        "title": "Missing Cache Layer",
        "severity": Severity.LOW,
        "cwe": [],
        "standards_reference": [],
    },
    "file_io": {
        "cluster_id": "file_io_in_request",
        "title": "File I/O in Request Path",
        "severity": Severity.MEDIUM,
        "cwe": [],
        "standards_reference": ["Twelve-Factor App - Processes"],
    },
    "missing_logging": {
        "cluster_id": "missing_logging",
        "title": "Insufficient Logging",
        "severity": Severity.LOW,
        "cwe": ["CWE-778"],
        "owasp": ["A09:2021"],
        "standards_reference": ["OWASP ASVS 7.1.1", "CWE-778"],
    },
    "unused_import": {
        "cluster_id": "unused_imports",
        "title": "Unused Imports",
        "severity": Severity.INFO,
        "cwe": [],
        "standards_reference": [],
    },
    "unused_variable": {
        "cluster_id": "unused_variables",
        "title": "Unused Variables",
        "severity": Severity.INFO,
        "cwe": [],
        "standards_reference": [],
    },
}


def _lookup_cluster(rule_id: str) -> dict[str, object]:
    rid_lower = rule_id.lower()
    for key, entry in CLUSTER_CATALOG.items():
        if key in rid_lower:
            return dict(entry)
    return {
        "cluster_id": rid_lower.replace(" ", "_"),
        "title": rule_id.replace("_", " ").title(),
        "severity": Severity.MEDIUM,
        "cwe": [],
        "owasp": [],
        "standards_reference": [],
    }


def _extract_service(file_path: str) -> str:
    parts = file_path.replace("\\", "/").split("/")
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"
    return parts[0] if parts else "unknown"


SEVERITY_RISK: dict[str, int] = {
    Severity.CRITICAL: 5,
    Severity.HIGH: 4,
    Severity.MEDIUM: 3,
    Severity.LOW: 2,
    Severity.INFO: 1,
}


@dataclass
class FlatEntry:
    rule_id: str
    category: str
    severity: str
    title: str
    description: str
    file_path: str
    line_start: int | None
    recommendation: str
    effort: int
    score_impact: float
    rpm_impact: int


def _flat(
    f: RuleViolation | DeadCodeFinding | ErrorFinding | ReliabilityFinding | DevOpsFinding | MaintainabilityFinding | Finding | dict[str, object] | _SimpleNamespace,
) -> FlatEntry:
    if isinstance(f, RuleViolation):
        return FlatEntry(
            rule_id=f.rule_id,
            category=str(f.category),
            severity=str(f.severity),
            title=f.title,
            description=f.description,
            file_path=f.file_path,
            line_start=f.line_start,
            recommendation=f.recommendation,
            effort=_estimate_effort(f.rule_id, f.title),
            score_impact=f.score_impact,
            rpm_impact=f.rpm_impact,
        )
    effort = _estimate_effort_from_title(getattr(f, "title", ""))
    path: str = getattr(f, "file_path", "")
    if isinstance(f, DeadCodeFinding):
        return FlatEntry(
            rule_id="unused_code",
            category=Category.DEAD_CODE,
            severity=Severity.MEDIUM,
            title=f"Dead code: {f.name}",
            description=f.evidence or f.name,
            file_path=path,
            line_start=f.line_start,
            recommendation="Remove unused code to improve maintainability",
            effort=2,
            score_impact=0.5,
            rpm_impact=0,
        )
    title: str = getattr(f, "title", "")
    if isinstance(f, ErrorFinding):
        return FlatEntry(
            rule_id=getattr(f, "rule_id", "error"),
            category=Category.ERROR,
            severity=str(getattr(f, "severity", Severity.MEDIUM)),
            title=title,
            description=(getattr(f, "description", "") or "")[:200],
            file_path=path,
            line_start=getattr(f, "line_start", None),
            recommendation=getattr(f, "recommendation", "") or "",
            effort=effort,
            score_impact=2.0,
            rpm_impact=0,
        )
    if isinstance(f, ReliabilityFinding):
        return FlatEntry(
            rule_id=f"reliability_{getattr(f, 'reliability_type', 'unknown')}",
            category=Category.RELIABILITY,
            severity=(
                Severity.HIGH
                if getattr(f, "severity", "") in ("critical", "high")
                else Severity.MEDIUM
            ),
            title=title,
            description=(getattr(f, "description", "") or "")[:200],
            file_path=path,
            line_start=getattr(f, "line_start", None),
            recommendation=getattr(f, "recommendation", "") or "",
            effort=effort,
            score_impact=2.0,
            rpm_impact=0,
        )
    if isinstance(f, DevOpsFinding):
        return FlatEntry(
            rule_id=f"devops_{getattr(f, 'devops_type', 'unknown')}",
            category=Category.DEVOPS,
            severity=(
                Severity.HIGH
                if getattr(f, "severity", "") in ("critical", "high")
                else Severity.MEDIUM
            ),
            title=title,
            description=(getattr(f, "description", "") or "")[:200],
            file_path=path,
            line_start=getattr(f, "line_start", None),
            recommendation=getattr(f, "recommendation", "") or "",
            effort=effort,
            score_impact=2.0,
            rpm_impact=0,
        )
    if isinstance(f, MaintainabilityFinding):
        return FlatEntry(
            rule_id=f"maint_{getattr(f, 'maintainability_type', 'unknown')}",
            category=Category.MAINTAINABILITY,
            severity=(
                Severity.HIGH
                if getattr(f, "severity", "") in ("critical", "high", "medium")
                else Severity.MEDIUM
            ),
            title=title,
            description=(getattr(f, "description", "") or "")[:200],
            file_path=path,
            line_start=getattr(f, "line_start", None),
            recommendation=getattr(f, "recommendation", "") or "",
            effort=effort,
            score_impact=2.0,
            rpm_impact=0,
        )
    if isinstance(f, Finding):
        return FlatEntry(
            rule_id=f.rule_id,
            category=str(f.category),
            severity=str(f.severity),
            title=f.title,
            description=f.description,
            file_path=f.file_path,
            line_start=f.line_start,
            recommendation=f.recommendation,
            effort=_estimate_effort(f.rule_id, f.title),
            score_impact=f.score_impact,
            rpm_impact=f.rpm_impact,
        )
    if isinstance(f, _SimpleNamespace):
        return FlatEntry(
            rule_id=getattr(f, "rule_id", "unknown"),
            category=getattr(f, "category", "unknown"),
            severity=str(getattr(f, "severity", Severity.LOW)),
            title=getattr(f, "title", ""),
            description=getattr(f, "description", ""),
            file_path=getattr(f, "file_path", ""),
            line_start=getattr(f, "line_start"),
            recommendation=getattr(f, "recommendation", ""),
            effort=_estimate_effort(
                getattr(f, "rule_id", ""), getattr(f, "title", "")
            ),
            score_impact=getattr(f, "score_impact", 0),
            rpm_impact=getattr(f, "rpm_impact", 0),
        )
    if isinstance(f, dict):
        return FlatEntry(
            rule_id=f.get("rule_id", "unknown"),
            category=f.get("category", "unknown"),
            severity=f.get("severity", Severity.LOW),
            title=f.get("title", ""),
            description=f.get("description", ""),
            file_path=f.get("file_path", ""),
            line_start=f.get("line_start"),
            recommendation=f.get("recommendation", ""),
            effort=_estimate_effort(f.get("rule_id", ""), f.get("title", "")),
            score_impact=f.get("score_impact", 0),
            rpm_impact=f.get("rpm_impact", 0),
        )
    return FlatEntry(
        rule_id="unknown",
        category="unknown",
        severity=Severity.LOW,
        title=title,
        description="",
        file_path=path,
        line_start=None,
        recommendation="",
        effort=15,
        score_impact=0,
        rpm_impact=0,
    )


def _estimate_effort(rule_id: str, title: str) -> int:
    effort_map: dict[str, int] = {
        "unused_import": 2,
        "unused_variable": 2,
        "unused_function": 5,
        "missing_timeout": 5,
        "bare_except": 5,
        "missing_logging": 10,
        "n_plus_one": 15,
        "missing_auth": 20,
        "hardcoded_secret": 10,
        "swallowed_exception": 10,
        "sync_in_async": 30,
        "high_complexity": 45,
        "duplicate_code": 20,
        "long_method": 15,
        "sql_injection": 60,
        "xss": 45,
        "ssrf": 30,
        "jwt": 20,
        "race_condition": 30,
        "thread_safety": 40,
        "missing_validation": 15,
    }
    for pattern, effort in effort_map.items():
        if pattern in title.lower() or pattern in rule_id.lower():
            return effort
    return 30


def _estimate_effort_from_title(title: str) -> int:
    effort_map: dict[str, int] = {
        "bare except": 5,
        "swallowed": 10,
        "timeout": 5,
        "logged": 10,
        "unused": 2,
        "dead code": 5,
    }
    title_lower = title.lower()
    for pattern, effort in effort_map.items():
        if pattern in title_lower:
            return effort
    return 15


SERVICE_PATTERNS: list[tuple[str, str]] = [
    ("frontend", "Frontend"),
    ("ui", "Frontend"),
    ("web", "Frontend"),
    ("auth", "Auth"),
    ("identity", "Auth"),
    ("core", "Core"),
    ("api", "Core"),
    ("gateway", "Core"),
    ("ai", "AI"),
    ("llm", "AI"),
    ("ml", "AI"),
    ("analysis", "Analysis"),
    ("scanner", "Analysis"),
    ("parser", "Analysis"),
    ("realtime", "Realtime"),
    ("websocket", "Realtime"),
    ("events", "Realtime"),
]


def _classify_service(file_path: str) -> str:
    path_lower = file_path.replace("\\", "/").lower()
    for pattern, label in SERVICE_PATTERNS:
        if pattern in path_lower:
            return label
    first_seg = path_lower.split("/")[0]
    return first_seg.replace("_", " ").title() if first_seg else "Unknown"


OWNERSHIP_MAP: list[tuple[list[str], str, str]] = [
    (["security", "auth", "jwt", "crypto", "secret", "xss", "injection"], "Security Team",
     "All security-critical findings require security team review"),
    (["performance", "n_plus_one", "caching", "bottleneck", "sync_in_async", "unbounded"],
     "Platform Team",
     "Performance and scalability concerns affect the platform layer"),
    (["devops", "docker", "deploy", "ci/cd", "pipeline", "kubernetes", "helm"],
     "DevOps Team",
     "Infrastructure and deployment configuration"),
    (["test", "coverage", "assertion", "mock"], "QA Team",
     "Test quality and coverage improvements"),
    (["frontend", "ui", "css", "component", "react", "vue", "angular", "typescript", "jsx", "tsx"],
     "Frontend Team",
     "Frontend-specific code quality and security issues"),
    (["maintainability", "complexity", "duplicate", "long_method", "dead_code", "unused", "quality"],
     "Platform Team",
     "Code maintainability and technical debt"),
]

import re


def _assign_ownership(rule_id: str, title: str, file_path: str) -> dict[str, str]:
    text = f"{rule_id} {title} {file_path}".lower()
    for patterns, team, rationale in OWNERSHIP_MAP:
        if any(p in text for p in patterns):
            return {"recommended_team": team, "rationale": rationale}
    return {"recommended_team": "Backend Team", "rationale": "General backend code ownership"}


def _generate_ai_recommendation(entry: FlatEntry, cluster: dict[str, object]) -> dict[str, object]:
    cluster_id = cluster.get("cluster_id", entry.rule_id)
    cwe = cluster.get("cwe", [])
    standards = cluster.get("standards_reference", [])
    cwe_ref = cwe[0] if cwe else "NIST SP 800-53"
    std_ref = standards[0] if standards else "OWASP ASVS"

    severity = entry.severity
    if severity == Severity.CRITICAL:
        business_impact = "Critical — potential data breach, regulatory fines, and customer trust loss"
        confidence = "high"
    elif severity == Severity.HIGH:
        business_impact = "High — may lead to service degradation or unauthorized access"
        confidence = "high"
    elif severity == Severity.MEDIUM:
        business_impact = "Moderate — impacts maintainability and developer velocity"
        confidence = "medium"
    else:
        business_impact = "Low — minor code quality concern"
        confidence = "medium"

    return {
        "cluster_id": cluster_id,
        "problem": entry.title,
        "root_cause": entry.description[:150] if entry.description else "Identified by static analysis",
        "business_impact": business_impact,
        "enterprise_best_practice": f"Refer to {std_ref} ({cwe_ref}) for remediation guidance",
        "recommended_refactor": entry.recommendation or "Follow OWASP/relevant best practice for remediation",
        "expected_score_gain": abs(entry.score_impact) if entry.score_impact else 1.0,
        "estimated_hours": max(1, entry.effort // 60),
        "ai_confidence": confidence,
    }


class EnterpriseGuide:
    def __init__(self) -> None:
        self.executive_summary: str = ""
        self.critical_issues: list[dict[str, object]] = []
        self.high_issues: list[dict[str, object]] = []
        self.medium_issues: list[dict[str, object]] = []
        self.architecture_review: dict[str, object] | None = None
        self.capacity_analysis: dict[str, object] | None = None
        self.migration_path: list[dict[str, object]] = []
        self.ai_executive_summary: str = ""

        self.repository_health: dict[str, object] | None = None
        self.engineering_scorecard: dict[str, object] | None = None
        self.business_risk: dict[str, object] | None = None
        self.scalability_review: dict[str, object] | None = None
        self.technical_debt: dict[str, object] | None = None
        self.issue_clusters: list[dict[str, object]] | None = None
        self.hotspots: list[dict[str, object]] | None = None
        self.service_health: dict[str, object] | None = None
        self.quick_wins: list[dict[str, object]] | None = None
        self.sprint_roadmap: dict[str, object] | None = None
        self.deployment_readiness: dict[str, object] | None = None
        self.release_recommendation: dict[str, object] | None = None
        self.ownership: list[dict[str, object]] | None = None
        self.estimated_effort: dict[str, object] | None = None
        self.ai_recommendations: list[dict[str, object]] | None = None
        self.raw_findings: list[dict[str, object]] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "executive_summary": self.executive_summary,
            "critical_issues": self.critical_issues,
            "high_issues": self.high_issues,
            "medium_issues": self.medium_issues,
            "architecture_review": self.architecture_review,
            "capacity_analysis": self.capacity_analysis,
            "migration_path": self.migration_path,
            "ai_executive_summary": self.ai_executive_summary,
            "repository_health": self.repository_health,
            "engineering_scorecard": self.engineering_scorecard,
            "business_risk": self.business_risk,
            "scalability_review": self.scalability_review,
            "technical_debt": self.technical_debt,
            "issue_clusters": self.issue_clusters,
            "hotspots": self.hotspots,
            "service_health": self.service_health,
            "quick_wins": self.quick_wins,
            "sprint_roadmap": self.sprint_roadmap,
            "deployment_readiness": self.deployment_readiness,
            "release_recommendation": self.release_recommendation,
            "ownership": self.ownership,
            "estimated_effort": self.estimated_effort,
            "ai_recommendations": self.ai_recommendations,
            "raw_findings": self.raw_findings,
        }


class EnterpriseGuideGenerator:
    """Generates a structured enterprise-grade CTO dashboard from analysis results."""

    async def generate(
        self,
        findings: list[RuleViolation],
        scores: Score,
        perf_metrics: PerformanceMetrics | None = None,
        simulation: list[SimulationResult] | None = None,
        dead_code: list[DeadCodeFinding] | None = None,
        errors: list[ErrorFinding] | None = None,
        reliability: list[ReliabilityFinding] | None = None,
        devops: list[DevOpsFinding] | None = None,
        maintainability: list[MaintainabilityFinding] | None = None,
    ) -> EnterpriseGuide:
        guide = EnterpriseGuide()

        self._generate_executive_summary(guide, scores, perf_metrics, simulation)
        self._group_findings_by_severity(
            guide, findings, dead_code, errors, reliability, devops, maintainability
        )
        self._generate_architecture_review(guide, findings)
        self._generate_capacity_analysis(guide, perf_metrics, simulation)
        self._generate_migration_path(guide, findings, perf_metrics)

        # ── New structured sections ──────────────────────────────
        self._generate_structured_executive_summary(guide, scores)
        self._generate_engineering_scorecard(guide, scores, findings)

        entries = self._collect_entries(
            findings, dead_code, errors, reliability, devops, maintainability
        )

        self._generate_issue_clusters(guide, entries)
        self._generate_hotspots(guide, entries)
        self._generate_service_health(guide, entries)
        self._generate_business_risk(guide, scores, entries)
        self._generate_technical_debt(guide, entries)
        self._generate_quick_wins(guide, entries)
        self._generate_scalability_review(guide, scores, perf_metrics, simulation)
        self._generate_deployment_readiness(guide, scores)
        self._generate_release_recommendation(guide, scores)
        self._generate_sprint_roadmap(guide, entries)
        self._generate_ownership(guide, entries)
        self._generate_estimated_effort(guide, entries)
        self._generate_raw_findings(guide, entries)
        self._generate_ai_recommendations(guide, entries, guide.issue_clusters)

        logger.info(
            "enterprise_guide_generated",
            total_entries=len(entries),
            cluster_count=len(guide.issue_clusters or []),
            hotspot_count=len(guide.hotspots or []),
        )
        return guide

    # ── Legacy methods (unchanged) ───────────────────────────────

    def _generate_executive_summary(
        self,
        guide: EnterpriseGuide,
        scores: Score,
        perf_metrics: PerformanceMetrics | None,
        simulation: list[SimulationResult] | None,
    ) -> None:
        tier_label = (
            scores.tier.value if isinstance(scores.tier, Tiers) else str(scores.tier)
        )

        def _fmt(v: int | None) -> str:
            return str(v) if v is not None else "N/A"

        parts = [
            f"Production Readiness Score: {scores.overall}/100 ({tier_label})",
            f"Security: {_fmt(scores.security)} | Performance: {_fmt(scores.performance)} | "
            f"Reliability: {_fmt(scores.reliability)} | Maintainability: {_fmt(scores.maintainability)} | "
            f"DevOps: {_fmt(scores.devops)}",
        ]
        if perf_metrics:
            parts.append(f"Estimated System RPM: {perf_metrics.overall_rpm}")
            parts.append(
                f"Breaks at: {perf_metrics.breaks_at_concurrent_users} concurrent users"
            )
        if simulation and len(simulation) > 0:
            last = simulation[-1]
            parts.append(
                f"Simulation status at {last.concurrent_users} users: {last.status}"
            )
        guide.executive_summary = "\n".join(parts)

    def _group_findings_by_severity(
        self,
        guide: EnterpriseGuide,
        findings: list[RuleViolation],
        dead_code: list[DeadCodeFinding] | None,
        errors: list[ErrorFinding] | None,
        reliability: list[ReliabilityFinding] | None = None,
        devops: list[DevOpsFinding] | None = None,
        maintainability: list[MaintainabilityFinding] | None = None,
    ) -> None:
        all_entries: list[tuple[object, ...]] = []
        for f in findings:
            entry = (
                f.title,
                f"{f.file_path}:{f.line_start}" if f.file_path else "unknown",
                str(f.severity),
                (f.description or "")[:200],
                f.recommendation or "",
                getattr(f, "enterprise_pattern", "") or "",
                _estimate_effort(f.rule_id, f.title),
            )
            all_entries.append((f.severity, *entry))

        for source_list, source_severity, label_prefix in [
            (dead_code, Severity.MEDIUM, "Dead code"),
            (errors, None, ""),
            (reliability, None, ""),
            (devops, None, ""),
            (maintainability, None, ""),
        ]:
            if not source_list:
                continue
            for item in source_list:
                sev = str(getattr(item, "severity", source_severity or Severity.MEDIUM))
                title = getattr(item, "title", "")
                path = getattr(item, "file_path", "") or ""
                line = getattr(item, "line_start", None)
                desc = (getattr(item, "description", "") or "")[:200]
                rec = getattr(item, "recommendation", "") or ""
                all_entries.append(
                    (
                        sev,
                        f"{label_prefix}: {title}" if label_prefix else title,
                        f"{path}:{line}" if line else path,
                        sev,
                        desc,
                        rec,
                        "",
                        _estimate_effort_from_title(title),
                    )
                )

        for _sev, title, file_ref, sev, desc, rec, ep, effort in all_entries:
            issue_entry: dict[str, object] = {
                "title": title,
                "file": file_ref,
                "severity": sev,
                "impact": desc,
                "recommendation": rec,
                "enterprise_pattern": ep,
                "estimated_effort": effort,
            }
            if sev in ("critical", Severity.CRITICAL):
                guide.critical_issues.append(issue_entry)
            elif sev in ("high", Severity.HIGH):
                guide.high_issues.append(issue_entry)
            elif sev in ("medium", Severity.MEDIUM):
                guide.medium_issues.append(issue_entry)

    def _generate_architecture_review(
        self,
        guide: EnterpriseGuide,
        findings: list[RuleViolation],
    ) -> None:
        total = len(findings)
        by_category: dict[str, int] = {}
        for f in findings:
            cat = str(f.category)
            by_category[cat] = by_category.get(cat, 0) + 1
        most_affected = sorted(by_category.items(), key=lambda x: -x[1])[:3]
        guide.architecture_review = {
            "total_findings": total,
            "most_affected_areas": [
                {"category": cat, "count": count} for cat, count in most_affected
            ],
            "summary": (
                f"Found {total} issues across {len(by_category)} categories. "
                f"Primary concerns: {', '.join(c for c, _ in most_affected)}."
                if most_affected
                else "No significant architectural concerns detected."
            ),
        }

    def _generate_capacity_analysis(
        self,
        guide: EnterpriseGuide,
        perf_metrics: PerformanceMetrics | None,
        simulation: list[SimulationResult] | None,
    ) -> None:
        if not perf_metrics:
            guide.capacity_analysis = {"status": "not_available"}
            return
        capacity: dict[str, object] = {
            "estimated_rpm": perf_metrics.overall_rpm,
            "breaks_at_concurrent_users": perf_metrics.breaks_at_concurrent_users,
            "bottlenecks": perf_metrics.bottlenecks,
        }
        if simulation:
            capacity["simulation_results"] = [
                {
                    "users": s.concurrent_users,
                    "status": s.status,
                    "error_rate_pct": s.error_rate_pct,
                    "overall_rpm": s.overall_rpm,
                }
                for s in simulation
            ]
        guide.capacity_analysis = capacity

    def _generate_migration_path(
        self,
        guide: EnterpriseGuide,
        findings: list[RuleViolation],
        perf_metrics: PerformanceMetrics | None,
    ) -> None:
        steps: list[dict[str, object]] = []
        for f in findings:
            if str(f.severity) not in ("critical", "high"):
                continue
            effort = _estimate_effort(f.rule_id, f.title)
            rpm_gain = abs(f.rpm_impact) if f.rpm_impact else 50
            score_gain = abs(f.score_impact)
            priority_score = (rpm_gain + score_gain * 10) / max(effort, 1)
            steps.append(
                {
                    "action": f.title,
                    "file": (
                        f"{f.file_path}:{f.line_start}" if f.file_path else "unknown"
                    ),
                    "effort_minutes": effort,
                    "rpm_impact": f"+{rpm_gain} RPM",
                    "score_impact": f"+{score_gain} points",
                    "fix_snippet": f.recommendation,
                    "priority_score": priority_score,
                }
            )
        steps.sort(key=lambda s: s["priority_score"], reverse=True)  # type: ignore[arg-type, return-value]
        for i, step in enumerate(steps, 1):
            step["step"] = i
            del step["priority_score"]
        guide.migration_path = steps

    # ── Helpers ──────────────────────────────────────────────────

    def _collect_entries(
        self,
        findings: list[RuleViolation],
        dead_code: list[DeadCodeFinding] | None,
        errors: list[ErrorFinding] | None,
        reliability: list[ReliabilityFinding] | None,
        devops: list[DevOpsFinding] | None,
        maintainability: list[MaintainabilityFinding] | None,
    ) -> list[FlatEntry]:
        entries: list[FlatEntry] = [_flat(f) for f in findings]
        for src in [dead_code, errors, reliability, devops, maintainability]:
            if src:
                entries.extend(_flat(f) for f in src)
        return entries

    @staticmethod
    def _score_to_risk_level(score: int | None) -> str:
        if score is None:
            return "unknown"
        if score >= 80:
            return "low"
        if score >= 60:
            return "medium"
        if score >= 40:
            return "high"
        return "critical"

    # ── New structured methods ───────────────────────────────────

    def _generate_structured_executive_summary(
        self, guide: EnterpriseGuide, scores: Score
    ) -> None:
        overall = scores.overall
        grade = score_to_grade(overall)
        tier = scores.tier.value if scores.tier else "Unknown"
        health = score_to_status(overall)

        if overall is None:
            remediation_time = "unknown"
            team_size = None
        elif overall < 40:
            remediation_time = "160+ hours"
            team_size = 4
        elif overall < 60:
            remediation_time = "80-160 hours"
            team_size = 3
        elif overall < 75:
            remediation_time = "40-80 hours"
            team_size = 2
        elif overall < 90:
            remediation_time = "10-40 hours"
            team_size = 1
        else:
            remediation_time = "0-10 hours"
            team_size = 1

        guide.repository_health = {
            "overall_score": overall,
            "overall_grade": grade,
            "repository_health": health,
            "production_readiness": tier,
            "deployment_readiness": self._compute_deployment_readiness(scores),
            "release_recommendation": self._compute_release_rec(scores),
            "business_risk": self._score_to_risk_level(overall),
            "engineering_risk": self._score_to_risk_level(scores.maintainability),
            "technical_debt_level": self._score_to_risk_level(
                scores.maintainability
            ),
            "estimated_remediation_time": remediation_time,
            "estimated_team_size": team_size,
        }

    def _compute_deployment_readiness(self, scores: Score) -> str:
        if scores.overall is None:
            return "unknown"
        if scores.overall >= 80 and (scores.security or 100) >= 70:
            return "ready"
        if scores.overall >= 60:
            return "conditional"
        return "not_ready"

    def _compute_release_rec(self, scores: Score) -> str:
        if scores.overall is None:
            return "unknown"
        if scores.overall >= 80 and (scores.security or 100) >= 75:
            return "go"
        if scores.overall >= 60:
            return "proceed_with_caution"
        return "no_go"

    def _generate_engineering_scorecard(
        self,
        guide: EnterpriseGuide,
        scores: Score,
        findings: list[RuleViolation],
    ) -> None:
        cat_findings: dict[str, list[RuleViolation]] = defaultdict(list)
        for f in findings:
            cat_findings[str(f.category)].append(f)

        def card(
            cat: str, cat_score: int | None, label: str
        ) -> dict[str, object]:
            cat_f = cat_findings.get(cat, [])
            severity_counts = Counter(str(f.severity) for f in cat_f)
            biggest = ""
            rec = ""
            if cat_f:
                biggest = cat_f[0].title
                rec = next(
                    (f.recommendation for f in cat_f if f.recommendation),
                    f"Review all {cat} findings",
                )
            return {
                "score": cat_score,
                "grade": score_to_grade(cat_score),
                "trend": "stable",
                "industry_comparison": (
                    "below_average"
                    if cat_score is not None and cat_score < 70
                    else "average" if cat_score is not None and cat_score < 85 else "above_average"
                ),
                "biggest_problem": biggest,
                "best_recommendation": rec,
                "total_findings": len(cat_f),
                "severity_breakdown": dict(severity_counts),
            }

        guide.engineering_scorecard = {
            "security": card(
                Category.SECURITY, scores.security, "Security"
            ),
            "performance": card(
                Category.PERFORMANCE, scores.performance, "Performance"
            ),
            "reliability": card(
                Category.RELIABILITY, scores.reliability, "Reliability"
            ),
            "maintainability": card(
                Category.MAINTAINABILITY, scores.maintainability, "Maintainability"
            ),
            "devops": card(Category.DEVOPS, scores.devops, "DevOps"),
        }

    def _generate_issue_clusters(
        self, guide: EnterpriseGuide, entries: list[FlatEntry]
    ) -> None:
        groups: dict[str, list[FlatEntry]] = defaultdict(list)
        for e in entries:
            groups[e.rule_id].append(e)

        clusters: list[dict[str, object]] = []
        for rule_id, group in sorted(groups.items(), key=lambda x: -len(x[1])):
            cluster_template = _lookup_cluster(rule_id)
            services = sorted(
                set(_classify_service(e.file_path) for e in group)
            )
            files = sorted(
                set(
                    f"{e.file_path}:{e.line_start}" if e.line_start else e.file_path
                    for e in group
                )
            )
            severity_counts = Counter(e.severity for e in group)
            total_effort = sum(e.effort for e in group)
            rep = max(group, key=lambda e: SEVERITY_RISK.get(e.severity, 0))

            clusters.append(
                {
                    "cluster_id": cluster_template["cluster_id"],
                    "title": cluster_template["title"],
                    "total_count": len(group),
                    "severity": cluster_template.get("severity", Severity.MEDIUM),
                    "severity_breakdown": dict(severity_counts),
                    "affected_services": services,
                    "total_files": len(files),
                    "representative_file": (
                        f"{rep.file_path}:{rep.line_start}"
                        if rep.line_start
                        else rep.file_path
                    ),
                    "root_cause": (rep.description or "")[:200],
                    "enterprise_recommendation": rep.recommendation
                    or "Follow OWASP/relevant best practice for remediation",
                    "estimated_fix_time": total_effort,
                    "cwe": cluster_template.get("cwe", []),
                    "owasp": cluster_template.get("owasp", []),
                    "standards_reference": cluster_template.get(
                        "standards_reference", []
                    ),
                }
            )

        guide.issue_clusters = clusters

    def _generate_hotspots(
        self, guide: EnterpriseGuide, entries: list[FlatEntry]
    ) -> None:
        dir_groups: dict[str, list[FlatEntry]] = defaultdict(list)
        for e in entries:
            dir_path = str(Path(e.file_path).parent) if e.file_path else "unknown"
            dir_groups[dir_path].append(e)

        hotspots: list[dict[str, object]] = []
        for dir_path, group in dir_groups.items():
            severity_counts = Counter(e.severity for e in group)
            risk_score = min(
                100,
                int(
                    sum(
                        SEVERITY_WEIGHTS.get(s, 0) * c
                        for s, c in severity_counts.items()
                    )
                    * 2.5
                ),
            )
            top = max(group, key=lambda e: SEVERITY_RISK.get(e.severity, 0))
            total_effort = sum(e.effort for e in group)

            if risk_score < 10:
                continue

            if risk_score >= 70:
                priority = "P0"
            elif risk_score >= 50:
                priority = "P1"
            elif risk_score >= 30:
                priority = "P2"
            else:
                priority = "P3"

            hotspots.append(
                {
                    "path": dir_path,
                    "risk_score": risk_score,
                    "reason": f"{severity_counts.get(Severity.CRITICAL, 0)} critical, "
                    f"{severity_counts.get(Severity.HIGH, 0)} high findings across {len(group)} files",
                    "priority": priority,
                    "estimated_effort": total_effort,
                    "total_findings": len(group),
                    "severity_breakdown": dict(severity_counts),
                    "top_issue": top.title,
                }
            )

        hotspots.sort(key=lambda h: h["risk_score"], reverse=True)
        guide.hotspots = hotspots[:20]

    def _generate_service_health(
        self, guide: EnterpriseGuide, entries: list[FlatEntry]
    ) -> None:
        service_groups: dict[str, list[FlatEntry]] = defaultdict(list)
        for e in entries:
            service = _classify_service(e.file_path)
            service_groups[service].append(e)

        health: dict[str, object] = {}
        for service, group in sorted(service_groups.items()):
            severity_counts = Counter(e.severity for e in group)
            total = len(group)
            critical = severity_counts.get(Severity.CRITICAL, 0)
            high = severity_counts.get(Severity.HIGH, 0)
            base = 100
            base -= critical * 15
            base -= high * 8
            base -= severity_counts.get(Severity.MEDIUM, 0) * 3
            base -= severity_counts.get(Severity.LOW, 0) * 1
            health_score = max(0, min(100, base))

            cat_count: dict[str, int] = Counter(e.category for e in group)

            health[service] = {
                "health_score": health_score,
                "grade": score_to_grade(health_score),
                "security": cat_count.get(Category.SECURITY, 0),
                "performance": cat_count.get(Category.PERFORMANCE, 0),
                "reliability": cat_count.get(Category.RELIABILITY, 0),
                "maintainability": cat_count.get(Category.MAINTAINABILITY, 0),
                "total_findings": total,
                "critical_count": critical,
                "high_count": high,
                "recommendation": (
                    f"Priority remediation needed ({critical} critical, {high} high)"
                    if critical > 0 or high > 5
                    else f"Routine maintenance ({total} findings)"
                ),
            }

        guide.service_health = health

    def _generate_business_risk(
        self,
        guide: EnterpriseGuide,
        scores: Score,
        entries: list[FlatEntry],
    ) -> None:
        severity_counts = Counter(e.severity for e in entries)
        cat_counts: dict[str, int] = Counter(e.category for e in entries)
        critical = severity_counts.get(Severity.CRITICAL, 0)
        high = severity_counts.get(Severity.HIGH, 0)
        has_critical_security = (
            critical > 0
            and cat_counts.get(Category.SECURITY, 0) > 0
        )

        def _risk(critical_count: int, high_count: int, threshold_c: int, threshold_h: int) -> str:
            if critical_count >= threshold_c:
                return "critical"
            if high_count >= threshold_h:
                return "high"
            if critical_count > 0 or high_count > threshold_h // 2:
                return "medium"
            return "low"

        guide.business_risk = {
            "revenue_risk": _risk(critical, high, 3, 8),
            "customer_impact": (
                "high"
                if (scores.performance is not None and scores.performance < 60)
                else _risk(critical, high, 2, 5)
            ),
            "compliance_risk": (
                "high" if has_critical_security else _risk(critical, high, 1, 4)
            ),
            "reputation_risk": (
                "high" if has_critical_security else _risk(critical, high, 2, 6)
            ),
            "downtime_risk": (
                "high"
                if (scores.reliability is not None and scores.reliability < 50)
                else _risk(critical, high, 3, 8)
            ),
            "operational_risk": _risk(critical, high, 2, 6),
            "details": (
                f"{critical} critical, {high} high severity issues found. "
                f"{'Security vulnerabilities present — compliance and reputation at risk.' if has_critical_security else ''}"
                f"{'Performance score below 60 — customer experience may be impacted.' if scores.performance is not None and scores.performance < 60 else ''}"
            ),
        }

    def _generate_technical_debt(
        self, guide: EnterpriseGuide, entries: list[FlatEntry]
    ) -> None:
        cat_effort: dict[str, int] = defaultdict(int)
        cat_count: dict[str, int] = defaultdict(int)
        cat_severity: dict[str, list[str]] = defaultdict(list)

        CATEGORY_DEBT_MAP: dict[str, str] = {
            Category.SECURITY: "security_debt",
            Category.STRUCTURE: "architecture_debt",
            Category.PERFORMANCE: "performance_debt",
            Category.MAINTAINABILITY: "maintainability_debt",
            Category.QUALITY: "maintainability_debt",
            Category.DEAD_CODE: "maintainability_debt",
            Category.RELIABILITY: "performance_debt",
            Category.DEVOPS: "devops_debt",
            Category.ERROR: "maintainability_debt",
        }

        for e in entries:
            debt_key = CATEGORY_DEBT_MAP.get(e.category, "other_debt")
            cat_effort[debt_key] += e.effort
            cat_count[debt_key] += 1
            cat_severity[debt_key].append(e.severity)

        def debt_section(key: str, label: str) -> dict[str, object]:
            cnt = cat_count.get(key, 0)
            hrs = cat_effort.get(key, 0)
            sevs = cat_severity.get(key, [])
            return {
                "count": cnt,
                "estimated_minutes": hrs,
                "estimated_hours": round(hrs / 60, 1),
                "severity": (
                    "critical" if any(s == Severity.CRITICAL for s in sevs)
                    else "high" if any(s == Severity.HIGH for s in sevs)
                    else "medium" if cnt > 0 else "low"
                ),
                "label": label,
            }

        guide.technical_debt = {
            "security_debt": debt_section("security_debt", "Security Debt"),
            "architecture_debt": debt_section("architecture_debt", "Architecture Debt"),
            "performance_debt": debt_section("performance_debt", "Performance Debt"),
            "maintainability_debt": debt_section(
                "maintainability_debt", "Maintainability Debt"
            ),
            "devops_debt": debt_section("devops_debt", "DevOps Debt"),
            "other_debt": debt_section("other_debt", "Other Debt"),
        }

    def _generate_quick_wins(
        self, guide: EnterpriseGuide, entries: list[FlatEntry]
    ) -> None:
        quick = [e for e in entries if e.effort <= 30]
        quick.sort(key=lambda e: SEVERITY_RISK.get(e.severity, 0), reverse=True)

        guide.quick_wins = [
            {
                "title": e.title,
                "file": f"{e.file_path}:{e.line_start}" if e.line_start else e.file_path,
                "estimated_impact": (
                    "high" if e.severity in (Severity.CRITICAL, Severity.HIGH) else "medium"
                ),
                "estimated_time": e.effort,
                "priority": (
                    "P0" if e.severity == Severity.CRITICAL
                    else "P1" if e.severity == Severity.HIGH
                    else "P2"
                ),
                "expected_score_improvement": abs(e.score_impact) if e.score_impact else 0.5,
            }
            for e in quick[:15]
        ]

    def _generate_scalability_review(
        self,
        guide: EnterpriseGuide,
        scores: Score,
        perf_metrics: PerformanceMetrics | None,
        simulation: list[SimulationResult] | None,
    ) -> None:
        if not perf_metrics:
            guide.scalability_review = {
                "estimated_rpm": None,
                "estimated_concurrent_users": None,
                "status": "not_available",
            }
            return

        rpm = perf_metrics.overall_rpm
        breaks_at = perf_metrics.breaks_at_concurrent_users
        bottlenecks = perf_metrics.bottlenecks[:3] if perf_metrics.bottlenecks else []

        concurrent_users = breaks_at if breaks_at else 0
        db_score = scores.reliability
        rpm_grade = score_to_status(rpm // 100) if rpm else "not_assessed"

        guide.scalability_review = {
            "estimated_rpm": rpm,
            "estimated_concurrent_users": concurrent_users,
            "expected_bottleneck": bottlenecks[0] if bottlenecks else "Database connections under load",
            "rpm_grade": rpm_grade,
            "database_scalability": {
                "score": db_score,
                "grade": score_to_grade(db_score),
                "recommendation": (
                    "Add read replicas and implement database connection pooling"
                    if db_score is not None and db_score < 70
                    else "Current database configuration appears adequate"
                ),
            },
            "cache_recommendation": (
                "Implement Redis/Memcached for API response caching and session storage"
                if perf_metrics.bottlenecks and any("db" in b.lower() for b in perf_metrics.bottlenecks)
                else "Evaluate caching strategy for frequently accessed data"
            ),
            "queue_recommendation": (
                "Offload async tasks to a message queue (RabbitMQ/SQS) to reduce request latency"
                if rpm and rpm > 5000
                else "Current synchronous processing may be acceptable at current scale"
            ),
            "horizontal_scaling_readiness": {
                "score": 70 if rpm and rpm > 10000 else 85,
                "grade": "B" if rpm and rpm > 10000 else "A",
                "status": "partial" if rpm and rpm > 10000 else "ready",
            },
            "vertical_scaling_readiness": {
                "score": 85,
                "grade": "B",
                "status": "ready",
            },
            "infrastructure_cost_projection": (
                "high increase at 2x scale — consider optimization" if rpm and rpm > 20000
                else "moderate increase at 2x scale"
            ),
        }

        if simulation:
            guide.scalability_review["simulation_results"] = [
                {
                    "users": s.concurrent_users,
                    "status": s.status,
                    "error_rate_pct": s.error_rate_pct,
                    "overall_rpm": s.overall_rpm,
                }
                for s in simulation
            ]

    def _generate_deployment_readiness(
        self, guide: EnterpriseGuide, scores: Score
    ) -> None:
        readiness = self._compute_deployment_readiness(scores)
        guide.deployment_readiness = {
            "status": readiness,
            "overall_score": scores.overall,
            "security_check": (
                "passed" if scores.security is not None and scores.security >= 70 else "failed"
            ),
            "performance_check": (
                "passed" if scores.performance is not None and scores.performance >= 60 else "failed"
            ),
            "reliability_check": (
                "passed" if scores.reliability is not None and scores.reliability >= 60 else "failed"
            ),
            "maintainability_check": (
                "passed" if scores.maintainability is not None and scores.maintainability >= 50 else "failed"
            ),
            "recommendation": (
                "Ready for deployment to production"
                if readiness == "ready"
                else "Address critical issues before deploying to production"
                if readiness == "not_ready"
                else "Can deploy with monitoring — address security concerns in parallel"
            ),
        }

    def _generate_release_recommendation(
        self, guide: EnterpriseGuide, scores: Score
    ) -> None:
        rec = self._compute_release_rec(scores)
        guide.release_recommendation = {
            "decision": rec,
            "overall_score": scores.overall,
            "grade": score_to_grade(scores.overall),
            "security_grade": score_to_grade(scores.security),
            "performance_grade": score_to_grade(scores.performance),
            "reliability_grade": score_to_grade(scores.reliability),
            "description": (
                "All checks pass — ready for production release"
                if rec == "go"
                else "Address critical issues before release"
                if rec == "no_go"
                else "Monitor closely — proceed with rollback plan"
            ),
        }

    def _generate_sprint_roadmap(
        self,
        guide: EnterpriseGuide,
        entries: list[FlatEntry],
    ) -> None:
        sprints: dict[str, list[FlatEntry]] = {
            "sprint_1": [],
            "sprint_2": [],
            "sprint_3": [],
            "sprint_4": [],
        }

        p0 = [e for e in entries if e.severity == Severity.CRITICAL]
        p1 = [e for e in entries if e.severity == Severity.HIGH]
        p2 = [e for e in entries if e.severity == Severity.MEDIUM]
        p3 = [
            e
            for e in entries
            if e.severity not in (Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM)
        ]

        sprints["sprint_1"] = p0 + p1[: max(0, 8 - len(p0))]
        remaining_p1 = p1[len(sprints["sprint_1"]) - len(p0) :]
        sprints["sprint_2"] = remaining_p1 + p2[: max(0, 10 - len(remaining_p1))]
        remaining_p2 = p2[len(sprints["sprint_2"]) - len(remaining_p1) :]
        sprints["sprint_3"] = remaining_p2 + p3[: max(0, 10 - len(remaining_p2))]
        sprints["sprint_4"] = p3[len(sprints["sprint_3"]) - len(remaining_p2) :]

        roadmap: dict[str, object] = {}
        sprint_labels = [
            ("sprint_1", "Security & Critical Fixes", 1),
            ("sprint_2", "High Priority Issues", 2),
            ("sprint_3", "Medium Priority & Performance", 3),
            ("sprint_4", "Tech Debt & Polish", 4),
        ]

        for key, label, num in sprint_labels:
            items = sprints[key]
            if not items:
                roadmap[key] = {
                    "sprint_number": num,
                    "title": label,
                    "objectives": ["No critical issues remaining — focus on preventive measures"],
                    "tasks": [],
                    "estimated_hours": 0,
                    "expected_score_gain": 0,
                }
                continue

            tasks = list(
                dict.fromkeys(
                    f"{e.title} — {e.file_path}" for e in items
                )
            )[:8]
            total_effort = sum(e.effort for e in items)

            severity_counts = Counter(e.severity for e in items)
            score_gain = int(
                severity_counts.get(Severity.CRITICAL, 0) * 5
                + severity_counts.get(Severity.HIGH, 0) * 3
                + severity_counts.get(Severity.MEDIUM, 0) * 1
            )

            roadmap[key] = {
                "sprint_number": num,
                "title": label,
                "objectives": [
                    f"Resolve {len(items)} findings"
                    f"{' (security focus)' if key == 'sprint_1' else ''}"
                ],
                "tasks": tasks,
                "estimated_hours": max(1, total_effort // 60),
                "expected_score_gain": min(100, score_gain),
            }

        guide.sprint_roadmap = roadmap

    def _generate_ownership(
        self,
        guide: EnterpriseGuide,
        entries: list[FlatEntry],
    ) -> None:
        team_groups: dict[str, list[FlatEntry]] = defaultdict(list)
        for e in entries:
            ow = _assign_ownership(e.rule_id, e.title, e.file_path)
            team_groups[ow["recommended_team"]].append(e)

        ownership_list: list[dict[str, object]] = []
        for team, team_entries in sorted(team_groups.items()):
            categories = sorted(set(e.category for e in team_entries))
            total = len(team_entries)
            effort = sum(e.effort for e in team_entries)
            rationale = _assign_ownership(
                team_entries[0].rule_id,
                team_entries[0].title,
                team_entries[0].file_path,
            )["rationale"]

            ownership_list.append(
                {
                    "recommended_team": team,
                    "total_findings": total,
                    "estimated_hours": max(1, effort // 60),
                    "categories": categories,
                    "rationale": rationale,
                }
            )

        ownership_list.sort(key=lambda x: x["total_findings"], reverse=True)
        guide.ownership = ownership_list

    def _generate_estimated_effort(
        self,
        guide: EnterpriseGuide,
        entries: list[FlatEntry],
    ) -> None:
        total_minutes = sum(e.effort for e in entries)
        by_severity: dict[str, int] = defaultdict(int)
        by_category: dict[str, int] = defaultdict(int)

        for e in entries:
            by_severity[e.severity] += e.effort
            by_category[e.category] += e.effort

        guide.estimated_effort = {
            "total_minutes": total_minutes,
            "total_hours": round(total_minutes / 60, 1),
            "total_days": round(total_minutes / 60 / 6, 1),
            "by_severity": dict(by_severity),
            "by_category": dict(by_category),
        }

    def _generate_raw_findings(
        self, guide: EnterpriseGuide, entries: list[FlatEntry]
    ) -> None:
        entries.sort(key=lambda e: SEVERITY_RISK.get(e.severity, 0), reverse=True)
        samples: list[dict[str, object]] = []
        seen_titles: set[str] = set()

        for e in entries:
            if e.title not in seen_titles:
                samples.append(
                    {
                        "rule_id": e.rule_id,
                        "category": e.category,
                        "severity": e.severity,
                        "title": e.title,
                        "file": (
                            f"{e.file_path}:{e.line_start}"
                            if e.line_start
                            else e.file_path
                        ),
                        "description": (e.description or "")[:200],
                        "recommendation": e.recommendation,
                        "estimated_effort": e.effort,
                    }
                )
                seen_titles.add(e.title)

        guide.raw_findings = samples[:30]

    def _generate_ai_recommendations(
        self,
        guide: EnterpriseGuide,
        entries: list[FlatEntry],
        clusters: list[dict[str, object]] | None,
    ) -> None:
        if not clusters:
            guide.ai_recommendations = []
            return

        cluster_map: dict[str, list[FlatEntry]] = defaultdict(list)
        for e in entries:
            cluster_lookup = _lookup_cluster(e.rule_id)
            cluster_map[cluster_lookup["cluster_id"]].append(e)

        recommendations: list[dict[str, object]] = []
        for cluster in clusters:
            cid: str = cluster["cluster_id"]  # type: ignore[assignment]
            group = cluster_map.get(cid, [])
            if group:
                rep = max(group, key=lambda e: SEVERITY_RISK.get(e.severity, 0))
                recommendations.append(
                    _generate_ai_recommendation(rep, cluster)
                )

        recommendations.sort(
            key=lambda r: (
                0 if r.get("ai_confidence") == "high"
                else 1 if r.get("ai_confidence") == "medium"
                else 2
            )
        )
        guide.ai_recommendations = recommendations
