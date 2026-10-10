"""Knowledge Engine configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class KnowledgeEngineConfig:
    """Configuration for the knowledge engine."""

    # Search providers
    tavily_api_key: str = field(
        default_factory=lambda: os.getenv("TAVILY_API_KEY", "")
    )
    google_api_key: str = field(
        default_factory=lambda: os.getenv("GOOGLE_SEARCH_API_KEY", "")
    )
    google_cse_id: str = field(
        default_factory=lambda: os.getenv("GOOGLE_CSE_ID", "")
    )
    github_token: str = field(
        default_factory=lambda: os.getenv("GITHUB_TOKEN", "")
    )

    # Ranking
    default_trust_score: float = 0.5
    min_relevance_score: float = 0.3
    min_composite_score: float = 0.4
    max_results_per_source: int = 10
    total_max_results: int = 20

    # Freshness half-lives (in days) by domain
    freshness_half_lives: dict[str, int] = field(default_factory=lambda: {
        "ai_news": 7,
        "tech_news": 14,
        "documentation": 180,
        "github_releases": 30,
        "research_papers": 365,
        "general": 60,
        "stack_overflow": 90,
        "reddit": 30,
    })

    # Context building
    max_context_tokens: int = 8000
    max_citations: int = 10
    context_format: str = "structured"  # "structured" or "narrative"


# Source trust scores — manually curated authority levels
SOURCE_TRUST_SCORES: dict[str, float] = {
    # Official documentation (highest trust)
    "docs.python.org": 0.95,
    "docs.djangoproject.com": 0.95,
    "fastapi.tiangolo.com": 0.95,
    "docs.fastapi.dev": 0.95,
    "react.dev": 0.95,
    "nextjs.org": 0.95,
    "nodejs.org": 0.95,
    "docs.docker.com": 0.95,
    "kubernetes.io": 0.95,
    "docs.aws.amazon.com": 0.95,
    "learn.microsoft.com": 0.95,
    "cloud.google.com": 0.95,
    "docs.anthropic.com": 0.95,
    "platform.openai.com": 0.95,
    "ai.google.dev": 0.95,
    "docs.langchain.com": 0.90,
    "python.langchain.com": 0.90,
    "docs.llamaindex.ai": 0.90,
    "redis.io": 0.90,
    "www.postgresql.org": 0.90,
    "docs.sqlalchemy.org": 0.90,
    "vercel.com": 0.85,
    "developers.cloudflare.com": 0.90,
    "supabase.com": 0.85,

    # GitHub (high trust)
    "github.com": 0.90,
    "raw.githubusercontent.com": 0.85,

    # Package registries
    "pypi.org": 0.85,
    "npmjs.com": 0.85,
    "crates.io": 0.85,

    # Research
    "arxiv.org": 0.90,
    "semanticscholar.org": 0.85,
    "aclanthology.org": 0.85,

    # Technical blogs
    "engineering.fb.com": 0.80,
    "netflixtechblog.com": 0.80,
    "blog.google": 0.80,
    "aws.amazon.com/blogs": 0.80,
    "github.blog": 0.80,

    # Community (moderate trust)
    "stackoverflow.com": 0.75,
    "dev.to": 0.60,

    # General (lower trust)
    "medium.com": 0.45,
    "reddit.com": 0.50,
    "quora.com": 0.35,

    # Government (high trust for legal/compliance)
    "gov.uk": 0.90,
    "irs.gov": 0.90,
    "uscis.gov": 0.90,
    "gdpr.eu": 0.85,
}


def get_trust_score(url: str) -> float:
    """Get trust score for a URL based on domain matching."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    # Exact match
    if domain in SOURCE_TRUST_SCORES:
        return SOURCE_TRUST_SCORES[domain]

    # Subdomain match (e.g., blog.github.com -> github.com)
    for known_domain, score in SOURCE_TRUST_SCORES.items():
        if domain.endswith("." + known_domain):
            return score * 0.95  # Slight penalty for subdomains

    return 0.5  # Default for unknown sources
