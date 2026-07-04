from dataclasses import dataclass, field


@dataclass(kw_only=True)
class DetectedTechnology:
    name: str
    category: str = ""
    version: str | None = None
    confidence: float = 1.0
    detected_from: str = ""

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DetectedTechnology):
            return NotImplemented
        return self.name == other.name


@dataclass(kw_only=True)
class DetectionResult:
    frameworks: list[DetectedTechnology] = field(default_factory=list)
    databases: list[DetectedTechnology] = field(default_factory=list)
    tools: list[DetectedTechnology] = field(default_factory=list)
    infra: list[DetectedTechnology] = field(default_factory=list)
    languages: list[DetectedTechnology] = field(default_factory=list)
    config_files: dict[str, dict[str, str]] = field(default_factory=dict)

    def all_technologies(self) -> list[DetectedTechnology]:
        return (
            self.frameworks + self.databases + self.tools + self.infra + self.languages
        )

    def has_framework(self, name: str) -> bool:
        return any(f.name == name for f in self.frameworks)

    def to_dict(self) -> dict[str, object]:
        def _ser(
            items: list[DetectedTechnology],
        ) -> list[dict[str, str | float | None]]:
            return [
                {
                    "name": t.name,
                    "category": t.category,
                    "version": t.version,
                    "confidence": t.confidence,
                    "detected_from": t.detected_from,
                }
                for t in items
            ]

        return {
            "frameworks": _ser(self.frameworks),
            "databases": _ser(self.databases),
            "tools": _ser(self.tools),
            "infra": _ser(self.infra),
            "languages": _ser(self.languages),
        }
