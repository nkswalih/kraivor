"""Research paper provider — ArXiv + Semantic Scholar."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from xml.etree import ElementTree as ET

import aiohttp

from app.knowledge_engine.sources.base import SourceResult, SourceContent
import contextlib

logger = logging.getLogger(__name__)

_ARXIV_API = "http://export.arxiv.org/api/query"
_SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1"


class ResearchPaperProvider:
    """Research paper search via ArXiv and Semantic Scholar."""

    name = "research_papers"
    base_trust_score = 0.85

    async def search(self, query: str, max_results: int = 5) -> list[SourceResult]:
        """Search for research papers."""
        results = await self._search_arxiv(query, max_results)
        if len(results) < max_results:
            more = await self._search_semantic_scholar(query, max_results - len(results))
            results.extend(more)
        return results[:max_results]

    async def fetch_content(self, url: str) -> SourceContent | None:
        """Fetch paper abstract and metadata."""
        if "arxiv.org" in url:
            return await self._fetch_arxiv(url)
        if "semanticscholar.org" in url:
            return await self._fetch_semantic_scholar(url)
        return None

    async def _search_arxiv(self, query: str, max_results: int) -> list[SourceResult]:
        """Search ArXiv API."""
        try:
            params = {
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": max_results,
                "sortBy": "relevance",
                "sortOrder": "descending",
            }

            async with aiohttp.ClientSession() as session, session.get(
                _ARXIV_API,
                params=params,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    return []
                xml_text = await resp.text()

            root = ET.fromstring(xml_text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}

            results = []
            for entry in root.findall("atom:entry", ns):
                title = entry.findtext("atom:title", "", ns).strip().replace("\n", " ")
                summary = entry.findtext("atom:summary", "", ns).strip().replace("\n", " ")
                link = entry.findtext("atom:id", "", ns).strip()

                # Extract authors
                authors = []
                for author in entry.findall("atom:author", ns):
                    name = author.findtext("atom:name", "", ns)
                    if name:
                        authors.append(name)

                # Published date
                pub_date_str = entry.findtext("atom:published", "", ns)
                pub_date = None
                if pub_date_str:
                    with contextlib.suppress(ValueError, TypeError):
                        pub_date = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))

                results.append(SourceResult(
                    url=link,
                    title=title,
                    snippet=summary[:500],
                    source_provider="arxiv",
                    published_at=pub_date,
                    author=", ".join(authors[:3]),
                    trust_score=self.base_trust_score,
                ))

            return results
        except Exception as e:
            logger.warning("ArXiv search failed: %s", e)
            return []

    async def _search_semantic_scholar(self, query: str, max_results: int) -> list[SourceResult]:
        """Search Semantic Scholar API."""
        try:
            url = f"{_SEMANTIC_SCHOLAR_API}/paper/search"
            params = {
                "query": query,
                "limit": max_results,
                "fields": "title,abstract,url,year,authors,citationCount",
            }

            async with aiohttp.ClientSession() as session, session.get(
                url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()

            results = []
            for paper in data.get("data", []):
                authors = [a.get("name", "") for a in paper.get("authors", [])]
                results.append(SourceResult(
                    url=paper.get("url", ""),
                    title=paper.get("title", ""),
                    snippet=(paper.get("abstract") or "")[:500],
                    source_provider="semantic_scholar",
                    author=", ".join(authors[:3]),
                    trust_score=0.85,
                    metadata={"citations": paper.get("citationCount", 0)},
                ))

            return results
        except Exception as e:
            logger.warning("Semantic Scholar search failed: %s", e)
            return []

    async def _fetch_arxiv(self, url: str) -> SourceContent | None:
        """Fetch ArXiv paper details."""
        # Extract paper ID from URL
        match = re.search(r"(\d{4}\.\d{4,5})(v\d+)?$", url)
        if not match:
            return None
        paper_id = match.group(1)

        try:
            api_url = f"{_ARXIV_API}?id_list={paper_id}"
            async with aiohttp.ClientSession() as session, session.get(
                api_url,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    return None
                xml_text = await resp.text()

            root = ET.fromstring(xml_text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            entry = root.find("atom:entry", ns)
            if entry is None:
                return None

            title = entry.findtext("atom:title", "", ns).strip().replace("\n", " ")
            summary = entry.findtext("atom:summary", "", ns).strip().replace("\n", " ")

            if len(summary) > 8000:
                summary = summary[:8000]

            return SourceContent(
                url=url,
                title=title,
                text=summary,
                source_provider="arxiv",
                trust_score=self.base_trust_score,
            )
        except Exception as e:
            logger.warning("ArXiv fetch failed: %s", e)
            return None

    async def _fetch_semantic_scholar(self, url: str) -> SourceContent | None:
        """Fetch Semantic Scholar paper details."""
        # Extract paper ID
        match = re.search(r"/paper/(.+?)(?:\?|$)", url)
        if not match:
            return None
        paper_id = match.group(1)

        try:
            api_url = f"{_SEMANTIC_SCHOLAR_API}/paper/{paper_id}"
            params = {"fields": "title,abstract,url,year,authors,citationCount,tldr"}

            async with aiohttp.ClientSession() as session, session.get(
                api_url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()

            title = data.get("title", "")
            abstract = data.get("abstract") or ""
            tldr = data.get("tldr", {}).get("text", "") if data.get("tldr") else ""

            content = f"## {title}\n\n"
            if tldr:
                content += f"**TL;DR:** {tldr}\n\n"
            content += f"**Abstract:** {abstract}"

            if len(content) > 8000:
                content = content[:8000]

            return SourceContent(
                url=url,
                title=title,
                text=content,
                source_provider="semantic_scholar",
                trust_score=0.85,
            )
        except Exception as e:
            logger.warning("Semantic Scholar fetch failed: %s", e)
            return None
