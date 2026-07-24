"""Proactive Learning Agent — monitors tech feeds and auto-indexes relevant knowledge.

Background workers that:
1. Monitor tech release feeds (GitHub trending, PyPI, npm)
2. Monitor documentation changes for tracked frameworks
3. Monitor security advisories for dependencies
4. Auto-index relevant updates into the knowledge base
5. Track what the workspace actually uses (from code, imports, configs)
"""

from __future__ import annotations

import logging
import re

from sqlalchemy import text

from app.infrastructure.db.database import async_session_factory

logger = logging.getLogger(__name__)


# ── Feed Monitors ────────────────────────────────────────────────────────────


class TechReleaseMonitor:
    """Monitors releases for technologies the workspace uses."""

    # Curated feeds for popular technologies
    FEEDS = {
        "python": {
            "pypi": "https://pypi.org/rss/packages/top.xml",
            "docs": "https://docs.python.org/3/whatsnew/",
        },
        "django": {
            "releases": "https://www.djangoproject.com/weblog/?feed=rss",
            "security": "https://www.djangoproject.com/weblog/?feed=rss&category=security",
        },
        "fastapi": {
            "releases": "https://github.com/fastapi/fastapi/releases.atom",
        },
        "react": {
            "releases": "https://github.com/facebook/react/releases.atom",
        },
        "node": {
            "releases": "https://nodejs.org/en/feed/release.xml",
        },
    }

    async def check_workspace_technologies(
        self, workspace_id: str
    ) -> list[str]:
        """Get technologies used in a workspace by analyzing code and dependencies."""
        async with async_session_factory() as session:
            # Check code embeddings for technology mentions
            result = await session.execute(text("""
                SELECT DISTINCT
                    CASE
                        WHEN content ILIKE '%django%' THEN 'django'
                        WHEN content ILIKE '%fastapi%' THEN 'fastapi'
                        WHEN content ILIKE '%flask%' THEN 'flask'
                        WHEN content ILIKE '%react%' THEN 'react'
                        WHEN content ILIKE '%vue%' THEN 'vue'
                        WHEN content ILIKE '%angular%' THEN 'angular'
                        WHEN content ILIKE '%nextjs%' OR content ILIKE '%next.js%' THEN 'nextjs'
                        WHEN content ILIKE '%docker%' THEN 'docker'
                        WHEN content ILIKE '%kubernetes%' OR content ILIKE '%k8s%' THEN 'kubernetes'
                        WHEN content ILIKE '%celery%' THEN 'celery'
                        WHEN content ILIKE '%redis%' THEN 'redis'
                        WHEN content ILIKE '%postgresql%' OR content ILIKE '%postgres%' THEN 'postgresql'
                        WHEN content ILIKE '%mongodb%' THEN 'mongodb'
                    END AS technology
                FROM ai.knowledge_embeddings
                WHERE workspace_id = :ws
                  AND content IS NOT NULL
            """), {"ws": workspace_id})
            rows = result.fetchall()

        techs = [row.technology for row in rows if row.technology]
        return list(set(techs))

    async def get_latest_releases(
        self, technology: str, max_items: int = 3
    ) -> list[dict]:
        """Fetch latest releases for a technology from its feed."""
        import httpx

        feeds = self.FEEDS.get(technology, {})
        releases = []

        for feed_type, feed_url in feeds.items():
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(feed_url, headers={"User-Agent": "KraivorBot/1.0"})
                    if resp.status_code == 200:
                        # Simple XML parsing for RSS/Atom feeds
                        items = self._parse_feed(resp.text, feed_type)
                        releases.extend(items[:max_items])
            except Exception as e:
                logger.debug("Feed fetch failed for %s/%s: %s", technology, feed_type, e)
                continue

        return releases[:max_items]

    def _parse_feed(self, xml_text: str, feed_type: str) -> list[dict]:
        """Parse RSS/Atom feed items."""
        items = []

        # Extract titles and links from XML
        title_pattern = re.compile(r"<title[^>]*>(.*?)</title>", re.DOTALL)
        link_pattern = re.compile(r"<link[^>]*>(.*?)</link>", re.DOTALL)
        pub_pattern = re.compile(r"<pubDate[^>]*>(.*?)</pubDate>", re.DOTALL)

        titles = title_pattern.findall(xml_text)
        links = link_pattern.findall(xml_text)
        pubs = pub_pattern.findall(xml_text)

        for i in range(min(len(titles), len(links), 10)):
            title = re.sub(r"<[^>]+>", "", titles[i]).strip()
            link = re.sub(r"<[^>]+>", "", links[i]).strip()
            pub = pubs[i].strip() if i < len(pubs) else ""

            if title and link:
                items.append({
                    "title": title,
                    "url": link,
                    "published": pub,
                    "feed_type": feed_type,
                })

        return items


class SecurityAdvisoryMonitor:
    """Monitors security advisories for workspace dependencies."""

    async def check_advisories(
        self, workspace_id: str, technologies: list[str]
    ) -> list[dict]:
        """Check for security advisories affecting workspace technologies."""
        import httpx

        advisories = []

        # GitHub Advisory Database (public API, no auth needed for basic queries)
        for tech in technologies[:5]:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(
                        "https://api.github.com/advisories",
                        params={
                            "affects": tech,
                            "type": "reviewed",
                            "per_page": 3,
                        },
                        headers={
                            "Accept": "application/vnd.github+json",
                            "User-Agent": "KraivorBot/1.0",
                        },
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        for advisory in data.get("advisories", data if isinstance(data, list) else []):
                            if isinstance(advisory, dict):
                                advisories.append({
                                    "title": advisory.get("summary", advisory.get("title", "")),
                                    "severity": advisory.get("severity", "unknown"),
                                    "url": advisory.get("html_url", advisory.get("url", "")),
                                    "technology": tech,
                                    "published": advisory.get("published_at", ""),
                                })
            except Exception as e:
                logger.debug("Advisory check failed for %s: %s", tech, e)
                continue

        return advisories[:10]


class DocumentationChangeMonitor:
    """Monitors documentation pages for changes and re-indexes if needed."""

    async def check_docs_freshness(
        self, workspace_id: str
    ) -> list[dict]:
        """Find knowledge items that haven't been refreshed recently."""
        async with async_session_factory() as session:
            result = await session.execute(text("""
                SELECT id, source_url, title, fetched_at, source_trust_score
                FROM ai.knowledge_embeddings
                WHERE workspace_id = :ws
                  AND source_provider IN ('docs', 'web')
                  AND fetched_at < NOW() - INTERVAL '7 days'
                ORDER BY fetched_at ASC
                LIMIT 10
            """), {"ws": workspace_id})
            rows = result.fetchall()

        return [
            {
                "id": row.id,
                "url": row.source_url,
                "title": row.title,
                "fetched_at": row.fetched_at.isoformat() if row.fetched_at else None,
                "trust_score": row.source_trust_score,
            }
            for row in rows
        ]


# ── Learning Pipeline ────────────────────────────────────────────────────────


class ProactiveLearningPipeline:
    """Orchestrates proactive knowledge acquisition for a workspace."""

    def __init__(self):
        self.release_monitor = TechReleaseMonitor()
        self.security_monitor = SecurityAdvisoryMonitor()
        self.docs_monitor = DocumentationChangeMonitor()

    async def run_full_cycle(self, workspace_id: str) -> dict:
        """Run a complete learning cycle for a workspace.

        1. Detect technologies used
        2. Check for new releases
        3. Check for security advisories
        4. Check docs freshness
        5. Auto-index relevant updates
        """
        results = {
            "workspace_id": workspace_id,
            "technologies": [],
            "new_releases": 0,
            "security_advisories": 0,
            "stale_docs": 0,
            "items_indexed": 0,
        }

        # 1. Detect technologies
        techs = await self.release_monitor.check_workspace_technologies(workspace_id)
        results["technologies"] = techs
        logger.info("Workspace %s uses: %s", workspace_id, techs)

        # 2. Check releases
        for tech in techs[:5]:
            try:
                releases = await self.release_monitor.get_latest_releases(tech)
                for release in releases:
                    await self._index_release(workspace_id, tech, release)
                    results["new_releases"] += 1
                    results["items_indexed"] += 1
            except Exception as e:
                logger.debug("Release check failed for %s: %s", tech, e)

        # 3. Security advisories
        try:
            advisories = await self.security_monitor.check_advisories(workspace_id, techs)
            for adv in advisories:
                await self._index_advisory(workspace_id, adv)
                results["security_advisories"] += 1
                results["items_indexed"] += 1
        except Exception as e:
            logger.debug("Security check failed: %s", e)

        # 4. Stale docs
        try:
            stale = await self.docs_monitor.check_docs_freshness(workspace_id)
            results["stale_docs"] = len(stale)
        except Exception as e:
            logger.debug("Docs freshness check failed: %s", e)

        logger.info(
            "Learning cycle complete for %s: %d techs, %d releases, %d advisories, %d indexed",
            workspace_id, len(techs), results["new_releases"],
            results["security_advisories"], results["items_indexed"],
        )

        return results

    async def _index_release(self, workspace_id: str, technology: str, release: dict):
        """Index a technology release as knowledge."""
        from app.knowledge_engine.store.knowledge_indexer import KnowledgeIndexer

        indexer = KnowledgeIndexer()
        await indexer.index_knowledge(
            workspace_id=workspace_id,
            source_url=release.get("url", ""),
            source_provider="proactive_release",
            title=f"{technology.title()} Release: {release.get('title', 'New')}",
            content=f"New release for {technology}: {release.get('title', '')}\nURL: {release.get('url', '')}",
            trust_score=0.7,
            metadata={
                "technology": technology,
                "feed_type": release.get("feed_type", ""),
                "proactive": True,
            },
        )

    async def _index_advisory(self, workspace_id: str, advisory: dict):
        """Index a security advisory as knowledge."""
        from app.knowledge_engine.store.knowledge_indexer import KnowledgeIndexer

        indexer = KnowledgeIndexer()
        severity = advisory.get("severity", "unknown")
        trust = 0.9 if severity in ("critical", "high") else 0.7

        await indexer.index_knowledge(
            workspace_id=workspace_id,
            source_url=advisory.get("url", ""),
            source_provider="proactive_security",
            title=f"Security Advisory [{severity.upper()}]: {advisory.get('title', '')}",
            content=f"Security advisory for {advisory.get('technology', 'unknown')}: {advisory.get('title', '')}\nSeverity: {severity}\nURL: {advisory.get('url', '')}",
            trust_score=trust,
            metadata={
                "severity": severity,
                "technology": advisory.get("technology", ""),
                "proactive": True,
            },
        )
