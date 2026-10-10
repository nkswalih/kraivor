"""Web search tool using DDGS (DuckDuckGo) with news support."""

import asyncio
import logging
from datetime import datetime

from app.application.tools.base import BaseTool

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2
_RETRY_BACKOFF = [0.5, 2.0]


class DuckDuckGoSearchTool(BaseTool):
    name = "web_search"
    description = "Search the web using DuckDuckGo"

    async def run(
        self,
        query: str,
        max_results: int = 5,
        region: str = "wt-wt",
        timelimit: str | None = None,
    ) -> str:
        last_error = None
        for attempt in range(_MAX_RETRIES):
            try:
                from ddgs import DDGS

                # Fix B: Run synchronous DDGS call in a thread to avoid blocking the event loop.
                results = await asyncio.to_thread(DDGS().text, query, max_results=max_results, region=region)
                if not results:
                    return "No results found for your query."

                lines = [f"## Search Results for: {query}", ""]
                for i, r in enumerate(results, 1):
                    title = r.get("title", "No title")
                    url = r.get("href", r.get("link", ""))
                    body = r.get("body", r.get("snippet", ""))
                    lines.append(f"### {i}. {title}")
                    lines.append(f"**URL:** {url}")
                    lines.append(f"{body}")
                    lines.append("")

                return "\n".join(lines)
            except ImportError:
                return "DDGS search not available (pip install ddgs)"
            except Exception as e:
                last_error = e
                logger.warning("DDGS search attempt %d failed: %s", attempt + 1, e)
                if attempt < _MAX_RETRIES - 1:
                    await asyncio.sleep(_RETRY_BACKOFF[attempt])

        return f"SEARCH_UNAVAILABLE: Web search failed after {_MAX_RETRIES} attempts — {last_error}"


class DuckDuckGoNewsTool(BaseTool):
    name = "web_search_news"
    description = "Search for recent news using DuckDuckGo News"

    async def run(
        self,
        query: str,
        max_results: int = 5,
        timelimit: str = "d",
    ) -> str:
        last_error = None
        for attempt in range(_MAX_RETRIES):
            try:
                from ddgs import DDGS

                results = await asyncio.to_thread(DDGS().news, query, max_results=max_results, timelimit=timelimit)
                if not results:
                    return "No recent news found for your query."

                lines = [f"## Recent News for: {query}", ""]
                for i, r in enumerate(results, 1):
                    title = r.get("title", "No title")
                    url = r.get("url", r.get("link", ""))
                    source = r.get("source", "Unknown")
                    date = r.get("date", "")
                    body = r.get("body", r.get("snippet", ""))

                    if date:
                        try:
                            if isinstance(date, str):
                                dt = datetime.fromisoformat(date.replace("Z", "+00:00"))
                                date_str = dt.strftime("%B %d, %Y %H:%M")
                            else:
                                date_str = str(date)
                        except (ValueError, TypeError):
                            date_str = str(date)
                    else:
                        date_str = "Unknown date"

                    lines.append(f"### {i}. {title}")
                    lines.append(f"**Source:** {source} | **Date:** {date_str}")
                    lines.append(f"**URL:** {url}")
                    lines.append(f"{body}")
                    lines.append("")

                return "\n".join(lines)
            except ImportError:
                return "DDGS News not available (pip install ddgs)"
            except Exception as e:
                last_error = e
                logger.warning("DDGS News attempt %d failed: %s", attempt + 1, e)
                if attempt < _MAX_RETRIES - 1:
                    await asyncio.sleep(_RETRY_BACKOFF[attempt])

        return f"SEARCH_UNAVAILABLE: News search failed after {_MAX_RETRIES} attempts — {last_error}"


class DuckDuckGoInstantTool(BaseTool):
    name = "web_search_instant"
    description = "Get instant answers from DuckDuckGo (calculations, conversions, definitions, etc.)"

    async def run(self, query: str) -> str:
        try:
            from ddgs import DDGS

            # Fix B: Run synchronous DDGS call in a thread to avoid blocking the event loop.
            results = await asyncio.to_thread(DDGS().answers, query)
            if not results:
                return "No instant answer found for your query."

            lines = [f"## Instant Answer for: {query}", ""]
            for r in results:
                text = r.get("text", "")
                source = r.get("source", "")
                if text:
                    lines.append(f"**Answer:** {text}")
                if source:
                    lines.append(f"**Source:** {source}")
                lines.append("")

            return "\n".join(lines) if len(lines) > 2 else "No instant answer found."
        except ImportError:
            return "DDGS instant answers not available (pip install ddgs)"
        except Exception as e:
            logger.error("DDGS instant answer failed: %s", e)
            return f"Instant answer failed: {e}"
