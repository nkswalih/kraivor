"""Web fetch tool using trafilatura for clean content extraction."""

import logging
import re

import aiohttp
import trafilatura

from app.application.tools.base import BaseTool
from app.core.url_guard import UnsafeURLError, assert_safe_url

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

_SCRIPT_OR_STYLE = re.compile(
    r"<(script|style)\b[^>]*>.*?</\1\s*>",
    re.IGNORECASE | re.DOTALL,
)
_HTML_TAG = re.compile(r"<[^>]+>")
_WHITESPACE = re.compile(r"\s+")


def _strip_html(html: str) -> str:
    """Strip script/style blocks and tags from HTML.

    The pattern is case-insensitive and tolerates whitespace before the
    closing ``>`` so that ``<SCRIPT>`` and ``</script >`` are removed
    rather than passed through to the model as text.
    """
    text = _SCRIPT_OR_STYLE.sub("", html)
    text = _HTML_TAG.sub(" ", text)
    return _WHITESPACE.sub(" ", text).strip()


class WebFetchTool(BaseTool):
    name = "web_fetch"
    description = "Fetch and extract clean text content from a URL"

    async def run(self, url: str, extract_mode: str = "text") -> str:
        try:
            assert_safe_url(url)
        except UnsafeURLError as e:
            return f"Refused to fetch {url}: {e}"

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
            text = _strip_html(html)

        if len(text) > _MAX_CHARS:
            text = text[:_MAX_CHARS] + "\n\n[Content truncated...]"

        return text if text else "No readable content found on this page."


class NewsFetchTool(BaseTool):
    name = "news_fetch"
    description = "Fetch news articles from a URL"

    async def run(self, url: str) -> str:
        try:
            assert_safe_url(url)
        except UnsafeURLError as e:
            return f"Refused to fetch {url}: {e}"

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
            text = _strip_html(html)

        if len(text) > _MAX_CHARS:
            text = text[:_MAX_CHARS] + "\n\n[Content truncated...]"

        return text if text else "No article content found."
