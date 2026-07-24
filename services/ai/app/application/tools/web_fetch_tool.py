"""Web fetch tool using trafilatura for clean content extraction."""

import logging

import aiohttp
import trafilatura

from app.application.tools.base import BaseTool

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
}

_MAX_CHARS = 8000


class WebFetchTool(BaseTool):
    name = "web_fetch"
    description = "Fetch and extract clean text content from a URL"

    async def run(self, url: str, extract_mode: str = "text") -> str:
        try:
            async with aiohttp.ClientSession(headers=_HEADERS) as session, session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=20),
                allow_redirects=True,
            ) as resp:
                if resp.status != 200:
                    return f"HTTP {resp.status} fetching {url}"
                html = await resp.text()
        except aiohttp.ClientError as e:
            return f"Network error fetching {url}: {e}"
        except Exception as e:
            return f"Failed to fetch {url}: {e}"

        # Use trafilatura to extract main content
        try:
            text = trafilatura.extract(
                html,
                include_links=True,
                include_comments=False,
                include_tables=True,
                favor_precision=False,
                favor_recall=True,
            )
        except Exception:
            text = None

        if not text:
            # Fallback: basic HTML stripping
            import re

            text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
            text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()

        if len(text) > _MAX_CHARS:
            text = text[:_MAX_CHARS] + "\n\n[Content truncated...]"

        return text if text else "No readable content found on this page."


class NewsFetchTool(BaseTool):
    name = "news_fetch"
    description = "Fetch news articles from a URL"

    async def run(self, url: str) -> str:
        try:
            async with aiohttp.ClientSession(headers=_HEADERS) as session, session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=20),
                allow_redirects=True,
            ) as resp:
                if resp.status != 200:
                    return f"HTTP {resp.status} fetching {url}"
                html = await resp.text()
        except aiohttp.ClientError as e:
            return f"Network error fetching {url}: {e}"
        except Exception as e:
            return f"Failed to fetch {url}: {e}"

        try:
            text = trafilatura.extract(
                html,
                include_links=True,
                include_comments=False,
                include_tables=False,
                favor_precision=True,
                favor_recall=False,
            )
        except Exception:
            text = None

        if not text:
            import re

            text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
            text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()

        if len(text) > _MAX_CHARS:
            text = text[:_MAX_CHARS] + "\n\n[Content truncated...]"

        return text if text else "No article content found."
