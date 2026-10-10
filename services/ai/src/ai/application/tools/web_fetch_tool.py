"""Web fetch tool using trafilatura for clean content extraction."""

import logging
import re

import aiohttp
import trafilatura

from app.application.tools.base import BaseTool
from app.core.url_guard import (
    MAX_REDIRECT_HOPS,
    REDIRECT_STATUSES,
    UnsafeURLError,
    assert_safe_url,
    resolve_redirect,
)

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

_TIMEOUT = aiohttp.ClientTimeout(total=20)
_MAX_CHARS = 8000

_SCRIPT_OR_STYLE = re.compile(
    r"<(script|style)\b[^>]*>.*?</\1\s*>", re.IGNORECASE | re.DOTALL
)
_HTML_TAG = re.compile(r"<[^>]+>")
_WHITESPACE = re.compile(r"\s+")

_WEB_EXTRACT = {
    "include_links": True,
    "include_comments": False,
    "include_tables": True,
    "favor_precision": False,
    "favor_recall": True,
}

_NEWS_EXTRACT = {
    "include_links": True,
    "include_comments": False,
    "include_tables": False,
    "favor_precision": True,
    "favor_recall": False,
}


def _strip_html(html: str) -> str:
    """Strip script/style blocks and tags from HTML.

    The pattern is case-insensitive and tolerates whitespace before the
    closing ``>`` so that ``<SCRIPT>`` and ``</script >`` are removed
    rather than passed through to the model as text.
    """
    text = _SCRIPT_OR_STYLE.sub("", html)
    text = _HTML_TAG.sub(" ", text)
    return _WHITESPACE.sub(" ", text).strip()


async def _get_once(
    session: aiohttp.ClientSession, url: str
) -> tuple[int, str | None, str]:
    """One GET with redirects disabled.

    Returns the status, the raw ``Location`` header, and the body. Keeping
    this to a single request is what lets the caller decide what to do
    with a redirect before anything is fetched from the target.
    """
    async with session.get(url, timeout=_TIMEOUT, allow_redirects=False) as resp:
        return resp.status, resp.headers.get("Location"), await resp.text()


async def _read_page(url: str, extract: dict, empty_message: str) -> str:
    """Fetch ``url`` and return its readable text, or a refusal message.

    Redirect following is disabled on every request and re-implemented
    here so each hop is validated. aiohttp would otherwise follow a
    ``Location`` to whatever the first host names, and ``assert_safe_url``
    on the initial URL cannot see that coming: a public host answering
    ``302`` with ``Location: http://169.254.169.254/`` puts the next
    request on the cloud metadata service, and the body would then be
    handed to the model as page text.
    """
    try:
        assert_safe_url(url)
    except UnsafeURLError as e:
        return f"Refused to fetch {url}: {e}"

    try:
        async with aiohttp.ClientSession(headers=_HEADERS) as session:
            current = url
            hops = 0
            status, location, body = await _get_once(session, current)
            while status in REDIRECT_STATUSES:
                if hops >= MAX_REDIRECT_HOPS:
                    logger.warning("Too many redirects fetching %s", url)
                    return (
                        f"Too many redirects fetching {url} "
                        f"(limit {MAX_REDIRECT_HOPS})"
                    )
                try:
                    current = resolve_redirect(current, location)
                except UnsafeURLError as e:
                    logger.warning("Refused unsafe redirect %s: %s", current, e)
                    return f"Refused to follow a redirect from {url}: {e}"
                hops += 1
                status, location, body = await _get_once(session, current)

            if status != 200:
                return f"HTTP {status} fetching {url}"
            html = body
    except aiohttp.ClientError as e:
        return f"Network error fetching {url}: {e}"
    except UnsafeURLError as e:
        return f"Refused to fetch {url}: {e}"
    except Exception as e:
        return f"Failed to fetch {url}: {e}"

    try:
        text = trafilatura.extract(html, **extract)
    except Exception:
        text = None

    if not text:
        text = _strip_html(html)

    if len(text) > _MAX_CHARS:
        text = text[:_MAX_CHARS] + "\n\n[Content truncated...]"

    return text if text else empty_message


class WebFetchTool(BaseTool):
    name = "web_fetch"
    description = "Fetch and extract clean text content from a URL"

    async def run(self, url: str, extract_mode: str = "text") -> str:
        return await _read_page(
            url, _WEB_EXTRACT, "No readable content found on this page."
        )


class NewsFetchTool(BaseTool):
    name = "news_fetch"
    description = "Fetch news articles from a URL"

    async def run(self, url: str) -> str:
        return await _read_page(url, _NEWS_EXTRACT, "No article content found.")
