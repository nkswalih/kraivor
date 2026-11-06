from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class EnterpriseGuideResponse(BaseModel):
    id: UUID
    job_id: UUID

    # ── Legacy fields ────────────────────────────────────────────
    executive_summary: str | None = None
    critical_issues: list[object] | None = None
    high_issues: list[object] | None = None
    medium_issues: list[object] | None = None
    architecture_review: dict[str, object] | None = None
    capacity_analysis: dict[str, object] | None = None
    migration_path: list[object] | None = None
    ai_executive_summary: str | None = None
    # Set only when `ai_executive_summary` is None *and* something failed. This is
    # the difference between "no summary was produced" and "no summary was
    # produced, here is why" -- a distinction that used to be invisible, because
    # both arrived as null.
    #
    # `code`, `message` and `suggested_action` come from the AI service's
    # `ClassifiedError`. There is deliberately no `provider`, `model` or
    # `technical_message` here either: the provider's verbatim response body
    # contains, on an auth failure, the rejected key.
    ai_summary_error: dict[str, object] | None = None

    # ── New structured fields ────────────────────────────────────
    repository_health: dict[str, object] | None = None
    engineering_scorecard: dict[str, object] | None = None
    business_risk: dict[str, object] | None = None
    scalability_review: dict[str, object] | None = None
    technical_debt: dict[str, object] | None = None
    issue_clusters: list[object] | None = None
    hotspots: list[object] | None = None
    service_health: dict[str, object] | None = None
    quick_wins: list[object] | None = None
    sprint_roadmap: dict[str, object] | None = None
    deployment_readiness: dict[str, object] | None = None
    release_recommendation: dict[str, object] | None = None
    ownership: list[object] | None = None
    estimated_effort: dict[str, object] | None = None
    ai_recommendations: list[object] | None = None
    raw_findings: list[object] | None = None

    generated_at: datetime | None = None
