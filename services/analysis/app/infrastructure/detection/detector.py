import re
from pathlib import Path

from app.core.logging import get_logger
from app.infrastructure.detection.config_reader import (
    detect_ci_platform,
    read_cargo_toml,
    read_csproj,
    read_gemfile,
    read_go_mod,
    read_json,
    read_pom_xml,
    read_requirements_txt,
    read_toml,
)
from app.infrastructure.detection.models import DetectedTechnology, DetectionResult
from app.infrastructure.detection.signatures import (
    ALL_CSHARP_SIGNATURES,
    ALL_GO_SIGNATURES,
    ALL_JAVA_SIGNATURES,
    ALL_PACKAGE_JSON_SIGNATURES,
    ALL_PYTHON_SIGNATURES,
    INFRA_SIGNALS,
)

logger = get_logger(__name__)


class FrameworkDetector:
    """Detects frameworks, tools, databases, and infrastructure
    from a cloned repository's configuration files and file tree.

    Scans well-known config file locations, parses their contents,
    and matches dependencies against known technology signatures.
    """

    CONFIG_PATTERNS = [
        "package.json",
        "pyproject.toml",
        "requirements.txt",
        "requirements/*.txt",
        "setup.py",
        "setup.cfg",
        "go.mod",
        "go.sum",
        "Cargo.toml",
        "Gemfile",
        "pubspec.yaml",
        "composer.json",
    ]

    INFRA_FILES = [
        "Dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
        "nginx.conf",
        "nginx/nginx.conf",
    ]

    TERRAFORM_PATTERN = ".tf"

    K8S_EXTENSIONS = {".yaml", ".yml"}

    DATABASE_CONFIG_PATTERNS = [
        "database.yml",
        "database.php",
        "databases.php",
        ".env",
        ".env.example",
        "config/database.php",
        "config/database.yml",
    ]

    def __init__(self) -> None:
        self._parsed_configs: dict[str, dict] = {}

    async def detect(self, repo_path: str) -> DetectionResult:
        result = DetectionResult()

        try:
            self._collect_config_files(repo_path)
            self._detect_from_package_json(result)
            self._detect_from_pyproject_toml(result)
            self._detect_from_requirements_txt(result)
            self._detect_from_go_mod(result)
            self._detect_from_cargo_toml(result)
            self._detect_from_gemfile(result)
            self._detect_from_csproj_files(repo_path, result)
            self._detect_from_pom_xml_files(repo_path, result)
            self._detect_infra_files(repo_path, result)
            self._detect_ci(repo_path, result)
        except Exception:
            logger.warning("framework_detection_error", repo_path=repo_path, exc_info=True)

        result.frameworks = self._deduplicate(result.frameworks)
        result.databases = self._deduplicate(result.databases)
        result.tools = self._deduplicate(result.tools)
        result.infra = self._deduplicate(result.infra)

        return result

    def _collect_config_files(self, repo_path: str) -> None:
        """Find and parse well-known config files."""
        root = Path(repo_path)

        pkg_json = root / "package.json"
        if pkg_json.exists():
            data = read_json(str(pkg_json))
            if data:
                self._parsed_configs["package.json"] = data

        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            data = read_toml(str(pyproject))
            if data:
                self._parsed_configs["pyproject.toml"] = data

        req_txt = root / "requirements.txt"
        if req_txt.exists():
            data = read_requirements_txt(str(req_txt))
            if data:
                self._parsed_configs["requirements.txt"] = data

        go_mod = root / "go.mod"
        if go_mod.exists():
            data = read_go_mod(str(go_mod))
            if data:
                self._parsed_configs["go.mod"] = data

        cargo = root / "Cargo.toml"
        if cargo.exists():
            data = read_cargo_toml(str(cargo))
            if data:
                self._parsed_configs["Cargo.toml"] = data

        gemfile = root / "Gemfile"
        if gemfile.exists():
            data = read_gemfile(str(gemfile))
            if data:
                self._parsed_configs["Gemfile"] = data

    def _detect_from_package_json(self, result: DetectionResult) -> None:
        data = self._parsed_configs.get("package.json")
        if not data:
            return

        deps = {
            **{k.lower(): v for k, v in data.get("dependencies", {}).items()},
            **{k.lower(): v for k, v in data.get("devDependencies", {}).items()},
        }

        for dep_name, dep_version in deps.items():
            for sig_name, tech in ALL_PACKAGE_JSON_SIGNATURES.items():
                if sig_name in dep_name or dep_name == sig_name:
                    resolved = self._clone_with_version(tech, dep_version)
                    self._categorize(result, resolved)

        result.config_files["package.json"] = {
            "name": data.get("name", ""),
            "version": data.get("version", ""),
        }

    def _detect_from_pyproject_toml(self, result: DetectionResult) -> None:
        data = self._parsed_configs.get("pyproject.toml")
        if not data:
            return

        deps: list[str] = []

        project = data.get("project", {}) if isinstance(data, dict) else {}
        if isinstance(project, dict):
            deps.extend(project.get("dependencies", []) or [])
            deps.extend(project.get("optional-dependencies", {}).get("dev", []) or [])

        tool_poetry = None
        if isinstance(data, dict):
            tool = data.get("tool", {}) if isinstance(data, dict) else {}
            if isinstance(tool, dict):
                tool_poetry = tool.get("poetry", {})

        if tool_poetry and isinstance(tool_poetry, dict):
            for group in ("dependencies", "dev-dependencies"):
                group_deps = tool_poetry.get(group, {})
                if isinstance(group_deps, dict):
                    deps.extend(group_deps.keys())

        extracted = self._extract_dep_names(deps)
        for dep_name in extracted:
            for sig_name, tech in ALL_PYTHON_SIGNATURES.items():
                if sig_name in dep_name or dep_name == sig_name:
                    self._categorize(result, tech)

    def _detect_from_requirements_txt(self, result: DetectionResult) -> None:
        deps = self._parsed_configs.get("requirements.txt")
        if not deps:
            return

        for dep_name in deps:
            for sig_name, tech in ALL_PYTHON_SIGNATURES.items():
                if sig_name in dep_name or dep_name == sig_name:
                    self._categorize(result, tech)

    def _detect_from_go_mod(self, result: DetectionResult) -> None:
        deps = self._parsed_configs.get("go.mod")
        if not deps:
            return

        for dep_path in deps:
            for sig_name, tech in ALL_GO_SIGNATURES.items():
                if sig_name in dep_path or dep_path.startswith(sig_name):
                    version = deps[dep_path]
                    resolved = self._clone_with_version(tech, version)
                    self._categorize(result, resolved)

    def _detect_from_cargo_toml(self, result: DetectionResult) -> None:
        deps = self._parsed_configs.get("Cargo.toml")
        if not deps:
            return

        for dep_name in deps:
            lower = dep_name.lower()
            if lower in ("actix-web", "actix_web"):
                result.frameworks.append(
                    DetectedTechnology(name="Actix", category="framework", detected_from="Cargo.toml")
                )
            elif lower in ("axum",):
                result.frameworks.append(
                    DetectedTechnology(name="Axum", category="framework", detected_from="Cargo.toml")
                )
            elif lower in ("rocket",):
                result.frameworks.append(
                    DetectedTechnology(name="Rocket", category="framework", detected_from="Cargo.toml")
                )
            elif lower == "tokio":
                result.tools.append(
                    DetectedTechnology(name="Tokio", category="tool", detected_from="Cargo.toml")
                )

    def _detect_from_gemfile(self, result: DetectionResult) -> None:
        deps = self._parsed_configs.get("Gemfile")
        if not deps:
            return

        for dep_name in deps:
            lower = dep_name.lower()
            if lower in ("rails", "rails"):
                result.frameworks.append(
                    DetectedTechnology(name="Ruby on Rails", category="framework", detected_from="Gemfile")
                )
            elif lower in ("sinatra",):
                result.frameworks.append(
                    DetectedTechnology(name="Sinatra", category="framework", detected_from="Gemfile")
                )

    def _detect_from_csproj_files(self, repo_path: str, result: DetectionResult) -> None:
        root = Path(repo_path)
        for csproj_file in root.rglob("*.csproj"):
            deps = read_csproj(str(csproj_file))
            if not deps:
                continue

            for dep_name, dep_version in deps.items():
                for sig_name, tech in ALL_CSHARP_SIGNATURES.items():
                    if sig_name in dep_name or dep_name == sig_name:
                        resolved = self._clone_with_version(tech, dep_version)
                        self._categorize(result, resolved)

    def _detect_from_pom_xml_files(self, repo_path: str, result: DetectionResult) -> None:
        root = Path(repo_path)
        for pom_file in root.rglob("pom.xml"):
            deps = read_pom_xml(str(pom_file))
            if not deps:
                continue

            for dep_key, dep_version in deps.items():
                parts = dep_key.split(":", 1)
                group_id = parts[0] if parts else dep_key
                artifact_id = parts[1] if len(parts) > 1 else dep_key

                for sig_name, tech in ALL_JAVA_SIGNATURES.items():
                    if sig_name in dep_key or dep_key.startswith(sig_name) or sig_name == artifact_id or sig_name.endswith("." + artifact_id) or sig_name in group_id:
                        resolved = self._clone_with_version(tech, dep_version)
                        self._categorize(result, resolved)

    def _detect_infra_files(self, repo_path: str, result: DetectionResult) -> None:
        root = Path(repo_path)

        if (root / "Dockerfile").exists():
            result.infra.append(self._clone_with_version(INFRA_SIGNALS["dockerfile"]))
        for compose_name in ("docker-compose.yml", "docker-compose.yaml"):
            if (root / compose_name).exists():
                result.infra.append(self._clone_with_version(INFRA_SIGNALS["docker_compose"]))

        has_k8s = False
        for k8s_dir in ("k8s", "kubernetes", "deploy", "manifests"):
            dir_path = root / k8s_dir
            if dir_path.is_dir():
                has_k8s = True
                break
        if not has_k8s:
            for f in root.iterdir():
                if f.suffix in self.K8S_EXTENSIONS and f.name not in (
                    "docker-compose.yml", "docker-compose.yaml",
                ):
                    content = self._safe_read(f)
                    if content and ("apiVersion:" in content and "kind:" in content):
                        has_k8s = True
                        break
        if has_k8s:
            result.infra.append(
                DetectedTechnology(name="Kubernetes", category="infra", detected_from="manifests", confidence=0.8)
            )

        for tf_file in root.rglob("*.tf"):
            if tf_file.is_file():
                result.infra.append(
                    DetectedTechnology(name="Terraform", category="infra", detected_from="*.tf", confidence=0.9)
                )
                break

        if (root / "nginx.conf").exists() or (root / "nginx/nginx.conf").exists():
            result.infra.append(
                DetectedTechnology(name="Nginx", category="infra", detected_from="nginx.conf", confidence=0.9)
            )

        self._detect_databases_from_env(repo_path, result)

    def _detect_ci(self, repo_path: str, result: DetectionResult) -> None:
        ci_name = detect_ci_platform(repo_path)
        if ci_name:
            result.infra.append(
                DetectedTechnology(name=ci_name, category="infra", detected_from="CI config")
            )

    def _detect_databases_from_env(self, repo_path: str, result: DetectionResult) -> None:
        for env_file in (".env", ".env.example"):
            path = Path(repo_path) / env_file
            if not path.exists():
                continue
            content = self._safe_read(path)
            if not content:
                continue

            lower = content.lower()
            db_signals: list[tuple[tuple[str, ...], DetectedTechnology]] = [
                (("postgresql", "postgres", "psql", "pg"),
                    DetectedTechnology(name="PostgreSQL", category="database", detected_from=".env", confidence=0.7)),
                (("mongodb", "mongo"),
                    DetectedTechnology(name="MongoDB", category="database", detected_from=".env", confidence=0.7)),
                (("redis://",),
                    DetectedTechnology(name="Redis", category="database", detected_from=".env", confidence=0.7)),
                (("kafka://",),
                    DetectedTechnology(name="Kafka", category="infra", detected_from=".env", confidence=0.6)),
                (("rabbitmq://", "amqp://"),
                    DetectedTechnology(name="RabbitMQ", category="infra", detected_from=".env", confidence=0.6)),
            ]

            for keywords, tech in db_signals:
                if any(kw in lower for kw in keywords) and not any(t.name == tech.name for t in result.databases + result.infra):
                    if tech.category == "database":
                        result.databases.append(tech)
                    else:
                        result.infra.append(tech)

    @staticmethod
    def _extract_dep_names(deps: list[str]) -> list[str]:
        names: list[str] = []
        for dep in deps:
            if not dep:
                continue
            cleaned = dep.strip()
            match = re.match(r"^([a-zA-Z0-9_.-]+)", cleaned)
            if match:
                names.append(match.group(1).lower().replace("-", "_").replace(".", "_"))
        return names

    @staticmethod
    def _categorize(result: DetectionResult, tech: DetectedTechnology) -> None:
        if tech.category == "database":
            result.databases.append(tech)
        elif tech.category == "infra":
            result.infra.append(tech)
        elif tech.category == "tool":
            result.tools.append(tech)
        elif tech.category == "framework":
            result.frameworks.append(tech)
        else:
            result.frameworks.append(tech)

    @staticmethod
    def _clone_with_version(tech: DetectedTechnology, version: str | None = None) -> DetectedTechnology:
        return DetectedTechnology(
            name=tech.name,
            category=tech.category,
            version=version,
            confidence=tech.confidence,
            detected_from=tech.detected_from,
        )

    @staticmethod
    def _deduplicate(items: list[DetectedTechnology]) -> list[DetectedTechnology]:
        seen: set[str] = set()
        result: list[DetectedTechnology] = []
        for item in items:
            if item.name not in seen:
                seen.add(item.name)
                result.append(item)
        return result

    @staticmethod
    def _safe_read(path: Path) -> str | None:
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except (OSError, PermissionError):
            return None
