"""L3: Extractability scoring — how well can the LLM extract claims from this content."""

from __future__ import annotations

import re

from app.knowledge_engine.sources.base import RankedSource


def score_extractability(ranked: list[RankedSource]) -> list[RankedSource]:
    """Score how easily an LLM can extract clean claims from the content.

    High scores for: clear headings, code blocks, tables, short paragraphs,
    specific numbers, named entities.
    Low scores for: walls of text, marketing language, vague claims.
    """
    for r in ranked:
        text = r.source.text
        if not text:
            r.extractability_score = 0.2
            continue

        score = 0.5  # Base score

        # Headings indicate structured content
        heading_count = len(re.findall(r"^#{1,3}\s", text, re.MULTILINE))
        score += min(0.15, heading_count * 0.03)

        # Code blocks are highly extractable
        code_blocks = len(re.findall(r"```", text))
        score += min(0.15, code_blocks * 0.02)

        # Tables indicate structured data
        table_rows = len(re.findall(r"\|.*\|", text))
        score += min(0.1, table_rows * 0.01)

        # Lists indicate organized points
        list_items = len(re.findall(r"^\s*[-*]\s", text, re.MULTILINE))
        score += min(0.1, list_items * 0.01)

        # Numbers and specific data
        numbers = len(re.findall(r"\b\d+\.?\d*[%s]?\b", text))
        score += min(0.1, numbers * 0.01)

        # Penalize marketing language
        marketing_words = ["revolutionary", "game-changing", "best-in-class",
                          "synergy", "leverage", "disrupt", "innovative"]
        marketing_count = sum(1 for w in marketing_words if w in text.lower())
        score -= min(0.2, marketing_count * 0.05)

        # Penalize very long paragraphs (walls of text)
        paragraphs = text.split("\n\n")
        avg_para_len = sum(len(p) for p in paragraphs) / max(len(paragraphs), 1)
        if avg_para_len > 500:
            score -= 0.1

        r.extractability_score = max(0.1, min(1.0, score))

    return ranked
