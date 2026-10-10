from app.core.constants import Category, Severity
from app.domain.rules.base import BaseRule, RuleViolation


class DevopsDockerfileRule(BaseRule):
    """Checks that the project has a Dockerfile."""

    rule_id: str = "DEVOPS-DOCKER"
    category: Category = Category.DEVOPS
    severity: Severity = Severity.MEDIUM
    description: str = "Checks for presence of containerization config"
    languages: list[str] = []
    file_patterns: list[str] = ["*"]
    _checked: bool = False

    async def analyze(
        self, file_path: str, content: str, ast_data: dict[str, object]
    ) -> list[RuleViolation]:
        # This rule is project-level, not file-level.
        # It's triggered once via special handling in the rule runner.
        return []


class DevopsEnvFileRule(BaseRule):
    """Checks for .env.example or similar environment template."""

    rule_id: str = "DEVOPS-ENV"
    category: Category = Category.DEVOPS
    severity: Severity = Severity.LOW
    description: str = "Checks for environment configuration template"
    languages: list[str] = []
    file_patterns: list[str] = ["*"]

    async def analyze(
        self, file_path: str, content: str, ast_data: dict[str, object]
    ) -> list[RuleViolation]:
        return []


class DevopsCIConfigRule(BaseRule):
    """Checks for CI/CD configuration files."""

    rule_id: str = "DEVOPS-CI"
    category: Category = Category.DEVOPS
    severity: Severity = Severity.MEDIUM
    description: str = "Checks for CI/CD pipeline configuration"
    languages: list[str] = []
    file_patterns: list[str] = ["*"]

    _CI_FILE_NAMES: set[str] = {
        ".github/workflows",
        ".gitlab-ci.yml",
        "Jenkinsfile",
        ".circleci/config.yml",
        ".drone.yml",
        ".woodpecker.yml",
        "azure-pipelines.yml",
        "bitbucket-pipelines.yml",
    }

    async def analyze(
        self, file_path: str, content: str, ast_data: dict[str, object]
    ) -> list[RuleViolation]:
        return []
