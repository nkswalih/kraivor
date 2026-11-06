"""Canonical analysis engine catalogue.

Single source of truth for which engines exist, what they are called, which
pipeline stage runs them, and which scoring category each one feeds.

This module exists because the engine list had drifted into four disagreeing
copies: the pipeline tracked 8 engines, the scorer tracked its 5 scoring
categories, the insights builder listed 6, and the job page hardcoded 5.
`dead_code` and `error_detection` ran on every analysis and appeared in none of
the frontend lists, so they were invisible while doing real work -- and
`churn` ran untracked entirely. The pipeline, the scorer and GET /jobs/engines
all read from here now, so the list has one origin.

The catalogue describes engines. `scorer.CATEGORY_ORDER` describes scoring
dimensions. Those overlap but are not the same thing, and neither is derived
from the other.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EngineSpec:
    """One analysis engine as the API and UI describe it."""

    key: str
    label: str
    description: str
    #: Pipeline stage that runs this engine.
    stage: str
    #: Scoring category this engine feeds, or None if it reports findings
    #: without contributing a score dimension.
    score_category: str | None = None


ENGINE_SPECS: tuple[EngineSpec, ...] = (
    EngineSpec(
        key="churn",
        label="Change Hotspots",
        description=(
            "Ranks files by commit frequency and contributor spread to surface "
            "where churn concentrates."
        ),
        stage="churn",
    ),
    EngineSpec(
        key="security",
        label="Security",
        description=(
            "Finds unauthenticated routes, hardcoded secrets, SQL and command "
            "injection, path traversal, SSRF, XXE, weak crypto and unsafe "
            "deserialization."
        ),
        stage="rules",
        score_category="security",
    ),
    EngineSpec(
        key="maintainability",
        label="Maintainability",
        description=(
            "Flags high cyclomatic complexity, oversized functions and deep "
            "directory nesting."
        ),
        stage="maintainability",
        score_category="maintainability",
    ),
    EngineSpec(
        key="reliability",
        label="Reliability",
        description=(
            "Looks for patterns that tend to fail at runtime rather than at "
            "build time."
        ),
        stage="reliability",
        score_category="reliability",
    ),
    EngineSpec(
        key="devops",
        label="DevOps",
        description=(
            "Checks Dockerfile, env-file and CI configuration for common "
            "packaging and pipeline problems."
        ),
        stage="devops",
        score_category="devops",
    ),
    EngineSpec(
        key="dead_code",
        label="Dead Code",
        description=(
            "Finds declarations that nothing references, so they can be removed."
        ),
        stage="dead_code",
    ),
    EngineSpec(
        key="error_detection",
        label="Error Handling",
        description=("Finds swallowed, untyped and mis-handled error paths."),
        stage="errors",
    ),
    EngineSpec(
        key="performance",
        label="Performance",
        description=("Derives per-endpoint throughput metrics and flags hot paths."),
        stage="perf",
        score_category="performance",
    ),
    EngineSpec(
        key="simulation",
        label="Load Simulation",
        description=(
            "Models production load to classify the system as stable, degraded "
            "or failing."
        ),
        stage="simulation",
    ),
)

ENGINE_SPECS_BY_KEY: dict[str, EngineSpec] = {s.key: s for s in ENGINE_SPECS}

#: Every engine the pipeline tracks, seeded to `pending` when a job starts.
ALL_ENGINES: set[str] = set(ENGINE_SPECS_BY_KEY)

#: Engines that feed a scoring category, in catalogue order.
SCORED_ENGINE_KEYS: tuple[str, ...] = tuple(
    s.key for s in ENGINE_SPECS if s.score_category is not None
)


def stage_to_engine_keys() -> dict[str, list[str]]:
    """Map pipeline stage -> engine keys, for the per-stage loop."""
    mapping: dict[str, list[str]] = {}
    for spec in ENGINE_SPECS:
        mapping.setdefault(spec.stage, []).append(spec.key)
    return mapping
