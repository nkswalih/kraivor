from enum import StrEnum


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Category(StrEnum):
    PERFORMANCE = "performance"
    SECURITY = "security"
    RELIABILITY = "reliability"
    MAINTAINABILITY = "maintainability"
    DEVOPS = "devops"
    DEAD_CODE = "dead_code"
    ERROR = "error"
    STRUCTURE = "structure"
    QUALITY = "quality"


class JobStatus(StrEnum):
    QUEUED = "queued"
    CLONING = "cloning"
    PARSING = "parsing"
    RULES = "rules"
    DEAD_CODE = "dead_code"
    ERRORS = "errors"
    PERF = "perf"
    SIMULATION = "simulation"
    SCORING = "scoring"
    GUIDE_GEN = "guide_gen"
    COMPLETED = "completed"
    FAILED = "failed"


class TriggerType(StrEnum):
    MANUAL = "manual"
    WEBHOOK = "webhook"
    SCHEDULED = "scheduled"
    API = "api"


class EngineStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    DISABLED = "disabled"
    NOT_CONFIGURED = "not_configured"


# Engines whose failure blocks the overall score from being computed
CORE_ENGINES: set[str] = {
    "security",
    "maintainability",
}


class FindingStatus(StrEnum):
    ACTIVE = "active"
    DISMISSED = "dismissed"


class SimulationStatus(StrEnum):
    STABLE = "stable"
    DEGRADED = "degraded"
    FAILING = "failing"


class Tiers(StrEnum):
    PRODUCTION_READY = "Production Ready"
    MINOR_ISSUES = "Minor Issues"
    NEEDS_WORK = "Needs Work"
    SIGNIFICANT_RISK = "Significant Risk"
    CRITICAL_STATE = "Critical State"


class DeadCodeType(StrEnum):
    UNUSED_IMPORT = "unused_import"
    UNUSED_FUNCTION = "unused_function"
    UNUSED_VARIABLE = "unused_variable"
    DEAD_ROUTE = "dead_route"
    ORPHAN_CLASS = "orphan_class"
    UNREACHABLE_CODE = "unreachable_code"
    UNUSED_PARAMETER = "unused_parameter"
    UNUSED_ASSIGNMENT = "unused_assignment"


class ErrorType(StrEnum):
    BARE_EXCEPT = "bare_except"
    SWALLOWED_EXCEPTION = "swallowed_exception"
    MISSING_TRY = "missing_try"
    UNHANDLED_EXCEPTION = "unhandled_exception"
    MISSING_VALIDATION = "missing_validation"
    MISSING_TIMEOUT = "missing_timeout"
    SILENT_FAIL = "silent_fail"
    IMPROPER_ERROR_PROPAGATION = "improper_error_propagation"


class QueueNames(StrEnum):
    HIGH = "analysis.high"
    NORMAL = "analysis.normal"
    BULK = "analysis.bulk"


# Score engine constants
DEFAULT_SCORE_WEIGHTS: dict[str, float] = {
    Category.PERFORMANCE: 0.25,
    Category.SECURITY: 0.25,
    Category.RELIABILITY: 0.20,
    Category.MAINTAINABILITY: 0.15,
    Category.DEVOPS: 0.15,
}

SEVERITY_PENALTIES: dict[Severity, float] = {
    Severity.CRITICAL: 15.0,
    Severity.HIGH: 10.0,
    Severity.MEDIUM: 5.0,
    Severity.LOW: 2.0,
    Severity.INFO: 0.0,
}

SCORE_TIER_THRESHOLDS: list[tuple[float, Tiers]] = [
    (90, Tiers.PRODUCTION_READY),
    (75, Tiers.MINOR_ISSUES),
    (60, Tiers.NEEDS_WORK),
    (40, Tiers.SIGNIFICANT_RISK),
    (0, Tiers.CRITICAL_STATE),
]

# RPM deduction keys — each must be referenced in rpm_calculator.py
RPM_DEDUCTIONS: dict[str, int] = {
    "n_plus_one": 400,
    "sync_external_call": 200,
    "unbounded_query": 300,
    "sync_in_async": 200,
    "high_complexity": 100,
    "file_io_in_request": 150,
    "no_caching": 100,
    "serialization_bottleneck": 150,
    "many_db_queries": 50,
}
