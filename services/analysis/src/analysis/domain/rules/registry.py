from fnmatch import fnmatch

from app.domain.rules.base import BaseRule


class RuleRegistry:
    """Discovers, registers, and filters analysis rules."""

    def __init__(self) -> None:
        self._rules: dict[str, BaseRule] = {}

    def register(self, rule: BaseRule) -> None:
        if not rule.rule_id:
            msg = f"Rule {rule.__class__.__name__} has empty rule_id"
            raise ValueError(msg)
        if rule.rule_id in self._rules:
            msg = f"Rule {rule.rule_id} is already registered"
            raise ValueError(msg)
        self._rules[rule.rule_id] = rule

    def register_many(self, rules: list[BaseRule]) -> None:
        for rule in rules:
            self.register(rule)

    def get(self, rule_id: str) -> BaseRule | None:
        return self._rules.get(rule_id)

    def get_all(self) -> list[BaseRule]:
        return list(self._rules.values())

    def filter_for_file(self, file_path: str, language: str) -> list[BaseRule]:
        applicable: list[BaseRule] = []
        for rule in self._rules.values():
            if rule.languages and language not in rule.languages:
                continue
            if rule.file_patterns == ["*"]:
                applicable.append(rule)
            else:
                for pattern in rule.file_patterns:
                    if fnmatch(file_path, pattern):
                        applicable.append(rule)
                        break
        return applicable

    def count(self) -> int:
        return len(self._rules)

    def clear(self) -> None:
        self._rules.clear()


def create_default_registry() -> RuleRegistry:
    """Create a registry with all built-in rules loaded."""
    from app.domain.rules.devops import (
        DevopsCIConfigRule,
        DevopsDockerfileRule,
        DevopsEnvFileRule,
    )
    from app.domain.rules.quality import (
        QualityHighComplexityRule,
        QualityLongFunctionRule,
    )
    from app.domain.rules.security import (
        SecurityCommandInjectionRule,
        SecurityCORSMisconfigRule,
        SecurityCSRFRule,
        SecurityDeserializationRule,
        SecurityHardcodedSecretRule,
        SecurityJWTRule,
        SecurityMissingAuthzRule,
        SecurityNoAuthRule,
        SecurityPathTraversalRule,
        SecuritySQLInjectionRule,
        SecuritySSRFRule,
        SecurityWeakCryptoRule,
        SecurityXSSRule,
        SecurityXXERule,
    )
    from app.domain.rules.structure import StructureDeepNestingRule

    registry = RuleRegistry()
    registry.register_many(
        [
            # Quality / structure
            QualityHighComplexityRule(),
            QualityLongFunctionRule(),
            StructureDeepNestingRule(),
            # Security (13 rules)
            SecurityNoAuthRule(),
            SecurityHardcodedSecretRule(),
            SecuritySQLInjectionRule(),
            SecurityCommandInjectionRule(),
            SecurityPathTraversalRule(),
            SecuritySSRFRule(),
            SecurityXXERule(),
            SecurityWeakCryptoRule(),
            SecurityJWTRule(),
            SecurityDeserializationRule(),
            SecurityMissingAuthzRule(),
            SecurityCSRFRule(),
            SecurityCORSMisconfigRule(),
            SecurityXSSRule(),
            # DevOps stubs
            DevopsDockerfileRule(),
            DevopsEnvFileRule(),
            DevopsCIConfigRule(),
        ]
    )
    return registry
