import os
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
        # A list per key, not a single dict per key: a monorepo has one
        # `package.json` and one `pyproject.toml` per package, and keeping only
        # whichever file happened to be read last is how `services/analysis`
        # could declare `fastapi` and still report no frameworks.
        self._parsed_configs: dict[str, list[dict[str, object]]] = {}
        # Container manifests seen anywhere in the same walk, so a
        # `deploy/docker-compose.yml` counts as one.
        self._infra_files: set[str] = set()

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
            logger.warning(
                "framework_detection_error", repo_path=repo_path, exc_info=True
            )

        result.frameworks = self._deduplicate(result.frameworks)
        result.databases = self._deduplicate(result.databases)
        result.tools = self._deduplicate(result.tools)
        result.infra = self._deduplicate(result.infra)

        return result

    # Filenames worth reading anywhere in the tree, not only at the root.
    #
    # Root-only collection was the reason framework detection returned an empty
    # list for every monorepo: this repository's own `pyproject.toml` at the
    # root is tool configuration with no `[project]` table and no dependencies,
    # while `services/analysis/pyproject.toml` carries `fastapi` and
    # `services/core/pyproject.toml` carries `django`, `djangorestframework`
    # and `celery`. `frontend/package.json` declares `react` and `next`. None of
    # it was read, so a run on this repository reported no frameworks at all.
    _CONFIG_FILENAMES: dict[str, str] = {
        "package.json": "package.json",
        "pyproject.toml": "pyproject.toml",
        "go.mod": "go.mod",
        "cargo.toml": "Cargo.toml",
        "gemfile": "Gemfile",
    }

    # Prefix/suffix pairs on the filename, plus directory-name prefixes, matched
    # against the filename only. The prefix is what keeps `README.txt`,
    # `CHANGELOG.txt` and `notes.txt` out of the requirements reader -- matching
    # a bare `.txt` suffix would have parsed every text file in the repository as
    # a dependency list -- while `requirements/base.txt` still gets in through
    # its directory.
    _CONFIG_REQ_PREFIX = "requirements"
    _CONFIG_REQ_SUFFIX = ".txt"
    _CONFIG_REQ_KEY = "requirements.txt"

    # Directories that are never source for a dependency manifest. Walking into
    # any of these would read a vendored copy of somebody else's project and
    # attribute its frameworks to this one.
    _CONFIG_SKIP_DIRS: set[str] = {
        ".git",
        ".hg",
        ".svn",
        "node_modules",
        "bower_components",
        ".venv",
        "venv",
        "env",
        ".tox",
        ".nox",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        "__pycache__",
        "vendor",
        "dist",
        "build",
        "target",
        ".next",
        ".nuxt",
        ".output",
        ".terraform",
        ".opencode",
        ".idea",
        ".vscode",
        "coverage",
        "htmlcov",
        "site-packages",
        "eggs",
        "*.egg-info",
    }

    # A walk that reaches every directory is unbounded on a large monorepo, and
    # the manifests it is looking for all live near the top. Both limits are
    # generous for a real project and cheap for a pathological one.
    _CONFIG_MAX_DEPTH = 6
    _CONFIG_MAX_FILES = 400

    def _collect_config_files(self, repo_path: str) -> None:
        """Find and parse dependency manifests anywhere in the tree.

        Bounded by depth and count rather than unlimited, and skipping the
        vendored directories listed in `_CONFIG_SKIP_DIRS`, so a repository
        containing a checkout of its own dependencies cannot report those as
        its frameworks.
        """
        root = Path(repo_path)
        if not root.exists():
            return

        found = 0
        for dirpath, dirnames, filenames in os.walk(root, topdown=True):
            rel = os.path.relpath(dirpath, root)
            depth = 0 if rel == "." else rel.count(os.sep) + 1
            if depth >= self._CONFIG_MAX_DEPTH:
                dirnames[:] = []
            else:
                dirnames[:] = [
                    d
                    for d in dirnames
                    if d not in self._CONFIG_SKIP_DIRS and not d.endswith(".egg-info")
                ]

            for filename in filenames:
                if found >= self._CONFIG_MAX_FILES:
                    return
                found += 1
                if filename in ("Dockerfile", "Containerfile") or filename.startswith(
                    "docker-compose."
                ):
                    self._infra_files.add(filename)
                self._read_config_file(Path(dirpath) / filename)

    def _read_config_file(self, path: Path) -> None:
        """Parse one manifest, storing it under its own key.

        Several manifests of the same kind may exist -- one per package in a
        monorepo -- so the store keeps a list per key and the `_detect_from_*`
        methods merge them, rather than each overwrite the last one read.
        """
        name = path.name
        lowered = name.lower()

        key: str | None = self._CONFIG_FILENAMES.get(lowered)
        if key is None and lowered.endswith(self._CONFIG_REQ_SUFFIX):
            parent = path.parent.name.lower()
            if (
                lowered.startswith(self._CONFIG_REQ_PREFIX)
                or parent.startswith(self._CONFIG_REQ_PREFIX)
            ):
                key = self._CONFIG_REQ_KEY

        if key is None:
            return

        data: object | None = None
        if key == "package.json":
            data = read_json(str(path))
        elif key == "pyproject.toml":
            data = read_toml(str(path))
        elif key == "requirements.txt":
            data = read_requirements_txt(str(path))
        elif key == "go.mod":
            data = read_go_mod(str(path))
        elif key == "Cargo.toml":
            data = read_cargo_toml(str(path))
        elif key == "Gemfile":
            data = read_gemfile(str(path))

        if isinstance(data, dict) and data:
            self._parsed_configs.setdefault(key, []).append(data)

    def _configs(self, key: str) -> list[dict[str, object]]:
        """Every parsed manifest under `key`, in the order they were read."""
        values = self._parsed_configs.get(key, [])
        return [v for v in values if isinstance(v, dict)]

    @staticmethod
    def _mapping(value: object) -> dict[str, object]:
        """`value` when it is a mapping, otherwise nothing.

        Manifests are hand-maintained files, so a `dependencies` key holding a
        string or a list is a real shape and would otherwise raise out of the
        whole detection pass.
        """
        if isinstance(value, dict):
            return value
        return {}

    @staticmethod
    def _string(value: object) -> str:
        """`value` when it is a string, otherwise empty.

        Manifest fields are hand-maintained; `"version": null` is a real shape
        and `config_files` is typed as strings.
        """
        return value if isinstance(value, str) else ""

    @staticmethod
    def _string_list(value: object) -> list[str]:
        """Strings only, from a field that is allowed to be a list or a scalar."""
        if isinstance(value, list):
            return [item for item in value if isinstance(item, str)]
        if isinstance(value, str):
            return [value]
        return []

    def _detect_from_package_json(self, result: DetectionResult) -> None:
        for data in self._configs("package.json"):
            deps: dict[str, object] = {}
            for field in ("dependencies", "devDependencies"):
                for name, version in self._mapping(data.get(field)).items():
                    deps[name.lower()] = version

            for dep_name, dep_version in deps.items():
                for sig_name, tech in ALL_PACKAGE_JSON_SIGNATURES.items():
                    if sig_name in dep_name or dep_name == sig_name:
                        resolved = self._clone_with_version(
                            tech,
                            dep_version if isinstance(dep_version, str) else None,
                        )
                        self._categorize(result, resolved)

            # Only the root manifest's identity is worth reporting; the rest
            # contribute their dependencies and nothing else.
            if "package.json" not in result.config_files:
                result.config_files["package.json"] = {
                    "name": self._string(data.get("name")),
                    "version": self._string(data.get("version")),
                }

    def _detect_from_pyproject_toml(self, result: DetectionResult) -> None:
        for data in self._configs("pyproject.toml"):
            deps: list[str] = []

            project = self._mapping(data.get("project"))
            if project:
                deps.extend(self._string_list(project.get("dependencies")))
                # Every optional group, not only `dev`. A monorepo routinely
                # puts its framework in `docs` or `test`, and reading one group
                # meant the answer depended on which group happened to exist.
                optional = self._mapping(project.get("optional-dependencies"))
                for group in optional.values():
                    deps.extend(self._string_list(group))

            # PEP 735 dependency groups, now the standard home for dev deps.
            for group in self._mapping(data.get("dependency-groups")).values():
                deps.extend(self._string_list(group))

            tool_poetry = self._mapping(
                self._mapping(data.get("tool")).get("poetry")
            )

            for group in ("dependencies", "dev-dependencies"):
                deps.extend(self._mapping(tool_poetry.get(group)).keys())
            # Poetry's per-group tables: `tool.poetry.group.test.dependencies`.
            for poetry_group in self._mapping(tool_poetry.get("group")).values():
                if isinstance(poetry_group, dict):
                    deps.extend(self._mapping(poetry_group.get("dependencies")).keys())

            extracted = self._extract_dep_names(deps)
            for dep_name in extracted:
                for sig_name, tech in ALL_PYTHON_SIGNATURES.items():
                    if sig_name in dep_name or dep_name == sig_name:
                        self._categorize(result, tech)

    def _detect_from_requirements_txt(self, result: DetectionResult) -> None:
        for deps in self._configs("requirements.txt"):
            for dep_name in deps:
                for sig_name, tech in ALL_PYTHON_SIGNATURES.items():
                    if sig_name in dep_name or dep_name == sig_name:
                        self._categorize(result, tech)

    def _detect_from_go_mod(self, result: DetectionResult) -> None:
        for deps in self._configs("go.mod"):
            for dep_path in deps:
                for sig_name, tech in ALL_GO_SIGNATURES.items():
                    if sig_name in dep_path or dep_path.startswith(sig_name):
                        version = deps[dep_path]
                        resolved = self._clone_with_version(tech, version)  # type: ignore[arg-type]
                        self._categorize(result, resolved)

    def _detect_from_cargo_toml(self, result: DetectionResult) -> None:
        for deps in self._configs("Cargo.toml"):
            for dep_name in deps:
                lower = dep_name.lower()
                if lower in ("actix-web", "actix_web"):
                    result.frameworks.append(
                        DetectedTechnology(
                            name="Actix",
                            category="framework",
                            detected_from="Cargo.toml",
                        )
                    )
                elif lower in ("axum",):
                    result.frameworks.append(
                        DetectedTechnology(
                            name="Axum", category="framework", detected_from="Cargo.toml"
                        )
                    )
                elif lower in ("rocket",):
                    result.frameworks.append(
                        DetectedTechnology(
                            name="Rocket",
                            category="framework",
                            detected_from="Cargo.toml",
                        )
                    )
                elif lower == "tokio":
                    result.tools.append(
                        DetectedTechnology(
                            name="Tokio", category="tool", detected_from="Cargo.toml"
                        )
                    )

    def _detect_from_gemfile(self, result: DetectionResult) -> None:
        for deps in self._configs("Gemfile"):
            for dep_name in deps:
                lower = dep_name.lower()
                if lower in ("rails", "rails"):
                    result.frameworks.append(
                        DetectedTechnology(
                            name="Ruby on Rails",
                            category="framework",
                            detected_from="Gemfile",
                        )
                    )
                elif lower in ("sinatra",):
                    result.frameworks.append(
                        DetectedTechnology(
                            name="Sinatra", category="framework", detected_from="Gemfile"
                        )
                    )

    def _detect_from_csproj_files(
        self, repo_path: str, result: DetectionResult
    ) -> None:
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

    def _detect_from_pom_xml_files(
        self, repo_path: str, result: DetectionResult
    ) -> None:
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
                    if (
                        sig_name in dep_key
                        or dep_key.startswith(sig_name)
                        or sig_name == artifact_id
                        or sig_name.endswith("." + artifact_id)
                        or sig_name in group_id
                    ):
                        resolved = self._clone_with_version(tech, dep_version)
                        self._categorize(result, resolved)

    def _detect_infra_files(self, repo_path: str, result: DetectionResult) -> None:
        root = Path(repo_path)

        # The root check is the fast path and, for a single-service repository,
        # the whole answer. `_walk_config` also reported the ones it passed on
        # its way through, because a monorepo keeps its `Dockerfile` beside the
        # service it builds and its compose file under `deploy/` -- checking only
        # the root reported no container tooling at all for those.
        if (root / "Dockerfile").exists() or "Dockerfile" in self._infra_files:
            result.infra.append(self._clone_with_version(INFRA_SIGNALS["dockerfile"]))
        for compose_name in ("docker-compose.yml", "docker-compose.yaml"):
            if (root / compose_name).exists() or compose_name in self._infra_files:
                result.infra.append(
                    self._clone_with_version(INFRA_SIGNALS["docker_compose"])
                )
                break

        has_k8s = False
        for k8s_dir in ("k8s", "kubernetes", "deploy", "manifests"):
            dir_path = root / k8s_dir
            if dir_path.is_dir():
                has_k8s = True
                break
        if not has_k8s:
            for f in root.iterdir():
                if f.suffix in self.K8S_EXTENSIONS and f.name not in (
                    "docker-compose.yml",
                    "docker-compose.yaml",
                ):
                    content = self._safe_read(f)
                    if content and ("apiVersion:" in content and "kind:" in content):
                        has_k8s = True
                        break
        if has_k8s:
            result.infra.append(
                DetectedTechnology(
                    name="Kubernetes",
                    category="infra",
                    detected_from="manifests",
                    confidence=0.8,
                )
            )

        for tf_file in root.rglob("*.tf"):
            if tf_file.is_file():
                result.infra.append(
                    DetectedTechnology(
                        name="Terraform",
                        category="infra",
                        detected_from="*.tf",
                        confidence=0.9,
                    )
                )
                break

        if (root / "nginx.conf").exists() or (root / "nginx/nginx.conf").exists():
            result.infra.append(
                DetectedTechnology(
                    name="Nginx",
                    category="infra",
                    detected_from="nginx.conf",
                    confidence=0.9,
                )
            )

        self._detect_databases_from_env(repo_path, result)

    def _detect_ci(self, repo_path: str, result: DetectionResult) -> None:
        ci_name = detect_ci_platform(repo_path)
        if ci_name:
            result.infra.append(
                DetectedTechnology(
                    name=ci_name, category="infra", detected_from="CI config"
                )
            )

    def _detect_databases_from_env(
        self, repo_path: str, result: DetectionResult
    ) -> None:
        for env_file in (".env", ".env.example"):
            path = Path(repo_path) / env_file
            if not path.exists():
                continue
            content = self._safe_read(path)
            if not content:
                continue

            lower = content.lower()
            db_signals: list[tuple[tuple[str, ...], DetectedTechnology]] = [
                (
                    ("postgresql", "postgres", "psql", "pg"),
                    DetectedTechnology(
                        name="PostgreSQL",
                        category="database",
                        detected_from=".env",
                        confidence=0.7,
                    ),
                ),
                (
                    ("mongodb", "mongo"),
                    DetectedTechnology(
                        name="MongoDB",
                        category="database",
                        detected_from=".env",
                        confidence=0.7,
                    ),
                ),
                (
                    ("redis://",),
                    DetectedTechnology(
                        name="Redis",
                        category="database",
                        detected_from=".env",
                        confidence=0.7,
                    ),
                ),
                (
                    ("kafka://",),
                    DetectedTechnology(
                        name="Kafka",
                        category="infra",
                        detected_from=".env",
                        confidence=0.6,
                    ),
                ),
                (
                    ("rabbitmq://", "amqp://"),
                    DetectedTechnology(
                        name="RabbitMQ",
                        category="infra",
                        detected_from=".env",
                        confidence=0.6,
                    ),
                ),
            ]

            for keywords, tech in db_signals:
                if any(kw in lower for kw in keywords) and not any(
                    t.name == tech.name for t in result.databases + result.infra
                ):
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
    def _clone_with_version(
        tech: DetectedTechnology, version: str | None = None
    ) -> DetectedTechnology:
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
