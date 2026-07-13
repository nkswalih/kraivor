"""Package registry provider — PyPI + npm metadata."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import aiohttp

from app.knowledge_engine.sources.base import SourceResult, SourceContent

logger = logging.getLogger(__name__)


class PackageRegistryProvider:
    """Package registry search and metadata for PyPI and npm."""

    name = "package_registries"
    base_trust_score = 0.85

    async def search(self, query: str, max_results: int = 5) -> list[SourceResult]:
        """Search for packages across registries."""
        results = []
        results.extend(await self._search_pypi(query, max_results))
        results.extend(await self._search_npm(query, max_results))
        return results[:max_results]

    async def fetch_content(self, url: str) -> SourceContent | None:
        """Fetch package metadata."""
        if "pypi.org" in url or "pypi" in url:
            return await self._fetch_pypi(url)
        if "npmjs.com" in url:
            return await self._fetch_npm(url)
        return None

    async def _search_pypi(self, query: str, max_results: int) -> list[SourceResult]:
        """Search PyPI."""
        try:
            url = f"https://pypi.org/simple/{query}"
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://pypi.org/search/?q={query}",
                    timeout=aiohttp.ClientTimeout(total=10),
                    headers={"Accept": "application/json"},
                ) as resp:
                    if resp.status != 200:
                        return []

            # Use PyPI JSON API for specific packages
            api_url = f"https://pypi.org/pypi/{query}/json"
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    api_url,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        info = data.get("info", {})
                        return [SourceResult(
                            url=f"https://pypi.org/project/{info.get('name', query)}/",
                            title=f"PyPI: {info.get('name', query)}",
                            snippet=info.get("summary", "")[:500],
                            source_provider="pypi",
                            trust_score=0.85,
                        )]
            return []
        except Exception as e:
            logger.warning("PyPI search failed: %s", e)
            return []

    async def _search_npm(self, query: str, max_results: int) -> list[SourceResult]:
        """Search npm registry."""
        try:
            url = f"https://registry.npmjs.org/-/v1/search?text={query}&size={max_results}"
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()

            results = []
            for pkg in data.get("objects", [])[:max_results]:
                p = pkg.get("package", {})
                results.append(SourceResult(
                    url=f"https://www.npmjs.com/package/{p.get('name', '')}",
                    title=f"npm: {p.get('name', '')}",
                    snippet=(p.get("description") or "")[:500],
                    source_provider="npm",
                    trust_score=0.85,
                ))
            return results
        except Exception as e:
            logger.warning("npm search failed: %s", e)
            return []

    async def _fetch_pypi(self, url: str) -> SourceContent | None:
        """Fetch PyPI package metadata."""
        import re
        match = re.search(r"/project/(.+?)/", url)
        if not match:
            return None
        package_name = match.group(1)

        try:
            api_url = f"https://pypi.org/pypi/{package_name}/json"
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    api_url,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()

            info = data.get("info", {})
            content = f"# {info.get('name', package_name)}\n\n"
            content += f"**Version:** {info.get('version', 'N/A')}\n"
            content += f"**Summary:** {info.get('summary', 'N/A')}\n"
            content += f"**Author:** {info.get('author', info.get('author_email', 'N/A'))}\n"
            content += f"**License:** {info.get('license', 'N/A')}\n"
            content += f"**Home Page:** {info.get('home_page', 'N/A')}\n\n"

            if info.get("description"):
                desc = info["description"][:5000]
                content += f"## Description\n\n{desc}"

            return SourceContent(
                url=url,
                title=f"PyPI: {info.get('name', package_name)}",
                text=content,
                source_provider="pypi",
                trust_score=0.85,
            )
        except Exception as e:
            logger.warning("PyPI fetch failed: %s", e)
            return None

    async def _fetch_npm(self, url: str) -> SourceContent | None:
        """Fetch npm package metadata."""
        import re
        match = re.search(r"/package/(.+?)(?:\?|$)", url)
        if not match:
            return None
        package_name = match.group(1)

        try:
            api_url = f"https://registry.npmjs.org/{package_name}"
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    api_url,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()

            latest_version = data.get("dist-tags", {}).get("latest", "")
            latest_data = data.get("versions", {}).get(latest_version, {})
            content = f"# {package_name}\n\n"
            content += f"**Latest Version:** {latest_version}\n"
            content += f"**Description:** {data.get('description', 'N/A')}\n"
            content += f"**License:** {latest_data.get('license', 'N/A')}\n"
            content += f"**Keywords:** {', '.join(data.get('keywords', [])[:10])}\n"

            readme = data.get("readme", "")
            if readme:
                content += f"\n## README\n\n{readme[:5000]}"

            return SourceContent(
                url=url,
                title=f"npm: {package_name}",
                text=content,
                source_provider="npm",
                trust_score=0.85,
            )
        except Exception as e:
            logger.warning("npm fetch failed: %s", e)
            return None
