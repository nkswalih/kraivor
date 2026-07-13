"""Web search provider — multi-provider with fallback chain.

Priority: Tavily (best quality) -> DDGS (free) -> Google Custom Search (fallback)
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.knowledge_engine.config import KnowledgeEngineConfig
from app.knowledge_engine.sources.base import SourceResult, SourceContent

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
}


class WebSearchProvider:
    """Multi-provider web search with fallback chain."""

    name = "web_search"
    base_trust_score = 0.5

    def __init__(self, config: KnowledgeEngineConfig | None = None):
        self.config = config or KnowledgeEngineConfig()

    async def search(self, query: str, max_results: int = 5) -> list[SourceResult]:
        """Search using multiple providers with fallback."""
        # Try Tavily first (best quality)
        if self.config.tavily_api_key:
            results = await self._search_tavily(query, max_results)
            if results:
                return results

        # Fallback to DDGS
        results = await self._search_ddgs(query, max_results)
        if results:
            return results

        # Fallback to Google Custom Search
        if self.config.google_api_key and self.config.google_cse_id:
            results = await self._search_google(query, max_results)
            if results:
                return results

        return []

    async def fetch_content(self, url: str) -> SourceContent | None:
        """Fetch and extract content from a URL."""
        try:
            import aiohttp
            import trafilatura

            async with aiohttp.ClientSession(headers=_HEADERS) as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=20),
                    allow_redirects=True,
                    ssl=False,
                ) as resp:
                    if resp.status != 200:
                        return None
                    html = await resp.text()

            text = trafilatura.extract(
                html,
                include_links=True,
                include_comments=False,
                include_tables=True,
                favor_recall=True,
            )

            if not text:
                return None

            # Extract title from HTML
            import re
            title_match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else url

            if len(text) > 8000:
                text = text[:8000] + "\n\n[Content truncated...]"

            return SourceContent(
                url=url,
                title=title,
                text=text,
                source_provider=self.name,
                trust_score=self.base_trust_score,
            )
        except Exception as e:
            logger.warning("Failed to fetch content from %s: %s", url, e)
            return None

    async def _search_tavily(self, query: str, max_results: int) -> list[SourceResult]:
        """Search using Tavily API."""
        try:
            from tavily import TavilyClient

            client = TavilyClient(api_key=self.config.tavily_api_key)
            response = client.search(
                query=query,
                max_results=max_results,
                search_depth="advanced",
            )

            results = []
            for r in response.get("results", []):
                pub_date = None
                if r.get("published_date"):
                    try:
                        pub_date = datetime.fromisoformat(r["published_date"].replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        pass

                results.append(SourceResult(
                    url=r.get("url", ""),
                    title=r.get("title", ""),
                    snippet=r.get("content", "")[:500],
                    source_provider="tavily",
                    published_at=pub_date,
                    trust_score=r.get("score", 0.5),
                ))
            return results
        except ImportError:
            logger.debug("Tavily not installed")
            return []
        except Exception as e:
            logger.warning("Tavily search failed: %s", e)
            return []

    async def _search_ddgs(self, query: str, max_results: int) -> list[SourceResult]:
        """Search using DuckDuckGo."""
        try:
            from ddgs import DDGS

            results_raw = DDGS().text(query, max_results=max_results)
            results = []
            for r in results_raw:
                results.append(SourceResult(
                    url=r.get("href", ""),
                    title=r.get("title", ""),
                    snippet=r.get("body", ""),
                    source_provider="ddgs",
                    trust_score=0.5,
                ))
            return results
        except Exception as e:
            logger.warning("DDGS search failed: %s", e)
            return []

    async def _search_google(self, query: str, max_results: int) -> list[SourceResult]:
        """Search using Google Custom Search API."""
        try:
            import aiohttp

            url = (
                f"https://www.googleapis.com/customsearch/v1"
                f"?key={self.config.google_api_key}"
                f"&cx={self.config.google_cse_id}"
                f"&q={query}"
                f"&num={max_results}"
            )

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()

            results = []
            for item in data.get("items", []):
                results.append(SourceResult(
                    url=item.get("link", ""),
                    title=item.get("title", ""),
                    snippet=item.get("snippet", ""),
                    source_provider="google_cse",
                    trust_score=0.6,
                ))
            return results
        except Exception as e:
            logger.warning("Google CSE search failed: %s", e)
            return []
