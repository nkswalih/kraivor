"""Community provider — StackOverflow + Reddit."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import aiohttp

from app.knowledge_engine.sources.base import SourceResult, SourceContent

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "Kraivor-AI/1.0 (knowledge-retrieval)",
}


class CommunityProvider:
    """Community sources: StackOverflow and Reddit."""

    name = "community"
    base_trust_score = 0.60

    async def search(self, query: str, max_results: int = 5) -> list[SourceResult]:
        """Search community sources."""
        results = []
        half = max_results // 2
        results.extend(await self._search_stackoverflow(query, half))
        results.extend(await self._search_reddit(query, max_results - len(results)))
        return results[:max_results]

    async def fetch_content(self, url: str) -> SourceContent | None:
        """Fetch community post content."""
        if "stackoverflow.com" in url:
            return await self._fetch_stackoverflow(url)
        if "reddit.com" in url or "redd.it" in url:
            return await self._fetch_reddit(url)
        return None

    async def _search_stackoverflow(self, query: str, max_results: int) -> list[SourceResult]:
        """Search StackOverflow via API."""
        try:
            url = "https://api.stackexchange.com/2.3/search/advanced"
            params = {
                "order": "desc",
                "sort": "relevance",
                "q": query,
                "site": "stackoverflow",
                "pagesize": max_results,
                "filter": "withbody",
            }

            async with aiohttp.ClientSession(headers=_HEADERS) as session:
                async with session.get(
                    url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()

            results = []
            for item in data.get("items", [])[:max_results]:
                pub_date = None
                if item.get("creation_date"):
                    try:
                        pub_date = datetime.fromtimestamp(item["creation_date"], tz=UTC)
                    except (ValueError, TypeError):
                        pass

                results.append(SourceResult(
                    url=item.get("link", ""),
                    title=item.get("title", ""),
                    snippet=item.get("body_markdown", "")[:500] if item.get("body_markdown") else "",
                    source_provider="stackoverflow",
                    published_at=pub_date,
                    trust_score=0.70,
                    metadata={
                        "score": item.get("score", 0),
                        "answer_count": item.get("answer_count", 0),
                        "tags": item.get("tags", []),
                    },
                ))

            return results
        except Exception as e:
            logger.warning("StackOverflow search failed: %s", e)
            return []

    async def _search_reddit(self, query: str, max_results: int) -> list[SourceResult]:
        """Search Reddit via public JSON API."""
        try:
            url = f"https://www.reddit.com/search.json"
            params = {
                "q": query,
                "limit": max_results,
                "sort": "relevance",
                "t": "year",
            }

            async with aiohttp.ClientSession(headers=_HEADERS) as session:
                async with session.get(
                    url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()

            results = []
            for child in data.get("data", {}).get("children", [])[:max_results]:
                post = child.get("data", {})
                pub_date = None
                if post.get("created_utc"):
                    try:
                        pub_date = datetime.fromtimestamp(post["created_utc"], tz=UTC)
                    except (ValueError, TypeError):
                        pass

                results.append(SourceResult(
                    url=f"https://reddit.com{post.get('permalink', '')}",
                    title=post.get("title", ""),
                    snippet=post.get("selftext", "")[:500],
                    source_provider="reddit",
                    published_at=pub_date,
                    trust_score=0.50,
                    metadata={
                        "subreddit": post.get("subreddit", ""),
                        "score": post.get("score", 0),
                        "num_comments": post.get("num_comments", 0),
                    },
                ))

            return results
        except Exception as e:
            logger.warning("Reddit search failed: %s", e)
            return []

    async def _fetch_stackoverflow(self, url: str) -> SourceContent | None:
        """Fetch StackOverflow question/answer."""
        try:
            import trafilatura

            async with aiohttp.ClientSession(headers=_HEADERS) as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=15),
                    ssl=False,
                ) as resp:
                    if resp.status != 200:
                        return None
                    html = await resp.text()

            text = trafilatura.extract(html, include_links=True, include_tables=True)
            if not text:
                return None

            import re
            title_match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else url

            if len(text) > 8000:
                text = text[:8000] + "\n\n[Content truncated...]"

            return SourceContent(
                url=url,
                title=title,
                text=text,
                source_provider="stackoverflow",
                trust_score=0.70,
            )
        except Exception as e:
            logger.warning("StackOverflow fetch failed: %s", e)
            return None

    async def _fetch_reddit(self, url: str) -> SourceContent | None:
        """Fetch Reddit post content."""
        try:
            # Add .json to get JSON version
            json_url = url.rstrip("/") + ".json"
            async with aiohttp.ClientSession(headers=_HEADERS) as session:
                async with session.get(
                    json_url,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()

            post = data[0]["data"]["children"][0]["data"]
            title = post.get("title", "")
            selftext = post.get("selftext", "")

            if not selftext:
                selftext = "No text content (link post)"

            content = f"# {title}\n\n{selftext}"

            # Add top comments
            comments = data[1]["data"]["children"][:5]
            if comments:
                content += "\n\n## Top Comments\n\n"
                for c in comments:
                    if c.get("data", {}).get("body"):
                        content += f"- {c['data']['body'][:300]}\n\n"

            if len(content) > 8000:
                content = content[:8000] + "\n\n[Content truncated...]"

            return SourceContent(
                url=url,
                title=title,
                text=content,
                source_provider="reddit",
                trust_score=0.50,
            )
        except Exception as e:
            logger.warning("Reddit fetch failed: %s", e)
            return None
