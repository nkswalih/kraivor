"""Framework detection on a monorepo, which used to return nothing.

`_collect_config_files` walked only the repository root, and every
`_detect_from_*` method was pointed at root-level paths. This repository's own
root `pyproject.toml` is tool configuration -- no `[project]` table, no
dependencies -- while the real manifests live at `services/*/pyproject.toml` and
`frontend/package.json`. Nothing that declared a framework was read, so a run
reported zero frameworks on a repository built entirely from them.

The walk is bounded (depth, file count, skipped directories) because the
alternative was an unbounded search through `node_modules` and `.venv`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.infrastructure.detection.detector import FrameworkDetector
from app.infrastructure.detection.models import DetectionResult


def _write(root: Path, rel: str, content: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _names(detected: list[object]) -> set[str]:
    """Lower-cased display names -- the signature table owns capitalisation."""
    return {t.name.lower() for t in detected}  # type: ignore[attr-defined]


def _infra_names(result: DetectionResult) -> set[str]:
    return {t.name.lower() for t in result.infra}


async def _detect(root: Path) -> DetectionResult:
    return await FrameworkDetector().detect(str(root))


@pytest.mark.asyncio
class TestMonorepoConfigDiscovery:
    async def test_nested_pyproject_is_read(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "services/api/pyproject.toml",
            '[project]\nname = "api"\ndependencies = ["fastapi>=0.115"]\n',
        )

        result = await _detect(tmp_path)

        assert "fastapi" in _names(result.frameworks)

    async def test_every_package_contributes(self, tmp_path: Path) -> None:
        """Two services, two different stacks -- both must survive.

        Before, each key held one dict, so whichever file happened to be read
        last overwrote the one before it.
        """
        _write(
            tmp_path,
            "services/api/pyproject.toml",
            '[project]\ndependencies = ["fastapi>=0.115"]\n',
        )
        _write(
            tmp_path,
            "services/worker/pyproject.toml",
            '[project]\ndependencies = ["celery>=5.4"]\n',
        )

        result = await _detect(tmp_path)

        names = _names(result.frameworks) | _names(result.tools)
        assert "fastapi" in names
        assert "celery" in names

    async def test_nested_package_json_is_read(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "frontend/package.json",
            '{"name":"web","dependencies":{"react":"^19.0.0",'
            '"next":"15.1.0"}}\n',
        )

        result = await _detect(tmp_path)

        names = _names(result.frameworks)
        assert "react" in names
        assert "next.js" in names

    async def test_dependencies_and_dev_dependencies_both_count(
        self, tmp_path: Path
    ) -> None:
        """A framework parked in `devDependencies` is still the framework."""
        _write(
            tmp_path,
            "packages/ui/package.json",
            '{"name":"ui","devDependencies":{"vite":"^6.0.0"}}\n',
        )

        result = await _detect(tmp_path)

        assert "vite" in _names(result.frameworks) | _names(result.tools)

    async def test_root_tool_config_without_project_table_contributes_nothing(
        self, tmp_path: Path
    ) -> None:
        _write(
            tmp_path,
            "pyproject.toml",
            '[tool.ruff]\nline-length = 88\n',
        )

        result = await _detect(tmp_path)

        assert _names(result.frameworks) == set()


@pytest.mark.asyncio
class TestRequirementsDiscovery:
    async def test_root_requirements(self, tmp_path: Path) -> None:
        _write(tmp_path, "requirements.txt", "django>=5.1\n")

        result = await _detect(tmp_path)

        assert "django" in _names(result.frameworks)

    async def test_requirements_in_a_subdirectory(self, tmp_path: Path) -> None:
        _write(tmp_path, "services/api/requirements.txt", "flask>=3.0\n")

        result = await _detect(tmp_path)

        assert "flask" in _names(result.frameworks)

    async def test_requirements_txt_suffix(self, tmp_path: Path) -> None:
        _write(tmp_path, "deploy/requirements-dev.txt", "pytest>=8.0\n")

        result = await _detect(tmp_path)

        assert "pytest" in _names(result.tools)

    async def test_readme_txt_is_not_parsed_as_dependencies(
        self, tmp_path: Path
    ) -> None:
        """A bare `.txt` match would have read every text file in the repo."""
        _write(tmp_path, "README.txt", "kraivor is a fastapi based tool\n")

        result = await _detect(tmp_path)

        assert _names(result.frameworks) == set()

    async def test_license_txt_is_not_parsed_as_dependencies(
        self, tmp_path: Path
    ) -> None:
        _write(tmp_path, "LICENSE.txt", "MIT license, mentions react once\n")

        result = await _detect(tmp_path)

        assert _names(result.frameworks) == set()


@pytest.mark.asyncio
class TestOptionalDependencyGroups:
    async def test_optional_groups_beyond_dev_are_read(
        self, tmp_path: Path
    ) -> None:
        _write(
            tmp_path,
            "services/api/pyproject.toml",
            '[project.optional-dependencies]\n'
            'worker = ["celery>=5.4"]\n'
            'test = ["pytest>=8.0"]\n',
        )

        result = await _detect(tmp_path)

        names = _names(result.frameworks) | _names(result.tools)
        assert "celery" in names
        assert "pytest" in names

    async def test_pep_735_dependency_groups(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "pyproject.toml",
            '[project]\nname = "x"\n'
            '[dependency-groups]\ndevelopment = ["pytest>=8.0"]\n',
        )

        result = await _detect(tmp_path)

        assert "pytest" in _names(result.tools)

    async def test_poetry_groups(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "pyproject.toml",
            '[tool.poetry.group.test.dependencies]\npytest = "^8.0"\n'
            '[tool.poetry.dependencies]\npython = "^3.12"\n'
            'django = "^5.1"\n',
        )

        result = await _detect(tmp_path)

        names = _names(result.frameworks) | _names(result.tools)
        assert "django" in names
        assert "pytest" in names


@pytest.mark.asyncio
class TestWalkBounds:
    async def test_dependency_directories_are_skipped(
        self, tmp_path: Path
    ) -> None:
        _write(
            tmp_path,
            "node_modules/left-pad/package.json",
            '{"dependencies":{"left-pad":"1.0.0"}}\n',
        )
        _write(
            tmp_path,
            "services/api/pyproject.toml",
            '[project]\ndependencies = ["fastapi>=0.115"]\n',
        )

        result = await _detect(tmp_path)

        names = _names(result.frameworks)
        assert "fastapi" in names
        assert "left-pad" not in names

    async def test_a_manifest_deeper_than_the_bound_is_ignored(
        self, tmp_path: Path
    ) -> None:
        deep = "/".join(f"level{i}" for i in range(8))
        _write(
            tmp_path,
            f"{deep}/pyproject.toml",
            '[project]\ndependencies = ["fastapi>=0.115"]\n',
        )

        result = await _detect(tmp_path)

        assert _names(result.frameworks) == set()

    async def test_malformed_manifest_does_not_raise(
        self, tmp_path: Path
    ) -> None:
        _write(tmp_path, "frontend/package.json", "{not json at all")
        _write(tmp_path, "pyproject.toml", "not toml at all =[")

        result = await _detect(tmp_path)

        assert isinstance(result.frameworks, list)


@pytest.mark.asyncio
class TestContainerManifests:
    async def test_dockerfile_outside_the_root_counts(
        self, tmp_path: Path
    ) -> None:
        _write(tmp_path, "services/api/Dockerfile", "FROM python:3.14\n")

        result = await _detect(tmp_path)

        assert "docker" in _infra_names(result)

    async def test_compose_file_under_deploy_counts(
        self, tmp_path: Path
    ) -> None:
        _write(tmp_path, "deploy/docker-compose.yml", "services:\n  api: {}\n")

        result = await _detect(tmp_path)

        assert "docker compose" in _infra_names(result)

    async def test_root_dockerfile_still_counts(self, tmp_path: Path) -> None:
        _write(tmp_path, "Dockerfile", "FROM python:3.14\n")

        result = await _detect(tmp_path)

        assert "docker" in _infra_names(result)
