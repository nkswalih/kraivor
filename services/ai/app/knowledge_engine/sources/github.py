"""GitHub provider — repos, releases, issues, discussions."""

from __future__ import annotations

import logging
from datetime import datetime

from app.knowledge_engine.config import KnowledgeEngineConfig
from app.knowledge_engine.sources.base import SourceResult, SourceContent

logger = logging.getLogger(__name__)

_HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "Kraivor-AI/1.0",
}


class GitHubProvider:
    """GitHub API provider for repositories, releases, and issues."""

    name = "github"
    base_trust_score = 0.90

    def __init__(self, config: KnowledgeEngineConfig | None = None):
        self.config = config or KnowledgeEngineConfig()
        if self.config.github_token:
            _HEADERS["Authorization"] = f"token {self.config.github_token}"

    async def search(self, query: str, max_results: int = 5) -> list[SourceResult]:
        """Search GitHub repositories."""
        try:
            import aiohttp

            url = (
                f"https://api.github.com/search/repositories"
                f"?q={query}"
                f"&sort=stars"
                f"&per_page={max_results}"
            )

            async with aiohttp.ClientSession(headers=_HEADERS) as session, session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()

            results = []
            for item in data.get("items", [])[:max_results]:
                results.append(SourceResult(
                    url=item.get("html_url", ""),
                    title=f"{item.get('full_name', '')} — {item.get('description', '')[:100]}",
                    snippet=(
                        f"Stars: {item.get('stargazers_count', 0)} | "
                        f"Language: {item.get('language', 'N/A')} | "
                        f"Updated: {item.get('updated_at', '')[:10]}"
                    ),
                    source_provider=self.name,
                    trust_score=self.base_trust_score,
                    metadata={
                        "stars": item.get("stargazers_count", 0),
                        "language": item.get("language"),
                        "topics": item.get("topics", []),
                    },
                ))
            return results
        except Exception as e:
            logger.warning("GitHub search failed: %s", e)
            return []

    async def fetch_content(self, url: str) -> SourceContent | None:
        """Fetch README or release notes from a GitHub URL."""
        try:
            import aiohttp

            # Parse owner/repo from URL
            parts = url.rstrip("/").split("/")
            if len(parts) < 5:
                return None
            owner = parts[-2]
            repo = parts[-1]

            # Try to get README
            readme_url = f"https://api.github.com/repos/{owner}/{repo}/readme"
            async with aiohttp.ClientSession(headers=_HEADERS) as session, session.get(
                readme_url,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    import base64
                    content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="replace")
                    if len(content) > 8000:
                        content = content[:8000] + "\n\n[Content truncated...]"

                    return SourceContent(
                        url=url,
                        title=f"{owner}/{repo} README",
                        text=content,
                        source_provider=self.name,
                        trust_score=self.base_trust_score,
                    )

            # Fallback: get latest release
            release_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
            async with aiohttp.ClientSession(headers=_HEADERS) as session, session.get(
                release_url,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    body = data.get("body", "No release notes")
                    if len(body) > 8000:
                        body = body[:8000] + "\n\n[Content truncated...]"

                    return SourceContent(
                        url=url,
                        title=f"{owner}/{repo} — Latest Release: {data.get('tag_name', '')}",
                        text=body,
                        source_provider=self.name,
                        trust_score=self.base_trust_score,
                        published_at=self._parse_date(data.get("published_at")),
                    )

            return None
        except Exception as e:
            logger.warning("GitHub fetch failed for %s: %s", url, e)
            return None

    def _parse_date(self, date_str: str | None) -> datetime | None:
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
