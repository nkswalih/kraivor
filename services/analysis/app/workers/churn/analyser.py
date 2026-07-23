import asyncio
import os
import subprocess
from collections import Counter
from dataclasses import dataclass

from app.core.constants import Severity
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ChurnFinding:
    file_path: str
    change_count: int
    unique_authors: int
    total_commits_analyzed: int

    def to_dict(self) -> dict[str, object]:
        return {
            "file_path": self.file_path,
            "change_count": self.change_count,
            "unique_authors": self.unique_authors,
            "total_commits_analyzed": self.total_commits_analyzed,
        }


class ChurnAnalyser:
    """Analyses git commit churn to identify hotspot files.

    Requires at least 2 commits of history to produce meaningful results.
    The more depth available, the more accurate the churn signal.
    """

    def __init__(self, repo_path: str, depth: int = 1) -> None:
        self._repo_path = repo_path
        self._depth = depth
        self._git_dir = os.path.join(repo_path, ".git")

    async def analyse(self) -> list[ChurnFinding]:
        if self._depth <= 1:
            logger.info("churn_skipped", reason="depth_too_shallow", depth=self._depth)
            return []

        return await asyncio.get_event_loop().run_in_executor(None, self._analyze_sync)

    def _analyze_sync(self) -> list[ChurnFinding]:
        try:
            file_changes = self._get_file_change_counts()
        except subprocess.CalledProcessError as e:
            logger.warning("churn_git_log_failed", error=str(e.stderr))
            return []
        except FileNotFoundError:
            logger.warning("churn_git_not_found")
            return []

        if not file_changes:
            return []

        total_commits = self._count_commits()
        changes = Counter(file_changes)

        threshold = self._compute_threshold(changes)
        findings: list[ChurnFinding] = []

        for file_path, count in changes.most_common(20):
            if count < threshold:
                break

            author_count = self._count_authors(file_path)
            findings.append(
                ChurnFinding(
                    file_path=file_path,
                    change_count=count,
                    unique_authors=author_count,
                    total_commits_analyzed=total_commits,
                )
            )

        return findings

    def _get_file_change_counts(self) -> list[str]:
        cmd = [
            "git",
            f"--git-dir={self._git_dir}",
            "--work-tree",
            self._repo_path,
            "log",
            f"--max-count={self._depth}",
            "--format=",
            "--name-only",
            "--diff-filter=AM",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        result.check_returncode()

        files: list[str] = []
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("{"):
                files.append(stripped)
        return files

    def _count_commits(self) -> int:
        cmd = [
            "git",
            f"--git-dir={self._git_dir}",
            "--work-tree",
            self._repo_path,
            "rev-list",
            "--count",
            f"--max-count={self._depth}",
            "HEAD",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return 0
        return int(result.stdout.strip())

    def _count_authors(self, file_path: str) -> int:
        cmd = [
            "git",
            f"--git-dir={self._git_dir}",
            "--work-tree",
            self._repo_path,
            "log",
            f"--max-count={self._depth}",
            "--format=%an",
            "--",
            file_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return 0
        authors = {line.strip() for line in result.stdout.splitlines() if line.strip()}
        return len(authors)

    @staticmethod
    def _compute_threshold(changes: Counter[str]) -> int:
        if not changes:
            return 0
        values = sorted(changes.values(), reverse=True)
        p80 = max(1, len(values) * 80 // 100)
        return values[p80] if p80 < len(values) else max(1, values[-1])


def finding_from_churn(
    churn: ChurnFinding, job_id: object, repo_id: object, workspace_id: object
) -> dict[str, object]:
    severity = (
        Severity.HIGH
        if churn.change_count >= 10
        else Severity.MEDIUM if churn.change_count >= 5 else Severity.LOW
    )

    multi_author_note = ""
    if churn.unique_authors > 3:
        multi_author_note = (
            f" {churn.unique_authors} different developers have touched this file, "
            "indicating ownership diffusion."
        )

    return {
        "job_id": job_id,
        "repo_id": repo_id,
        "workspace_id": workspace_id,
        "rule_id": "churn/hotspot",
        "category": "quality",
        "severity": str(severity),
        "title": f"High churn file: {churn.file_path}",
        "description": (
            f"This file was modified {churn.change_count} times "
            f"across {churn.total_commits_analyzed} analyzed commits."
            f"{multi_author_note}"
        ),
        "recommendation": (
            "Review this file for refactoring opportunities. High-churn files "
            "are statistically more likely to contain bugs. Consider splitting "
            "the file into smaller, single-responsibility modules."
        ),
        "file_path": churn.file_path,
        "line_start": None,
        "line_end": None,
        "code_snippet": "",
        "score_impact": -5.0 if churn.change_count >= 10 else -2.0,
        "rpm_impact": 0,
        "breaks_at_users": None,
    }
