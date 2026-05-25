from apps.workspaces.constants import PLAN_LIMITS, WorkspacePlan, WorkspaceRole


class TestWorkspaceRole:
    def test_enum_values(self):
        assert WorkspaceRole.OWNER == "owner"
        assert WorkspaceRole.ADMIN == "admin"
        assert WorkspaceRole.MEMBER == "member"
        assert WorkspaceRole.VIEWER == "viewer"

    def test_at_least_admin_returns_owner_and_admin(self):
        assert WorkspaceRole.at_least_admin() == ["owner", "admin"]

    def test_at_least_member_returns_owner_admin_member(self):
        assert WorkspaceRole.at_least_member() == ["owner", "admin", "member"]

    def test_all_roles_returns_all(self):
        assert WorkspaceRole.all_roles() == ["owner", "admin", "member", "viewer"]


class TestWorkspacePlan:
    def test_enum_values(self):
        assert WorkspacePlan.FREE == "free"
        assert WorkspacePlan.PRO == "pro"
        assert WorkspacePlan.TEAM == "team"
        assert WorkspacePlan.ENTERPRISE == "enterprise"


class TestPlanLimits:
    def test_free_plan_limits(self):
        limits = PLAN_LIMITS[WorkspacePlan.FREE]
        assert limits["max_members"] == 3
        assert limits["max_repos"] == 2
        assert limits["ai_queries_per_month"] == 50
        assert limits["analysis_per_month"] == 10

    def test_pro_plan_limits(self):
        limits = PLAN_LIMITS[WorkspacePlan.PRO]
        assert limits["max_members"] == 10
        assert limits["max_repos"] == 10
        assert limits["ai_queries_per_month"] == 500
        assert limits["analysis_per_month"] == 100

    def test_team_plan_limits(self):
        limits = PLAN_LIMITS[WorkspacePlan.TEAM]
        assert limits["max_members"] == 50
        assert limits["max_repos"] == 50
        assert limits["ai_queries_per_month"] == 5000
        assert limits["analysis_per_month"] == 1000

    def test_enterprise_plan_unlimited(self):
        limits = PLAN_LIMITS[WorkspacePlan.ENTERPRISE]
        assert limits["max_members"] == -1
        assert limits["max_repos"] == -1
        assert limits["ai_queries_per_month"] == -1
        assert limits["analysis_per_month"] == -1
