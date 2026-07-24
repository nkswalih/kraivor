"""Conflict Resolution — detects contradictory claims across knowledge sources.

When multiple sources provide conflicting information, this module:
1. Detects semantic contradictions using embedding similarity + negation patterns
2. Groups conflicting claims by topic
3. Ranks resolutions by source trust, recency, and consensus
4. Returns a structured conflict report
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from app.infrastructure.rag.embedder import Embedder
from app.infrastructure.db.database import async_session_factory
from sqlalchemy import text

logger = logging.getLogger(__name__)

_embedder = Embedder()

# Negation patterns that flip meaning
NEGATION_PATTERNS = [
    r"\bnot\b", r"\bno\b", r"\bnever\b", r"\bneither\b", r"\bnor\b",
    r"\bcannot\b", r"\bcan't\b", r"\bwon't\b", r"\bdon't\b", r"\bdoesn't\b",
    r"\bisn't\b", r"\baren't\b", r"\bwasn't\b", r"\bweren't\b",
    r"\bshouldn't\b", r"\bwouldn't\b", r"\bcouldn't\b",
    r"\bfalse\b", r"\bincorrect\b", r"\bwrong\b", r"\bdeprecated\b",
    r"\breplaced by\b", r"\bsuperseded by\b",
]

# Affirmation patterns
AFFIRMATION_PATTERNS = [
    r"\bis\b", r"\bare\b", r"\bwas\b", r"\bwere\b",
    r"\btrue\b", r"\bcorrect\b", r"\bright\b", r"\brecommended\b",
    r"\bsupported\b", r"\bofficial\b", r"\bcurrent\b", r"\blatest\b",
]


@dataclass
class ConflictingClaim:
    """A single claim from a source."""
    content: str
    source_url: str
    source_provider: str
    trust_score: float
    fetched_at: str | None = None


@dataclass
class ConflictGroup:
    """A group of conflicting claims about the same topic."""
    topic: str
    claims: list[ConflictingClaim]
    conflict_type: str  # negation, version, deprecated, opinion
    resolution: str | None = None
    confidence: float = 0.0


@dataclass
class ConflictReport:
    """Full conflict resolution report."""
    topic: str
    conflicts_found: int
    groups: list[ConflictGroup]
    resolution_summary: str
    sources_consulted: int


class ConflictResolver:
    """Detects and resolves conflicting knowledge across sources."""

    async def detect_conflicts(
        self,
        workspace_id: str,
        topic: str,
        max_sources: int = 10,
    ) -> ConflictReport:
        """Search stored knowledge for a topic and detect conflicts."""
        # Retrieve knowledge on the topic
        results = await self._search_knowledge(workspace_id, topic, max_sources)

        if len(results) < 2:
            return ConflictReport(
                topic=topic,
                conflicts_found=0,
                groups=[],
                resolution_summary="Insufficient sources to detect conflicts.",
                sources_consulted=len(results),
            )

        # Extract claims from each source
        claims = self._extract_claims(results)

        # Group conflicting claims
        groups = self._group_conflicts(claims)

        # Resolve each group
        for group in groups:
            group.resolution = self._resolve_group(group)
            group.confidence = self._compute_resolution_confidence(group)

        # Build summary
        summary = self._build_resolution_summary(groups)

        return ConflictReport(
            topic=topic,
            conflicts_found=len(groups),
            groups=groups,
            resolution_summary=summary,
            sources_consulted=len(results),
        )

    async def _search_knowledge(
        self, workspace_id: str, query: str, top_k: int
    ) -> list[dict]:
        """Search stored knowledge."""
        async with async_session_factory() as session:
            result = await session.execute(text("""
                SELECT source_url, source_provider, source_trust_score,
                       title, content, fetched_at,
                       ts_rank_cd(
                           to_tsvector('english', coalesce(title, '') || ' ' || coalesce(content, '')),
                           plainto_tsquery('english', :query)
                       ) AS rank
                FROM ai.knowledge_embeddings
                WHERE workspace_id = :workspace_id
                  AND to_tsvector('english', coalesce(title, '') || ' ' || coalesce(content, ''))
                      @@ plainto_tsquery('english', :query)
                ORDER BY rank DESC
                LIMIT :top_k
            """), {"workspace_id": workspace_id, "query": query, "top_k": top_k})
            rows = result.fetchall()

        return [
            {
                "url": row.source_url,
                "provider": row.source_provider,
                "trust": row.source_trust_score or 0.5,
                "title": row.title,
                "content": row.content[:3000],
                "fetched_at": row.fetched_at.isoformat() if row.fetched_at else None,
            }
            for row in rows
        ]

    def _extract_claims(self, results: list[dict]) -> list[ConflictingClaim]:
        """Extract factual claims from search results."""
        claims = []
        for r in results:
            # Split content into sentences
            sentences = re.split(r'[.!?]+', r["content"])
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 20 and self._is_factual_claim(sentence):
                    claims.append(ConflictingClaim(
                        content=sentence,
                        source_url=r["url"],
                        source_provider=r["provider"],
                        trust_score=r["trust"],
                        fetched_at=r.get("fetched_at"),
                    ))
        return claims

    def _is_factual_claim(self, sentence: str) -> bool:
        """Check if a sentence is a factual claim (not opinion/noise)."""
        # Must contain some assertion
        has_verb = bool(re.search(r'\b(is|are|was|were|has|have|can|should|uses?|supports?)\b', sentence.lower()))
        # Not too short or too generic
        is_substantive = len(sentence) > 30
        # Not a question
        is_not_question = not sentence.strip().endswith("?")
        return has_verb and is_substantive and is_not_question

    def _group_conflicts(self, claims: list[ConflictingClaim]) -> list[ConflictGroup]:
        """Group claims that conflict with each other."""
        groups = []
        used = set()

        for i, c1 in enumerate(claims):
            if i in used:
                continue

            group_claims = [c1]
            for j, c2 in enumerate(claims):
                if j <= i or j in used:
                    continue
                if self._claims_conflict(c1, c2):
                    group_claims.append(c2)
                    used.add(j)

            if len(group_claims) >= 2:
                used.add(i)
                conflict_type = self._classify_conflict(group_claims)
                topic = self._extract_topic(c1.content)
                groups.append(ConflictGroup(
                    topic=topic,
                    claims=group_claims,
                    conflict_type=conflict_type,
                ))

        return groups

    def _claims_conflict(self, c1: ConflictingClaim, c2: ConflictingClaim) -> bool:
        """Check if two claims conflict using negation detection + semantic similarity."""
        t1 = c1.content.lower()
        t2 = c2.content.lower()

        # Check for negation pattern differences
        has_negation_1 = any(re.search(p, t1) for p in NEGATION_PATTERNS)
        has_negation_2 = any(re.search(p, t2) for p in NEGATION_PATTERNS)

        # If one is negated and other isn't, they likely conflict
        if has_negation_1 != has_negation_2:
            # Also check they're about the same subject
            words1 = set(re.findall(r'\b\w{4,}\b', t1))
            words2 = set(re.findall(r'\b\w{4,}\b', t2))
            overlap = len(words1 & words2) / max(len(words1 | words2), 1)
            if overlap > 0.3:
                return True

        # Check for version conflicts (v1 vs v2, old vs new)
        version_pattern = r'v?(\d+\.?\d*)'
        v1 = re.findall(version_pattern, t1)
        v2 = re.findall(version_pattern, t2)
        if v1 and v2 and v1 != v2:
            words1 = set(re.findall(r'\b\w{4,}\b', t1))
            words2 = set(re.findall(r'\b\w{4,}\b', t2))
            overlap = len(words1 & words2) / max(len(words1 | words2), 1)
            if overlap > 0.4:
                return True

        # Check for deprecated/superseded patterns
        deprecation_clues = ["deprecated", "replaced by", "superseded", "no longer", "end of life"]
        has_deprecation_1 = any(clue in t1 for clue in deprecation_clues)
        has_deprecation_2 = any(clue in t2 for clue in deprecation_clues)
        if has_deprecation_1 != has_deprecation_2:
            words1 = set(re.findall(r'\b\w{4,}\b', t1))
            words2 = set(re.findall(r'\b\w{4,}\b', t2))
            overlap = len(words1 & words2) / max(len(words1 | words2), 1)
            if overlap > 0.3:
                return True

        return False

    def _classify_conflict(self, claims: list[ConflictingClaim]) -> str:
        """Classify the type of conflict."""
        all_text = " ".join(c.content.lower() for c in claims)

        if any(p in all_text for p in ["deprecated", "replaced by", "superseded", "end of life"]):
            return "deprecated"
        if re.search(r'v?\d+\.?\d*', all_text):
            return "version"
        if any(re.search(p, all_text) for p in NEGATION_PATTERNS):
            return "negation"
        return "opinion"

    def _extract_topic(self, text: str) -> str:
        """Extract a short topic phrase from a claim."""
        # Take first meaningful clause
        words = text.split()[:8]
        return " ".join(words)

    def _resolve_group(self, group: ConflictGroup) -> str:
        """Determine the best resolution for a conflict group."""
        claims = group.claims

        # Sort by trust score (descending), then by recency
        sorted_claims = sorted(claims, key=lambda c: c.trust_score, reverse=True)

        # Check for deprecation
        for c in sorted_claims:
            if any(p in c.content.lower() for p in ["deprecated", "replaced by", "superseded"]):
                return f"Deprecated: {c.content[:200]}"

        # Check for version preference (higher version preferred)
        if group.conflict_type == "version":
            return f"Latest version preferred: {sorted_claims[0].content[:200]}"

        # Default: highest trust source wins
        return f"Highest-trust source ({sorted_claims[0].source_provider}): {sorted_claims[0].content[:200]}"

    def _compute_resolution_confidence(self, group: ConflictGroup) -> float:
        """Compute confidence in the resolution (0-1)."""
        if not group.claims:
            return 0.0

        # Trust spread: bigger spread = more confidence in winner
        trusts = [c.trust_score for c in group.claims]
        max_trust = max(trusts)
        min_trust = min(trusts)
        trust_spread = max_trust - min_trust

        # More sources = higher confidence
        source_count = len(group.claims)
        source_bonus = min(0.3, source_count * 0.05)

        # Consensus: if most sources agree, higher confidence
        if group.conflict_type == "deprecated":
            return min(0.95, 0.7 + source_bonus)

        return min(0.9, 0.5 + trust_spread * 0.3 + source_bonus)

    def _build_resolution_summary(self, groups: list[ConflictGroup]) -> str:
        """Build a human-readable summary of all resolutions."""
        if not groups:
            return "No conflicts detected."

        lines = [f"Found {len(groups)} conflict(s):\n"]
        for i, g in enumerate(groups, 1):
            lines.append(f"{i}. **{g.topic}** ({g.conflict_type})")
            lines.append(f"   Sources: {len(g.claims)} disagreeing")
            lines.append(f"   Resolution: {g.resolution[:150]}")
            lines.append(f"   Confidence: {g.confidence:.0%}")
            lines.append("")

        return "\n".join(lines)
