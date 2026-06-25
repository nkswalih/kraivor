from typing import Any

import pytest

from app.domain.rules.devops import DevopsCIConfigRule, DevopsDockerfileRule, DevopsEnvFileRule
from app.domain.rules.quality import QualityHighComplexityRule, QualityLongFunctionRule
from app.domain.rules.registry import RuleRegistry, create_default_registry
from app.domain.rules.security import SecurityHardcodedSecretRule, SecurityNoAuthRule
from app.domain.rules.structure import StructureDeepNestingRule


class TestRuleRegistry:
    def test_register_and_get(self) -> None:
        registry = RuleRegistry()
        rule = QualityHighComplexityRule()
        registry.register(rule)
        assert registry.get("QUAL-COMPLEX") is rule
        assert registry.count() == 1

    def test_register_duplicate_raises(self) -> None:
        registry = RuleRegistry()
        registry.register(QualityHighComplexityRule())
        with pytest.raises(ValueError, match="already registered"):
            registry.register(QualityHighComplexityRule())

    def test_register_empty_rule_id_raises(self) -> None:
        registry = RuleRegistry()
        rule = QualityHighComplexityRule()
        rule.rule_id = ""
        with pytest.raises(ValueError, match="empty rule_id"):
            registry.register(rule)

    def test_register_many(self) -> None:
        registry = RuleRegistry()
        registry.register_many([QualityHighComplexityRule(), QualityLongFunctionRule()])
        assert registry.count() == 2

    def test_get_all(self) -> None:
        registry = RuleRegistry()
        registry.register(QualityHighComplexityRule())
        registry.register(SecurityNoAuthRule())
        assert len(registry.get_all()) == 2

    def test_filter_for_file_all_patterns(self) -> None:
        registry = RuleRegistry()
        rule = QualityHighComplexityRule()
        registry.register(rule)
        result = registry.filter_for_file("some/file.py", "python")
        assert rule in result

    def test_filter_for_file_specific_pattern(self) -> None:
        registry = RuleRegistry()
        rule = SecurityNoAuthRule()
        registry.register(rule)
        assert registry.filter_for_file("routes/api.py", "python")
        assert not registry.filter_for_file("some/util.py", "python")

    def test_filter_for_file_language_filter(self) -> None:
        registry = RuleRegistry()
        rule = QualityHighComplexityRule()
        rule.languages = ["python"]
        registry.register(rule)
        assert registry.filter_for_file("file.py", "python")
        assert not registry.filter_for_file("file.js", "javascript")

    def test_create_default_registry(self) -> None:
        registry = create_default_registry()
        assert registry.count() == 8

    def test_clear(self) -> None:
        registry = create_default_registry()
        registry.clear()
        assert registry.count() == 0


class TestQualityHighComplexityRule:
    @pytest.mark.parametrize("func_data,expected_violations", [
        ({"name": "low", "line_start": 1, "line_end": 2, "snippet": "def low(): pass", "complexity": 5}, 0),
        ({"name": "high", "line_start": 1, "line_end": 20, "snippet": "def high():\n" + "\n".join([f"    if a{i}: pass" for i in range(16)]), "complexity": 16}, 1),
    ])
    async def test_complexity_threshold(self, func_data: dict[str, Any], expected_violations: int) -> None:
        rule = QualityHighComplexityRule()
        result = await rule.analyze("test.py", "", {"functions": [func_data]})
        assert len(result) == expected_violations

    async def test_high_complexity_severity(self) -> None:
        rule = QualityHighComplexityRule()
        result = await rule.analyze("test.py", "", {"functions": [{
            "name": "very_high", "line_start": 1, "line_end": 50,
            "snippet": "def f():\n" + "\n".join([f"    if a{i}: pass" for i in range(35)]),
            "complexity": 35,
        }]})
        assert len(result) == 1
        assert result[0].severity == "high"

    async def test_no_violations_for_simple_code(self) -> None:
        rule = QualityHighComplexityRule()
        result = await rule.analyze("test.py", "", {"functions": []})
        assert len(result) == 0


class TestQualityLongFunctionRule:
    async def test_short_function_no_violation(self) -> None:
        rule = QualityLongFunctionRule()
        result = await rule.analyze("test.py", "", {"functions": [{"name": "short", "line_start": 1, "line_end": 10}]})
        assert len(result) == 0

    async def test_long_function_violation(self) -> None:
        rule = QualityLongFunctionRule()
        result = await rule.analyze("test.py", "", {"functions": [{"name": "long", "line_start": 1, "line_end": 60}]})
        assert len(result) == 1
        assert "long" in result[0].title

    async def test_very_long_function_medium_severity(self) -> None:
        rule = QualityLongFunctionRule()
        result = await rule.analyze("test.py", "", {"functions": [{"name": "very_long", "line_start": 1, "line_end": 150}]})
        assert len(result) == 1
        assert result[0].severity == "medium"


class TestSecurityNoAuthRule:
    async def test_missing_auth_on_get(self) -> None:
        rule = SecurityNoAuthRule()
        routes = [{"path": "/api/test", "method": "GET", "has_auth": False, "line_start": 1}]
        result = await rule.analyze("routes.py", "", {"routes": routes})
        assert len(result) == 1
        assert result[0].severity == "high"

    async def test_missing_auth_on_post_is_critical(self) -> None:
        rule = SecurityNoAuthRule()
        routes = [{"path": "/api/data", "method": "POST", "has_auth": False, "line_start": 1}]
        result = await rule.analyze("routes.py", "", {"routes": routes})
        assert len(result) == 1
        assert result[0].severity == "critical"

    async def test_authenticated_route_no_violation(self) -> None:
        rule = SecurityNoAuthRule()
        routes = [{"path": "/api/secure", "method": "GET", "has_auth": True, "line_start": 1}]
        result = await rule.analyze("routes.py", "", {"routes": routes})
        assert len(result) == 0

    async def test_no_routes_no_violation(self) -> None:
        rule = SecurityNoAuthRule()
        result = await rule.analyze("routes.py", "", {"routes": []})
        assert len(result) == 0

    async def test_file_pattern_filter(self) -> None:
        import fnmatch
        rule = SecurityNoAuthRule()
        assert fnmatch.fnmatch("routes.py", rule.file_patterns[0])
        assert not fnmatch.fnmatch("models.py", rule.file_patterns[0])


class TestSecurityHardcodedSecretRule:
    async def test_detects_api_key(self) -> None:
        rule = SecurityHardcodedSecretRule()
        content = 'API_KEY = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8g9h0"'
        result = await rule.analyze("config.py", content, {})
        assert len(result) == 1
        assert "Hardcoded secret" in result[0].title

    async def test_detects_password(self) -> None:
        rule = SecurityHardcodedSecretRule()
        content = 'password = "supersecretpassword123"'
        result = await rule.analyze("config.py", content, {})
        assert len(result) >= 1

    async def test_skips_low_entropy_values(self) -> None:
        rule = SecurityHardcodedSecretRule()
        content = 'NAME = "hello"'
        result = await rule.analyze("config.py", content, {})
        assert len(result) == 0

    async def test_empty_content_no_violation(self) -> None:
        rule = SecurityHardcodedSecretRule()
        result = await rule.analyze("test.py", "", {})
        assert len(result) == 0

    async def test_multiple_secrets(self) -> None:
        rule = SecurityHardcodedSecretRule()
        content = '\n'.join([
            'API_KEY = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8g9h0"',
            'SECRET = "x9y8z7w6v5u4t3s2r1q0p9o8n7m6l5k4j3i2h1g0f"',
        ])
        result = await rule.analyze("config.py", content, {})
        assert len(result) == 2


class TestStructureDeepNestingRule:
    async def test_shallow_nesting_no_violation(self) -> None:
        rule = StructureDeepNestingRule()
        result = await rule.analyze("src/app.py", "", {})
        assert len(result) == 0

    async def test_deep_nesting_violation(self) -> None:
        rule = StructureDeepNestingRule()
        result = await rule.analyze("src/level1/level2/level3/level4/level5/file.py", "", {})
        assert len(result) == 1
        assert "Deep directory nesting" in result[0].title

    async def test_very_deep_nesting_medium_severity(self) -> None:
        rule = StructureDeepNestingRule()
        result = await rule.analyze("a/b/c/d/e/f/g/h/file.py", "", {})
        assert len(result) == 1
        assert result[0].severity == "medium"


class TestDevopsRules:
    async def test_dockerfile_rule_returns_empty(self) -> None:
        rule = DevopsDockerfileRule()
        result = await rule.analyze("Dockerfile", "", {})
        assert result == []

    async def test_env_file_rule_returns_empty(self) -> None:
        rule = DevopsEnvFileRule()
        result = await rule.analyze(".env", "", {})
        assert result == []

    async def test_ci_config_rule_returns_empty(self) -> None:
        rule = DevopsCIConfigRule()
        result = await rule.analyze(".github/workflows/ci.yml", "", {})
        assert result == []
