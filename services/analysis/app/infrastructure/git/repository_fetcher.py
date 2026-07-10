import asyncio
import contextlib
import os
import tempfile
from pathlib import Path

from app.core.config import get_settings

settings = get_settings()
from app.core.logging import get_logger
from app.infrastructure.cache.redis import RedisCache

logger = get_logger(__name__)

_LANGUAGE_EXTENSIONS: dict[str, list[str]] = {
    "python": [".py", ".pyi", ".pyx"],
    "javascript": [".js", ".jsx", ".mjs", ".cjs"],
    "typescript": [".ts", ".tsx"],
    "go": [".go"],
    "java": [".java"],
    "rust": [".rs"],
    "ruby": [".rb"],
    "csharp": [".cs"],
    "php": [".php"],
    "kotlin": [".kt", ".kts"],
    "elixir": [".ex", ".exs"],
    "dockerfile": ["Dockerfile", ".dockerfile"],
    "yaml": [".yml", ".yaml"],
    "json": [".json"],
    "markdown": [".md", ".mdx"],
    "shell": [".sh", ".bash"],
    "sql": [".sql"],
}

_EXCLUDED_DIRS: set[str] = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    ".tox",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "vendor",
    "dist",
    "build",
    ".next",
    "target",
    ".terraform",
}

_EXCLUDED_EXTENSIONS: set[str] = {
    ".pyc",
    ".pyo",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".ico",
    ".svg",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".bz2",
    ".lock",
    ".min.js",
    ".min.css",
}


class RepositoryFetcher:
    """Clones repositories for analysis and provides file access.

    Uses shallow clones (--depth 1) for speed. Cloned repos
    are stored in ephemeral storage and cleaned up after analysis.
    """

    def __init__(self, cache: RedisCache | None = None) -> None:
        self._cache = cache

    async def clone(
        self,
        clone_url: str,
        branch: str = "main",
        depth: int = 1,
        github_token: str = "",
    ) -> str:
        """Clone a repository to a temporary directory.

        Args:
            clone_url: Repository clone URL.
            branch: Branch to clone.
            depth: Clone depth (1 = shallow).
            github_token: GitHub token for private repos.

        Returns:
            Path to the cloned repository root.
        """
        os.makedirs(settings.analysis.ephemeral_path, exist_ok=True)
        dest = tempfile.mkdtemp(
            prefix="kraivor_analysis_",
            dir=settings.analysis.ephemeral_path,
        )

        # Add token to URL for private repos
        if github_token and "github.com" in clone_url:
            clone_url = clone_url.replace(
                "https://github.com",
                f"https://x-access-token:{github_token}@github.com",
            )

        cmd = [
            "git",
            "clone",
            "--depth",
            str(depth),
            "--branch",
            branch,
            "--single-branch",
            clone_url,
            dest,
        ]

        stderr_fd: int | None = None
        stderr_path = ""
        try:
            stderr_fd, stderr_path = tempfile.mkstemp(
                suffix=".git_stderr",
                dir=settings.analysis.ephemeral_path,
            )
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=stderr_fd,
            )
            os.close(stderr_fd)
            stderr_fd = None

            try:
                await asyncio.wait_for(proc.wait(), timeout=settings.git.clone_timeout)
            except TimeoutError:
                proc.kill()
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(proc.wait(), timeout=5)
                raise RuntimeError(
                    f"Git clone timed out after {settings.git.clone_timeout}s"
                ) from None

            if proc.returncode != 0:
                with open(stderr_path, "rb") as f:
                    stderr = f.read()
                msg = stderr.decode(errors="replace").strip()
                raise RuntimeError(f"Git clone failed: {msg}")

            logger.info("repository_cloned", url=clone_url, branch=branch, dest=dest)
            return dest
        finally:
            if stderr_fd is not None:
                os.close(stderr_fd)
            if stderr_path and os.path.exists(stderr_path):
                with contextlib.suppress(OSError):
                    os.unlink(stderr_path)

    async def list_branches(self, repo_url: str) -> list[str]:
        import re

        logger.info("listing_branches", url=repo_url)
        proc = await asyncio.create_subprocess_exec(
            "git",
            "ls-remote",
            "--heads",
            repo_url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        branches: list[str] = []
        for line in stdout.decode().splitlines():
            m = re.search(r"refs/heads/(.+)$", line)
            if m:
                branches.append(m.group(1))
        return branches

    async def detect_languages(self, repo_path: str) -> list[str]:
        return await asyncio.to_thread(self._detect_languages_sync, repo_path)

    def _detect_languages_sync(self, repo_path: str) -> list[str]:
        detected: set[str] = set()
        for _root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in _EXCLUDED_DIRS]
            for file in files:
                ext = Path(file).suffix.lower()
                if ext in _EXCLUDED_EXTENSIONS:
                    continue
                for lang, exts in _LANGUAGE_EXTENSIONS.items():
                    if ext in exts or file in exts:
                        detected.add(lang)
        return sorted(detected)

    async def build_file_tree(
        self, repo_path: str
    ) -> dict[str, list[dict[str, object]]]:
        return await asyncio.to_thread(self._build_file_tree_sync, repo_path)

    def _build_file_tree_sync(
        self, repo_path: str
    ) -> dict[str, list[dict[str, object]]]:
        tree: dict[str, list[dict[str, object]]] = {}
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in _EXCLUDED_DIRS]
            rel_root = os.path.relpath(root, repo_path)
            if rel_root == ".":
                rel_root = ""

            for file in files:
                ext = Path(file).suffix.lower()
                if ext in _EXCLUDED_EXTENSIONS or file in _EXCLUDED_EXTENSIONS:
                    continue
                full_path = os.path.join(root, file)
                rel_path = os.path.join(rel_root, file) if rel_root else file
                lang = self._detect_language(file)
                size = os.path.getsize(full_path)

                entry = {
                    "path": rel_path,
                    "size": size,
                    "language": lang,
                }

                if lang not in tree:
                    tree[lang] = []
                tree[lang].append(entry)

        return tree

    async def count_loc(self, repo_path: str) -> int:
        return await asyncio.to_thread(self._count_loc_sync, repo_path)

    def _count_loc_sync(self, repo_path: str) -> int:
        total = 0
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in _EXCLUDED_DIRS]
            for file in files:
                ext = Path(file).suffix.lower()
                if ext in _EXCLUDED_EXTENSIONS:
                    continue
                full_path = os.path.join(root, file)
                try:
                    with open(full_path, "rb") as f:
                        total += sum(1 for _ in f)
                except (OSError, PermissionError):
                    continue
        return total

    async def get_source_files(self, repo_path: str) -> list[dict[str, object]]:
        return await asyncio.to_thread(self._get_source_files_sync, repo_path)

    def _get_source_files_sync(self, repo_path: str) -> list[dict[str, object]]:
        files: list[dict[str, object]] = []
        for root, dirs, _ in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in _EXCLUDED_DIRS]
            for file in _:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, repo_path)
                ext = Path(file).suffix.lower()

                if ext in _EXCLUDED_EXTENSIONS:
                    continue

                language = self._detect_language(file)
                if not language:
                    continue

                try:
                    size = os.path.getsize(full_path)
                    if size > settings.analysis.max_file_size_bytes:
                        logger.warning(
                            "file_too_large",
                            path=rel_path,
                            size=size,
                        )
                        continue

                    with open(full_path, encoding="utf-8", errors="replace") as f:
                        content = f.read()

                    files.append(
                        {
                            "path": rel_path,
                            "language": language,
                            "content": content,
                            "size_bytes": size,
                            "lines_count": content.count("\n") + 1,
                        }
                    )
                except (OSError, PermissionError, UnicodeDecodeError) as e:
                    logger.warning(
                        "file_read_error",
                        path=rel_path,
                        error=str(e),
                    )
                    continue

        return files

    async def cleanup(self, repo_path: str) -> None:
        """Remove the cloned repository."""
        import shutil

        try:
            shutil.rmtree(repo_path, ignore_errors=True)
            logger.info("repository_cleaned_up", path=repo_path)
        except OSError as e:
            logger.error("repository_cleanup_failed", path=repo_path, error=str(e))

    @staticmethod
    def _detect_language(filename: str) -> str:
        ext = Path(filename).suffix.lower()
        if filename in _LANGUAGE_EXTENSIONS.get("dockerfile", []):
            return "dockerfile"
        for lang, exts in _LANGUAGE_EXTENSIONS.items():
            if ext in exts:
                return lang
        return ""
