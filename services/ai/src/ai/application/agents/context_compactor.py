"""Context Compactor — summarises long conversations to stay within token budgets.

Inspired by opencode's ContextCompactor and open-design's prompt compression.
Uses a lightweight LLM call to produce a structured summary of older messages
while preserving the most recent N turns verbatim.
"""

from __future__ import annotations

import logging
import time

from app.infrastructure.llm.client import LLMClient

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a conversation summariser. Compress the conversation history into a concise
structured summary. Preserve all facts, decisions, file paths, error messages, and
technical details. Remove filler, greetings, and repetitive phrases.

Output format (strict):
## Key Facts
- bullet list of important facts, decisions, and context

## Recent Actions
- what was done in the last few turns

## Open Questions
- anything still unresolved (or "None")

Rules:
- Keep under 300 tokens.
- Never invent information.
- Preserve file paths, numbers, and code snippets verbatim.
- Use bullet points, not prose.
"""


class ContextCompactor:
    """Summarises older conversation history to reduce token usage.

    When the history exceeds a configurable token threshold, older turns are
    replaced with an LLM-generated summary while the most recent `keep_recent`
    turns are preserved verbatim.
    """

    def __init__(
        self,
        llm: LLMClient | None = None,
        *,
        token_threshold: int = 2000,
        keep_recent: int = 6,
        model: str = "qwen/qwen3-32b",
        max_summary_tokens: int = 400,
    ):
        self.llm = llm
        self.token_threshold = token_threshold
        self.keep_recent = keep_recent
        self.model = model
        self.max_summary_tokens = max_summary_tokens

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimate (4 chars ≈ 1 token)."""
        return len(text) // 4

    def _history_tokens(self, history: list[dict]) -> int:
        return sum(self._estimate_tokens(h.get("content", "")) for h in history)

    async def compact(self, history: list[dict]) -> list[dict]:
        """Return compacted history. If under threshold, returns original."""
        if not history or len(history) <= self.keep_recent + 2:
            return history

        total_tokens = self._history_tokens(history)
        if total_tokens < self.token_threshold:
            return history

        # Split: older turns to summarise, recent turns to keep
        split_point = len(history) - self.keep_recent
        older = history[:split_point]
        recent = history[split_point:]

        logger.info(
            "context_compactor: compacting %d older turns (~%d tokens) → summary",
            len(older),
            total_tokens,
        )

        if self.llm is None:
            logger.warning("context_compactor: no LLM client, falling back to truncation")
            return recent

        # Build the conversation text for summarisation
        conversation_text = "\n".join(
            f"{'User' if h.get('role') == 'user' else 'Assistant'}: {h.get('content', '')[:1000]}"
            for h in older
        )

        start = time.monotonic()
        try:
            summary_text = await self.llm.generate(
                system=_SYSTEM_PROMPT,
                user=f"Summarise this conversation:\n\n{conversation_text}",
                model=self.model,
                max_tokens=self.max_summary_tokens,
                temperature=0.1,
            )
        except Exception as e:
            logger.warning("context_compactor: LLM summarisation failed: %s", e)
            # Fallback: keep only recent turns
            return recent

        elapsed = time.monotonic() - start
        summary_tokens = self._estimate_tokens(summary_text)
        saved = total_tokens - summary_tokens - self._history_tokens(recent)

        logger.info(
            "context_compactor: summary=%d tokens, saved=%d tokens (%.1fs)",
            summary_tokens,
            saved,
            elapsed,
        )

        # Inject summary as a system message at the start
        summary_turn = {
            "role": "assistant",
            "content": f"[Conversation Summary]\n{summary_text}",
        }
        return [summary_turn] + recent
