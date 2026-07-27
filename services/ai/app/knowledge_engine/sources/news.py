"""News provider — DDGS News + Google News RSS."""

from __future__ import annotations

import logging
from datetime import datetime
from xml.etree import ElementTree as ET

import aiohttp

from app.knowledge_engine.sources.base import SourceResult, SourceContent
import contextlib

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
}


class NewsProvider:
    """News search provider using DDGS News and Google News RSS."""

    name = "news"
    base_trust_score = 0.65

    async def search(self, query: str, max_results: int = 5) -> list[SourceResult]:
        """Search for recent news."""
        # Try DDGS News first
        results = await self._search_ddgs_news(query, max_results)
        if results:
            return results

        # Fallback to Google News RSS
        return await self._search_google_news(query, max_results)

    async def fetch_content(self, url: str) -> SourceContent | None:
        """Fetch news article content."""
        try:
            import trafilatura

            async with aiohttp.ClientSession(headers=_HEADERS) as session, session.get(
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
                include_tables=False,
                favor_precision=True,
            )

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
                source_provider=self.name,
                trust_score=self.base_trust_score,
            )
        except Exception as e:
            logger.warning("Failed to fetch news from %s: %s", url, e)
            return None

    async def _search_ddgs_news(self, query: str, max_results: int) -> list[SourceResult]:
        """Search using DDGS News."""
        try:
            from ddgs import DDGS

            results_raw = DDGS().news(query, max_results=max_results, timelimit="w")
            results = []
            for r in results_raw:
                pub_date = None
                if r.get("date"):
                    with contextlib.suppress(ValueError, TypeError):
                        pub_date = datetime.fromisoformat(str(r["date"]).replace("Z", "+00:00"))

                results.append(SourceResult(
                    url=r.get("url", ""),
                    title=r.get("title", ""),
                    snippet=r.get("body", "")[:500],
                    source_provider=f"news_{r.get('source', 'ddgs').lower().replace(' ', '_')}",
                    published_at=pub_date,
                    trust_score=0.65,
                ))
            return results
        except Exception as e:
            logger.warning("DDGS News search failed: %s", e)
            return []

    async def _search_google_news(self, query: str, max_results: int) -> list[SourceResult]:
        """Search using Google News RSS feed."""
        try:
            url = (
                f"https://news.google.com/rss/search"
                f"?q={query}"
                f"&hl=en-US"
                f"&gl=US"
                f"&ceid=US:en"
            )

            async with aiohttp.ClientSession(headers=_HEADERS) as session, session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    return []
                xml_text = await resp.text()

            # Parse RSS
            root = ET.fromstring(xml_text)
            items = root.findall(".//item")[:max_results]

            results = []
            for item in items:
                title = item.findtext("title", "")
                link = item.findtext("link", "")
                pub_date_str = item.findtext("pubDate", "")
                source_name = item.findtext("source", "Google News")

                pub_date = None
                if pub_date_str:
                    try:
                        from email.utils import parsedate_to_datetime
                        pub_date = parsedate_to_datetime(pub_date_str)
                    except (ValueError, TypeError):
                        pass

                results.append(SourceResult(
                    url=link,
                    title=title,
                    snippet=f"Source: {source_name}",
                    source_provider=f"news_{source_name.lower().replace(' ', '_')}",
                    published_at=pub_date,
                    trust_score=0.60,
                ))

            return results
        except Exception as e:
            logger.warning("Google News RSS failed: %s", e)
            return []
