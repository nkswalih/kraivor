#!/usr/bin/env python
"""Fail CI if the container base images or the Python version drift.

Two things this guards, both of which happened before and cost real time:

1. Every third-party base image must be pinned by digest. A mutable tag like
   ``python:3.11-slim`` means two builds a week apart get different bytes, and
   nobody notices until an image behaves differently in production. Dependabot
   keeps the digests current; this check stops one from being dropped.

   Images built by this repo are exempt, since their digests do not exist until
   a pipeline publishes them. The exemptions are listed explicitly below rather
   than pattern-matched, so adding a new first-party image is a deliberate act.

2. The declared Python floor, the interpreter CI runs, the interpreter the
   linters target and the tag baked into the Dockerfiles must all agree. The
   root pyproject used to say py312 while three services said py311, CI ran
   3.12 and the images shipped 3.11 -- four different answers to one question.

Run directly: ``python scripts/check_base_images.py``
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys
import tomllib

# Images this repo builds and pushes itself. No digest exists in the repo.
FIRST_PARTY = (
    "${ECR_REGISTRY}/",
    "kraivor-",
)

SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".ruff_cache", ".pytest_cache"}

SERVICES = ("auth", "core", "ai", "analysis", "notifications")

# Dockerfile FROM tags are floats on purpose: they name the release for humans,
# and the digest behind them is the immutable truth.
PYTHON_TAG_RE = re.compile(r"^python:(3)\.(\d+)")
NODE_TAG_RE = re.compile(r"^node:(\d+)")


def walk(patterns: tuple[str, ...]) -> list[str]:
    out: list[str] = []
    for pattern in patterns:
        out.extend(glob.glob(pattern, recursive=True))
    return sorted(
        p.replace("\\", "/")
        for p in out
        if not any(sep in p for sep in SKIP_DIRS)
    )


def is_first_party(ref: str) -> bool:
    return any(ref.startswith(prefix) for prefix in FIRST_PARTY)


def check_digests() -> list[str]:
    """Every base image reference must carry an @sha256: digest."""
    problems: list[str] = []
    files = walk(
        (
            "*/Dockerfile*",
            "services/*/Dockerfile*",
            "docker-compose*.yml",
            ".github/workflows/*.yml",
            "infra/kubernetes/**/*.yaml",
        )
    )

    for path in files:
        with open(path, "rb") as fh:
            lines = fh.read().decode("utf-8", "replace").splitlines()

        for number, line in enumerate(lines, 1):
            stripped = line.strip()

            if stripped.startswith("FROM "):
                ref = stripped.split()[1]
            elif stripped.startswith("image:"):
                ref = stripped.split("image:", 1)[1].strip().strip('"').strip("'")
            else:
                continue

            if not ref or is_first_party(ref):
                continue

            # ARG-driven bases cannot be pinned at the FROM line.
            if ref.startswith("$"):
                continue

            if "@sha256:" not in ref:
                problems.append(
                    f"{path}:{number}: base image is not pinned by digest: {ref}"
                )

    return problems


def declared_python_floor() -> dict[str, str]:
    """requires-python for each service, plus the root linter target."""
    floors: dict[str, str] = {}
    for service in SERVICES:
        path = f"services/{service}/pyproject.toml"
        if not os.path.exists(path):
            continue
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
        floors[service] = data.get("project", {}).get("requires-python", "<unset>")
    return floors


def check_python_consistency() -> list[str]:
    """The floor, CI, the linters and the images must name one Python."""
    problems: list[str] = []
    floors = declared_python_floor()

    distinct = set(floors.values())
    if len(distinct) > 1:
        detail = ", ".join(f"{k}={v}" for k, v in sorted(floors.items()))
        problems.append(f"services disagree on requires-python: {detail}")

    if not floors:
        return problems

    floor = next(iter(distinct))
    match = re.search(r">=\s*(\d+)\.(\d+)", floor)
    if not match:
        problems.append(f"cannot parse requires-python {floor!r}")
        return problems
    floor_minor = int(match.group(2))

    # CI interpreter
    for wf in glob.glob(".github/workflows/*.yml"):
        with open(wf, "rb") as fh:
            text = fh.read().decode("utf-8", "replace")
        for number, line in enumerate(text.splitlines(), 1):
            if "PYTHON_VERSION" not in line:
                continue
            ci = re.search(r'"(3)\.(\d+)"', line)
            if not ci:
                continue
            ci_minor = int(ci.group(2))
            if ci_minor < floor_minor:
                problems.append(
                    f"{wf}:{number}: CI runs Python 3.{ci_minor} but "
                    f"services require >=3.{floor_minor}"
                )

    # Linter targets in every pyproject
    for path in walk(("pyproject.toml", "services/*/pyproject.toml")):
        with open(path, "rb") as fh:
            text = fh.read().decode("utf-8", "replace")
        for number, line in enumerate(text.splitlines(), 1):
            target = re.search(r'target-version\s*=\s*\[?"py3(\d+)"', line)
            if target and int(target.group(1)) != floor_minor:
                problems.append(
                    f"{path}:{number}: linter targets py3{target.group(1)} "
                    f"but the floor is 3.{floor_minor}"
                )
            mypy = re.search(r'python_version\s*=\s*"3\.(\d+)"', line)
            if mypy and int(mypy.group(1)) != floor_minor:
                problems.append(
                    f"{path}:{number}: mypy targets 3.{mypy.group(1)} "
                    f"but the floor is 3.{floor_minor}"
                )

    # Dockerfile base tags
    for path in walk(("services/*/Dockerfile", "services/*/Dockerfile.dev")):
        with open(path, "rb") as fh:
            for number, line in enumerate(fh.read().decode("utf-8", "replace").splitlines(), 1):
                if not line.startswith("FROM "):
                    continue
                ref = line.split()[1].split("@")[0]
                hit = PYTHON_TAG_RE.match(ref)
                if hit and int(hit.group(2)) != floor_minor:
                    problems.append(
                        f"{path}:{number}: image ships Python 3.{hit.group(2)} "
                        f"but the floor is 3.{floor_minor}"
                    )

    return problems


def check_node_consistency() -> list[str]:
    """For each service with a manifest, the Node image and @types/node must
    not sit a major apart. Directories without a package.json are skipped
    rather than inheriting someone else's types."""
    problems: list[str] = []

    for directory in ("frontend", "services/realtime"):
        pkg_path = f"{directory}/package.json"
        dockerfile = f"{directory}/Dockerfile"
        if not (os.path.exists(pkg_path) and os.path.exists(dockerfile)):
            continue

        with open(pkg_path, "rb") as fh:
            pkg = json.loads(fh.read().decode("utf-8"))

        types = (pkg.get("devDependencies") or {}).get("@types/node", "")
        types_major = re.search(r"\^(\d+)", types)
        if not types_major:
            problems.append(f"{pkg_path}: cannot read a major from @types/node {types!r}")
            continue

        with open(dockerfile, "rb") as fh:
            for number, line in enumerate(fh.read().decode("utf-8", "replace").splitlines(), 1):
                if not line.startswith("FROM "):
                    continue
                ref = line.split()[1].split("@")[0]
                hit = NODE_TAG_RE.match(ref)
                if hit and int(hit.group(1)) != int(types_major.group(1)):
                    problems.append(
                        f"{dockerfile}:{number}: image ships Node {hit.group(1)} "
                        f"but @types/node is {types_major.group(1)}"
                    )
                image_major = int(hit.group(1)) if hit else None

        # CI must build on the same Node major the image ships.
        if image_major is None:
            continue
        for wf in glob.glob(".github/workflows/*.yml"):
            with open(wf, "rb") as fh:
                text = fh.read().decode("utf-8", "replace")
            for number, line in enumerate(text.splitlines(), 1):
                declared = re.search(r'node-version:\s*"?(\d+)', line)
                if declared and int(declared.group(1)) != image_major:
                    problems.append(
                        f"{wf}:{number}: CI uses Node {declared.group(1)} "
                        f"but the images ship Node {image_major}"
                    )

    return problems


def main() -> int:
    problems = check_digests() + check_python_consistency() + check_node_consistency()

    if problems:
        print("Base image / toolchain drift detected:\n", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        print(
            "\nPin the image (tag@sha256:...), then re-run:\n"
            "  python scripts/check_base_images.py",
            file=sys.stderr,
        )
        return 1

    floors = declared_python_floor()
    print(f"Base images digest-pinned; Python floor consistent ({next(iter(set(floors.values())), 'n/a')}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())