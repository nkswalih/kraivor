"""
Domain constants for the workspaces app.

Kept in a separate module so they can be imported by models, serializers,
permissions, and tests without circular import risk.
"""

from django.db import models


class WorkspaceRole(models.TextChoices):
    """
    Role hierarchy — higher roles subsume lower roles' permissions.

    OWNER   — full control, can delete workspace, cannot be removed
    ADMIN   — manage members, all content operations
    MEMBER  — create content, trigger analyses, use AI
    VIEWER  — read-only: view results, reports, notes
    """

    OWNER = "owner", "Owner"
    ADMIN = "admin", "Admin"
    MEMBER = "member", "Member"
    VIEWER = "viewer", "Viewer"

    @classmethod
    def at_least_admin(cls) -> list[str]:
        return [cls.OWNER, cls.ADMIN]

    @classmethod
    def at_least_member(cls) -> list[str]:
        return [cls.OWNER, cls.ADMIN, cls.MEMBER]

    @classmethod
    def all_roles(cls) -> list[str]:
        return [cls.OWNER, cls.ADMIN, cls.MEMBER, cls.VIEWER]


class WorkspacePlan(models.TextChoices):
    FREE = "free", "Free"
    PRO = "pro", "Pro"
    TEAM = "team", "Team"
    ENTERPRISE = "enterprise", "Enterprise"


# Plan-based feature limits — enforced in services, not models
PLAN_LIMITS = {
    WorkspacePlan.FREE: {
        "max_members": 3,
        "max_repos": 2,
        "ai_queries_per_month": 50,
        "analysis_per_month": 10,
    },
    WorkspacePlan.PRO: {
        "max_members": 10,
        "max_repos": 10,
        "ai_queries_per_month": 500,
        "analysis_per_month": 100,
    },
    WorkspacePlan.TEAM: {
        "max_members": 50,
        "max_repos": 50,
        "ai_queries_per_month": 5000,
        "analysis_per_month": 1000,
    },
    WorkspacePlan.ENTERPRISE: {
        "max_members": -1,  # unlimited
        "max_repos": -1,
        "ai_queries_per_month": -1,
        "analysis_per_month": -1,
    },
}