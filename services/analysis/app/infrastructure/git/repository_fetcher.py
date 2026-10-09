import asyncio
import contextlib
import os
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

from app.core.config import get_settings

settings = get_settings()
from app.core.logging import get_logger
from app.infrastructure.cache.redis import RedisCache

logger = get_logger(__name__)

# Hosts that may receive the GitHub token. Compared by parsed hostname.
_GITHUB_HOSTS = frozenset({"github.com", "www.github.com"})


def _is_github_host(url: str) -> bool:
    """Return True if the URL hostname is exactly a GitHub host.

    Substring matching is not sufficient: ``https://github.com.evil.com/x``
    contains ``github.com`` but its host is ``github.com.evil.com``, and a
    naive replace would attach the token to that host.
    """
    try:
        host = urlsplit(url).hostname
    except ValueError:
        return False
    return host is not None and host.lower() in _GITHUB_HOSTS


# Which extension (or bare filename) belongs to which language.
#
# This table is the single source of truth for three things that used to drift
# apart: `languages_detected`, the language breakdown's per-language line
# counts, and which files `get_source_files` hands to the parsers. When it held
# sixteen languages, a repository full of HTML, CSS, TOML, Terraform, INI and
# plain-text config counted every one of those lines into `total_lines` while
# attributing them to no language at all -- so the breakdown's shares summed to
# 100 over a denominator that was a fifth of the number printed beside them.
#
# Names follow GitHub Linguist's, lowercased, because that is the name a reader
# already associates with the colour in the frontend's `language-colors` table.
_LANGUAGE_EXTENSIONS: dict[str, list[str]] = {
    # ── General purpose ───────────────────────────────────
    "python": [".py", ".pyi", ".pyx", ".pyw", ".pyz"],
    "javascript": [".js", ".jsx", ".mjs", ".cjs"],
    "typescript": [".ts", ".tsx", ".mts", ".cts"],
    "go": [".go"],
    "java": [".java"],
    "rust": [".rs"],
    "ruby": [".rb", ".rake", ".gemspec"],
    "php": [".php", ".php3", ".php4", ".php5", ".phtml"],
    "kotlin": [".kt", ".kts"],
    "elixir": [".ex", ".exs"],
    "swift": [".swift"],
    "scala": [".scala"],
    "dart": [".dart"],
    "perl": [".pl", ".pm", ".pod"],
    "lua": [".lua"],
    "haskell": [".hs", ".lhs"],
    "erlang": [".erl", ".hrl"],
    "clojure": [".clj", ".cljs", ".edn"],
    "ocaml": [".ml", ".mli"],
    "r": [".r", ".rmd"],
    "matlab": [".mat"],
    "julia": [".jl"],
    "groovy": [".gradle", ".groovy"],
    "pascal": [".pas", ".pp"],
    "fortran": [".f", ".f90", ".f95"],
    "cobol": [".cbl", ".cob"],
    "crystal": [".cr"],
    "nim": [".nim"],
    "zig": [".zig"],
    "solidity": [".sol"],
    "protobuf": [".proto"],
    "viml": [".vim"],
    "coffeescript": [".coffee"],
    "pug": [".pug", ".jade"],
    "handlebars": [".hbs", ".handlebars"],
    # ── C family ──────────────────────────────────────────
    # `.h` is ambiguous between C and C++ headers and Linguist resolves it by
    # contents. Attributing it to C is the cheaper error: a C++ project shows
    # `cpp` from its `.hpp`/`.cc` files either way.
    "c": [".c", ".h"],
    "cpp": [".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx"],
    "csharp": [".cs", ".csx"],
    "objective-c": [".m"],
    "objective-c++": [".mm"],
    # ── Web ───────────────────────────────────────────────
    "html": [".html", ".htm", ".xhtml"],
    "vue": [".vue"],
    "css": [".css"],
    "scss": [".scss"],
    "sass": [".sass"],
    "less": [".less"],
    "svelte": [".svelte"],
    "graphql": [".graphql", ".gql"],
    "jupyter": [".ipynb"],
    # ── Data & config ─────────────────────────────────────
    "yaml": [".yml", ".yaml"],
    "json": [".json", ".jsonc", ".json5"],
    "markdown": [".md", ".mdx", ".markdown"],
    "toml": [".toml"],
    "xml": [".xml", ".xsd", ".xsl", ".xslt"],
    "csv": [".csv", ".tsv"],
    "tex": [".tex", ".sty", ".cls"],
    "rst": [".rst"],
    # ── Shell & build ─────────────────────────────────────
    "shell": [".sh", ".bash", ".zsh", ".ksh"],
    "powershell": [".ps1", ".psm1", ".psd1"],
    "batchfile": [".bat", ".cmd"],
    "makefile": ["Makefile", "makefile", "GNUmakefile", ".mk"],
    "cmake": ["CMakeLists.txt", ".cmake"],
    "terraform": [".tf", ".tfvars"],
    "hcl": [".hcl"],
    "nix": [".nix"],
    "dockerfile": ["Dockerfile", ".dockerfile", "Containerfile"],
    # ── Markup ────────────────────────────────────────────
    "sql": [".sql"],
}

# The catch-all bucket. A file whose extension maps to no language still has
# lines, and those lines are in `total_lines`, so they have to be attributed
# somewhere for the shares to sum to the figure printed beside them.
_OTHER_LANGUAGE = "other"

# Filenames that carry no extension and so reach `_detect_language` as "".
# Kept separate because they are matched by exact name rather than suffix.
_LANGUAGE_FILENAMES: dict[str, str] = {
    "dockerfile": "dockerfile",
    "containerfile": "dockerfile",
    "makefile": "makefile",
    "gnumakefile": "makefile",
    "cmakelists.txt": "cmake",
    "gemfile": "ruby",
    "rakefile": "ruby",
    "jenkinsfile": "groovy",
    "vagrantfile": "ruby",
    "procfile": "shell",
    "dockerfile.dev": "dockerfile",
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
            prefix="kraivor_analysis_", dir=settings.analysis.ephemeral_path
        )

        # Add token to URL for private repos. The host is compared exactly
        # rather than by substring: "github.com" in url would also match
        # https://github.com.evil.com/, and the replace below would then
        # splice the token into an attacker-controlled URL.
        if github_token and _is_github_host(clone_url):
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
                suffix=".git_stderr", dir=settings.analysis.ephemeral_path
            )
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=stderr_fd
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
                # Routed through `_detect_language` rather than re-deriving the
                # answer here, so the names this reports and the names the line
                # breakdown buckets under cannot drift apart.
                lang = self._detect_language(file)
                if lang:
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

                entry = {"path": rel_path, "size": size, "language": lang}

                if lang not in tree:
                    tree[lang] = []
                tree[lang].append(entry)

        return tree

    async def language_line_counts(self, repo_path: str) -> dict[str, int]:
        """Lines of code per language, over a single walk of the repository.

        Returns every language present, including `_OTHER_LANGUAGE` for files
        no entry maps. Summing the result is what `total_lines` is, so a
        language breakdown built from this and the LINES figure printed beside
        it cannot disagree -- which is what they did before, when the breakdown
        was summed over only the language-mapped files while `total_lines`
        counted every non-excluded file, including `.toml`, `.html`, `.css`,
        `.tf`, `.ini` and every extensionless file in the repository.

        Deliberately one walk rather than two: a breakdown derived from
        `get_source_files` shares neither its exclusions nor its size cap, so
        the two could never be made to agree by adjusting one of them.
        """
        return await asyncio.to_thread(self._language_line_counts_sync, repo_path)

    def _language_line_counts_sync(self, repo_path: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in _EXCLUDED_DIRS]
            for file in files:
                ext = Path(file).suffix.lower()
                if ext in _EXCLUDED_EXTENSIONS:
                    continue
                full_path = os.path.join(root, file)
                try:
                    with open(full_path, "rb") as f:
                        lines = sum(1 for _ in f)
                except (OSError, PermissionError):
                    continue
                lang = self._detect_language(file) or _OTHER_LANGUAGE
                counts[lang] = counts.get(lang, 0) + lines
        return counts

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
                        logger.warning("file_too_large", path=rel_path, size=size)
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
                    logger.warning("file_read_error", path=rel_path, error=str(e))
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
        """Map a filename to a language key, or "" when nothing maps.

        Filenames are tried before extensions because `Makefile`,
        `CMakeLists.txt` and `Dockerfile` carry no extension at all and the
        suffix lookup below would return "" for them.
        """
        name = filename.lower()
        if name in _LANGUAGE_FILENAMES:
            return _LANGUAGE_FILENAMES[name]

        ext = Path(filename).suffix.lower()
        for lang, exts in _LANGUAGE_EXTENSIONS.items():
            if ext and ext in exts:
                return lang
        return ""
