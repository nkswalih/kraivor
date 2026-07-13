"""Main Knowledge Engine — orchestrates retrieval, ranking, and context building."""

from __future__ import annotations

import logging
from typing import Any

from app.knowledge_engine.config import KnowledgeEngineConfig
from app.knowledge_engine.sources.base import SourceResult, SourceContent, RankedSource
from app.knowledge_engine.sources.web_search import WebSearchProvider
from app.knowledge_engine.sources.documentation import DocumentationProvider
from app.knowledge_engine.sources.github import GitHubProvider
from app.knowledge_engine.sources.news import NewsProvider
from app.knowledge_engine.sources.research_papers import ResearchPaperProvider
from app.knowledge_engine.sources.package_registries import PackageRegistryProvider
from app.knowledge_engine.sources.community import CommunityProvider
from app.knowledge_engine.ranking.reranker import rank_sources
from app.knowledge_engine.processing.deduplicator import deduplicate_sources, deduplicate_content
from app.knowledge_engine.context.context_builder import build_knowledge_context, build_citation_list
from app.knowledge_engine.store.knowledge_indexer import KnowledgeIndexer
from app.knowledge_engine.store.knowledge_retriever import KnowledgeRetriever
from app.knowledge_engine.graph.knowledge_graph import KnowledgeGraph
from app.knowledge_engine.quality.quality_scorer import KnowledgeQualityScorer
from app.knowledge_engine.learning.proactive_agent import ProactiveLearningPipeline
from app.knowledge_engine.monitoring.cache import KnowledgeCache
from app.knowledge_engine.monitoring.metrics import KnowledgeMetrics, QueryMetric

logger = logging.getLogger(__name__)


class KnowledgeEngine:
    """The Knowledge Engine retrieves, ranks, and delivers verified knowledge.

    Usage:
        engine = KnowledgeEngine()
        result = await engine.research("What is FastAPI?", max_sources=5)
        # result.context  -> formatted context for LLM
        # result.citations -> structured citation list
    """

    def __init__(self, config: KnowledgeEngineConfig | None = None):
        self.config = config or KnowledgeEngineConfig()

        # Initialize providers
        self.web_search = WebSearchProvider(self.config)
        self.documentation = DocumentationProvider()
        self.github = GitHubProvider(self.config)
        self.news = NewsProvider()
        self.research_papers = ResearchPaperProvider()
        self.package_registries = PackageRegistryProvider()
        self.community = CommunityProvider()

        # Knowledge storage
        self.indexer = KnowledgeIndexer()
        self.retriever = KnowledgeRetriever()

        # Knowledge intelligence
        self.graph = KnowledgeGraph()
        self.quality = KnowledgeQualityScorer()
        self.learning = ProactiveLearningPipeline()

        # Monitoring
        self.cache = KnowledgeCache()
        self.metrics = KnowledgeMetrics()

    async def research(
        self,
        query: str,
        max_sources: int = 10,
        providers: list[str] | None = None,
        embedder: Any = None,
        workspace_id: str | None = None,
    ) -> "ResearchResult":
        """Conduct research on a query using multiple knowledge sources.

        Args:
            query: The research query
            max_sources: Maximum number of sources to return
            providers: Which providers to use (None = all)
            embedder: Optional embedder for semantic ranking
            workspace_id: Optional workspace for cache/metrics tracking

        Returns:
            ResearchResult with context, citations, and metadata
        """
        import time
        start_time = time.time()

        # Check cache first
        cache_hit = False
        if workspace_id:
            cached = await self.cache.get(workspace_id, query, cache_type="research")
            if cached:
                cache_hit = True
                elapsed = (time.time() - start_time) * 1000
                await self.metrics.record_query(QueryMetric(
                    query=query, workspace_id=workspace_id, latency_ms=elapsed,
                    source_count=cached.get("source_count", 0), cache_hit=True,
                ))
                return ResearchResult(
                    query=query,
                    context=cached.get("context", ""),
                    citations=cached.get("citations", []),
                    sources=[],
                    elapsed_seconds=elapsed / 1000,
                )

        # 1. Determine which providers to search
        active_providers = self._select_providers(query, providers)

        # 2. Search all providers in parallel
        all_sources = await self._search_parallel(query, active_providers)

        # 3. Deduplicate
        all_sources = deduplicate_sources(all_sources)

        if not all_sources:
            elapsed = time.time() - start_time
            return ResearchResult(
                query=query,
                context="No relevant knowledge found for this query.",
                citations=[],
                sources=[],
                elapsed_seconds=elapsed,
            )

        # 4. Fetch content for top sources (limited to avoid too many requests)
        fetch_count = min(len(all_sources), max_sources * 2)
        top_sources = all_sources[:fetch_count]
        fetched = await self._fetch_parallel(top_sources)
        fetched = deduplicate_content(fetched)

        # 5. Rank sources
        ranked = await rank_sources(query, fetched, embedder, self.config.min_composite_score)

        # 6. Build context
        context = build_knowledge_context(
            ranked, query,
            max_tokens=self.config.max_context_tokens,
            max_citations=max_sources,
        )
        citations = build_citation_list(ranked, max_sources)

        elapsed = time.time() - start_time
        logger.info(
            "Knowledge research complete: query='%s', sources=%d, elapsed=%.1fs",
            query[:50], len(ranked), elapsed,
        )

        result = ResearchResult(
            query=query,
            context=context,
            citations=citations,
            sources=ranked[:max_sources],
            elapsed_seconds=elapsed,
        )

        # Cache and record metrics
        if workspace_id:
            try:
                await self.cache.set(
                    workspace_id, query,
                    {"context": context, "citations": citations, "source_count": len(ranked)},
                    cache_type="research",
                    ttl_seconds=1800,
                )
                await self.metrics.record_query(QueryMetric(
                    query=query, workspace_id=workspace_id,
                    latency_ms=elapsed * 1000, source_count=len(ranked),
                    cache_hit=False,
                ))
            except Exception:
                pass

        return result

    async def search(
        self,
        query: str,
        max_results: int = 5,
        provider: str = "web",
    ) -> list[SourceResult]:
        """Simple search using a single provider."""
        providers = {
            "web": self.web_search,
            "docs": self.documentation,
            "github": self.github,
            "news": self.news,
            "papers": self.research_papers,
            "packages": self.package_registries,
            "community": self.community,
        }
        p = providers.get(provider, self.web_search)
        return await p.search(query, max_results)

    async def fetch(self, url: str) -> SourceContent | None:
        """Fetch content from a URL using the appropriate provider."""
        # Try to determine provider from URL
        if "github.com" in url:
            return await self.github.fetch_content(url)
        if "arxiv.org" in url or "semanticscholar.org" in url:
            return await self.research_papers.fetch_content(url)
        if "pypi.org" in url or "npmjs.com" in url:
            return await self.package_registries.fetch_content(url)
        if "stackoverflow.com" in url or "reddit.com" in url:
            return await self.community.fetch_content(url)

        # Default: web search provider
        return await self.web_search.fetch_content(url)

    async def get_documentation(
        self,
        framework: str,
        topic: str | None = None,
    ) -> SourceContent | None:
        """Get documentation for a specific framework and optional topic."""
        results = await self.documentation.search(
            topic or framework,
            max_results=1,
        )
        if results:
            return await self.documentation.fetch_content(results[0].url)
        return None

    # ── Knowledge Storage & Retrieval ────────────────────────────────────────

    async def store_knowledge(
        self,
        workspace_id: str,
        source_url: str,
        source_provider: str,
        title: str,
        content: str,
        trust_score: float = 0.5,
        summary: str | None = None,
        metadata: dict | None = None,
    ) -> str:
        """Store a knowledge item in the persistent knowledge base."""
        return await self.indexer.index_knowledge(
            workspace_id=workspace_id,
            source_url=source_url,
            source_provider=source_provider,
            title=title,
            content=content,
            trust_score=trust_score,
            summary=summary,
            metadata=metadata,
        )

    async def store_research_results(
        self,
        workspace_id: str,
        research_result: dict,
        top_k: int = 5,
    ) -> int:
        """Store ranked sources from a research query. Returns count stored."""
        return await self.indexer.index_research_result(
            workspace_id=workspace_id,
            research_result=research_result,
            top_k=top_k,
        )

    async def retrieve_knowledge(
        self,
        workspace_id: str,
        query: str,
        top_k: int = 5,
    ) -> list[dict]:
        """Retrieve previously stored knowledge relevant to a query."""
        return await self.retriever.retrieve(
            workspace_id=workspace_id,
            query=query,
            top_k=top_k,
        )

    async def research_with_memory(
        self,
        query: str,
        workspace_id: str,
        max_sources: int = 10,
    ) -> "ResearchResult":
        """Research with automatic memory: check stored knowledge first, then search web, then store results."""
        # 1. Check stored knowledge first
        stored = await self.retrieve_knowledge(workspace_id, query, top_k=3)

        # 2. Conduct fresh research
        result = await self.research(query, max_sources=max_sources)

        # 3. Store results for future use (async, don't block response)
        try:
            await self.store_research_results(
                workspace_id=workspace_id,
                research_result={
                    "query": query,
                    "sources": [
                        {
                            "url": s.source.url if hasattr(s, "source") else s.url,
                            "title": s.source.title if hasattr(s, "source") else s.title,
                            "provider": s.source.source_provider if hasattr(s, "source") else s.source_provider,
                            "trust_score": s.source.trust_score if hasattr(s, "source") else getattr(s, "composite_score", 0.5),
                            "content": getattr(s.source, "snippet", None) or (s.source.title if hasattr(s, "source") else s.title),
                        }
                        for s in result.sources
                    ],
                },
                top_k=5,
            )
        except Exception as e:
            logger.warning("Failed to store research results: %s", e)

        # 4. Prepend stored knowledge to context
        if stored:
            stored_context = "\n\n".join([
                f"[Previously stored] {s['title']} ({s['provider']}):\n{s['content'][:1500]}"
                for s in stored[:3]
            ])
            result.context = f"## Previously Retrieved Knowledge\n{stored_context}\n\n---\n\n{result.context}"

        return result

    async def get_knowledge_stats(self, workspace_id: str) -> dict:
        """Get knowledge store statistics for a workspace."""
        return await self.retriever.get_stats(workspace_id)

    def _select_providers(
        self,
        query: str,
        providers: list[str] | None,
    ) -> list:
        """Select which providers to search based on query and config."""
        if providers:
            provider_map = {
                "web": self.web_search,
                "docs": self.documentation,
                "github": self.github,
                "news": self.news,
                "papers": self.research_papers,
                "packages": self.package_registries,
                "community": self.community,
            }
            return [provider_map[p] for p in providers if p in provider_map]

        # Auto-select based on query
        query_lower = query.lower()
        selected = []

        # Documentation queries
        if any(kw in query_lower for kw in [
            "how to", "tutorial", "documentation", "docs", "guide",
            "tutorial", "example", "api reference", "setup", "install",
        ]):
            selected.append(self.documentation)

        # Always include web search
        selected.append(self.web_search)

        # GitHub-related queries
        if any(kw in query_lower for kw in [
            "github", "repository", "repo", "release", "changelog",
            "source code", "open source",
        ]):
            selected.append(self.github)

        # News queries
        if any(kw in query_lower for kw in [
            "latest", "recent", "news", "announcement", "update",
            "what happened", "breaking",
        ]):
            selected.append(self.news)

        # Research queries
        if any(kw in query_lower for kw in [
            "research", "paper", "study", "arxiv", "algorithm",
            "theory", "benchmark", "survey",
        ]):
            selected.append(self.research_papers)

        # Package queries
        if any(kw in query_lower for kw in [
            "package", "library", "npm", "pypi", "dependency",
            "version", "changelog", "release",
        ]):
            selected.append(self.package_registries)

        # Community queries
        if any(kw in query_lower for kw in [
            "stackoverflow", "reddit", "community", "forum",
            "discussion", "best practice", "experience",
        ]):
            selected.append(self.community)

        # Always include docs if not already
        if self.documentation not in selected:
            selected.append(self.documentation)

        return selected

    async def _search_parallel(
        self,
        query: str,
        providers: list,
    ) -> list[SourceResult]:
        """Search multiple providers concurrently."""
        import asyncio

        async def _safe_search(provider):
            try:
                return await provider.search(query, max_results=5)
            except Exception as e:
                logger.warning("Search failed for %s: %s", provider.name, e)
                return []

        tasks = [_safe_search(p) for p in providers]
        results = await asyncio.gather(*tasks)

        all_sources = []
        for result_list in results:
            all_sources.extend(result_list)

        return all_sources

    async def _fetch_parallel(
        self,
        sources: list[SourceResult],
    ) -> list[SourceContent]:
        """Fetch content from multiple sources concurrently."""
        import asyncio

        async def _safe_fetch(source):
            try:
                # Find the right provider
                provider = self._get_provider_for_source(source)
                if provider:
                    return await provider.fetch_content(source.url)
                return await self.web_search.fetch_content(source.url)
            except Exception as e:
                logger.warning("Fetch failed for %s: %s", source.url, e)
                return None

        tasks = [_safe_fetch(s) for s in sources]
        results = await asyncio.gather(*tasks)

        return [r for r in results if r is not None]

    def _get_provider_for_source(self, source: SourceResult):
        """Get the appropriate provider for a source."""
        provider_map = {
            "documentation": self.documentation,
            "github": self.github,
            "news": self.news,
            "arxiv": self.research_papers,
            "semantic_scholar": self.research_papers,
            "pypi": self.package_registries,
            "npm": self.package_registries,
            "stackoverflow": self.community,
            "reddit": self.community,
            "tavily": self.web_search,
            "ddgs": self.web_search,
            "google_cse": self.web_search,
        }
        return provider_map.get(source.source_provider, self.web_search)


class ResearchResult:
    """Result from a knowledge research query."""

    def __init__(
        self,
        query: str,
        context: str,
        citations: list[dict],
        sources: list[RankedSource],
        elapsed_seconds: float,
    ):
        self.query = query
        self.context = context
        self.citations = citations
        self.sources = sources
        self.elapsed_seconds = elapsed_seconds

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "context": self.context,
            "citations": self.citations,
            "source_count": len(self.sources),
            "elapsed_seconds": self.elapsed_seconds,
        }

    def __repr__(self) -> str:
        return (
            f"ResearchResult(query='{self.query[:30]}...', "
            f"sources={len(self.sources)}, "
            f"elapsed={self.elapsed_seconds:.1f}s)"
        )
