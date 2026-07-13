"""Deduplication of search results by URL and content similarity."""

from __future__ import annotations

import hashlib

from app.knowledge_engine.sources.base import SourceResult, SourceContent


def deduplicate_sources(sources: list[SourceResult]) -> list[SourceResult]:
    """Remove duplicate sources by URL domain+path and content hash."""
    seen_urls: set[str] = set()
    seen_content: set[str] = set()
    unique: list[SourceResult] = []

    for src in sources:
        # Normalize URL
        normalized = _normalize_url(src.url)
        if normalized in seen_urls:
            continue

        # Check content similarity
        content_hash = hashlib.sha256(
            f"{src.title}:{src.snippet[:200]}".encode()
        ).hexdigest()[:12]
        if content_hash in seen_content:
            continue

        seen_urls.add(normalized)
        seen_content.add(content_hash)
        unique.append(src)

    return unique


def deduplicate_content(sources: list[SourceContent]) -> list[SourceContent]:
    """Remove duplicate content by URL and text hash."""
    seen_urls: set[str] = set()
    unique: list[SourceContent] = []

    for src in sources:
        normalized = _normalize_url(src.url)
        if normalized in seen_urls:
            continue
        seen_urls.add(normalized)
        unique.append(src)

    return unique


def _normalize_url(url: str) -> str:
    """Normalize URL for deduplication."""
    from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

    try:
        parsed = urlparse(url)
        # Remove tracking params
        params = parse_qs(parsed.query)
        clean_params = {
            k: v for k, v in params.items()
            if k not in ("utm_source", "utm_medium", "utm_campaign", "utm_content", "ref", "source")
        }
        return urlunparse((
            parsed.scheme,
            parsed.netloc.lower(),
            parsed.path.rstrip("/"),
            parsed.params,
            urlencode(clean_params, doseq=True),
            "",  # Remove fragment
        ))
    except Exception:
        return url.lower().rstrip("/")
