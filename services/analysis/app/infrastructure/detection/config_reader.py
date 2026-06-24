import json
import os
import re
from pathlib import Path
from typing import Any


def read_json(file_path: str) -> dict[str, Any] | None:
    try:
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, PermissionError):
        return None


def read_toml(file_path: str) -> dict[str, Any] | None:
    try:
        import tomllib
    except ImportError:
        return None

    try:
        with open(file_path, "rb") as f:
            return tomllib.load(f)
    except (FileNotFoundError, PermissionError, ValueError):
        return None


def read_lines(file_path: str) -> list[str] | None:
    try:
        with open(file_path, encoding="utf-8", errors="replace") as f:
            return [line.strip() for line in f if line.strip()]
    except (FileNotFoundError, PermissionError):
        return None


def read_requirements_txt(file_path: str) -> dict[str, str | None] | None:
    lines = read_lines(file_path)
    if lines is None:
        return None

    deps: dict[str, str | None] = {}
    for line in lines:
        line = line.split("#")[0].strip()
        if not line:
            continue
        match = re.match(r"^([a-zA-Z0-9_.-]+)\s*(?:[=~<>!]+\s*([\d.*]+))?", line)
        if match:
            name = match.group(1).lower().replace("-", "_").replace(".", "_")
            version = match.group(2)
            deps[name] = version
    return deps


def read_go_mod(file_path: str) -> dict[str, str | None] | None:
    lines = read_lines(file_path)
    if lines is None:
        return None

    deps: dict[str, str | None] = {}
    in_require_block = False

    for line in lines:
        stripped = line.strip()

        if stripped == "require (":
            in_require_block = True
            continue
        if in_require_block and stripped == ")":
            in_require_block = False
            continue

        if in_require_block:
            parts = stripped.split()
            if len(parts) >= 2 and "/" in parts[0]:
                deps[parts[0]] = parts[1] if len(parts) > 1 else None
        elif stripped.startswith("require ") and not stripped.endswith("("):
            parts = stripped.split()
            if len(parts) >= 2 and "/" in parts[1]:
                deps[parts[1]] = parts[2] if len(parts) > 2 else None

    return deps


def read_cargo_toml(file_path: str) -> dict[str, str | None] | None:
    data = read_toml(file_path)
    if data is None:
        return None

    deps: dict[str, str | None] = {}
    for section in ("dependencies", "dev-dependencies", "build-dependencies"):
        dep_group = data.get(section, {})
        if isinstance(dep_group, dict):
            for name, value in dep_group.items():
                if isinstance(value, str):
                    deps[name] = value
                elif isinstance(value, dict):
                    deps[name] = value.get("version")
    return deps


def read_gemfile(file_path: str) -> dict[str, str | None] | None:
    lines = read_lines(file_path)
    if lines is None:
        return None

    deps: dict[str, str | None] = {}
    for line in lines:
        match = re.match(r"^\s*gem\s+['\"]([^'\"]+)['\"]", line)
        if match:
            name = match.group(1).lower()
            ver_match = re.search(r"['\"]\s*=>\s*['\"]([^'\"]+)['\"]", line)
            deps[name] = ver_match.group(1) if ver_match else None
    return deps


def read_pubspec_yaml(file_path: str) -> dict[str, str | None] | None:
    try:
        import yaml
    except ImportError:
        return None

    try:
        with open(file_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except (FileNotFoundError, PermissionError, yaml.YAMLError):
        return None

    if not isinstance(data, dict):
        return None

    deps: dict[str, str | None] = {}
    for section in ("dependencies", "dev_dependencies"):
        dep_group = data.get(section, {})
        if isinstance(dep_group, dict):
            for name, value in dep_group.items():
                if isinstance(value, str):
                    deps[name] = value
    return deps


def detect_ci_platform(repo_path: str) -> str | None:
    if os.path.isdir(os.path.join(repo_path, ".github", "workflows")):
        return "GitHub Actions"
    if os.path.isfile(os.path.join(repo_path, ".gitlab-ci.yml")):
        return "GitLab CI"
    if os.path.isfile(os.path.join(repo_path, "Jenkinsfile")):
        return "Jenkins"
    if os.path.isfile(os.path.join(repo_path, ".circleci", "config.yml")):
        return "CircleCI"
    ci_dirs = {
        ".drone.yml": "Drone",
        ".woodpecker.yml": "Woodpecker",
        "azure-pipelines.yml": "Azure Pipelines",
        "bitbucket-pipelines.yml": "Bitbucket Pipelines",
    }
    for filename, name in ci_dirs.items():
        if os.path.isfile(os.path.join(repo_path, filename)):
            return name
    return None
