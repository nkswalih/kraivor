import json
import os
import re


def read_json(file_path: str) -> dict[str, object] | None:
    try:
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)  # type: ignore[no-any-return]
    except (FileNotFoundError, json.JSONDecodeError, PermissionError):
        return None


def read_toml(file_path: str) -> dict[str, object] | None:
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


def read_csproj(file_path: str) -> dict[str, str | None] | None:
    """Parse a .csproj file for PackageReference items."""
    try:
        import xml.etree.ElementTree as ET
        tree = ET.parse(file_path)
        root = tree.getroot()
    except (FileNotFoundError, ET.ParseError, PermissionError, ImportError):
        return None

    ns = {"ns": "http://schemas.microsoft.com/developer/msbuild/2003"}
    deps: dict[str, str | None] = {}

    has_ns = root.tag.startswith("{http://schemas.microsoft.com/developer/msbuild/2003}")
    tag = "{http://schemas.microsoft.com/developer/msbuild/2003}PackageReference" if has_ns else "PackageReference"

    for ref in root.iter(tag):
        name = ref.get("Include")
        if not name:
            continue
        version = None
        ver_attr = ref.get("Version")
        if ver_attr:
            version = ver_attr
        elif has_ns:
            ver_elem = ref.find("ns:Version", ns)
            if ver_elem is not None and ver_elem.text:
                version = ver_elem.text
        deps[name.lower()] = version

    return deps


def read_pom_xml(file_path: str) -> dict[str, str | None] | None:
    """Parse a Maven pom.xml for dependencies."""
    try:
        import xml.etree.ElementTree as ET
        tree = ET.parse(file_path)
        root = tree.getroot()
    except (FileNotFoundError, ET.ParseError, PermissionError, ImportError):
        return None

    ns = {"ns": "http://maven.apache.org/POM/4.0.0"}
    deps: dict[str, str | None] = {}

    for dep in root.iter("{http://maven.apache.org/POM/4.0.0}dependency"):
        group_id = dep.find("ns:groupId", ns)
        artifact_id = dep.find("ns:artifactId", ns)
        if group_id is not None and group_id.text and artifact_id is not None and artifact_id.text:
            key = f"{group_id.text.strip()}:{artifact_id.text.strip()}"
            version_elem = dep.find("ns:version", ns)
            version = version_elem.text.strip() if version_elem is not None and version_elem.text else None
            deps[key.lower()] = version

    return deps
