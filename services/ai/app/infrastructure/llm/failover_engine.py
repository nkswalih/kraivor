"""Two-stage provider failover engine.

Inspired by OpenClaw's auth-profile-rotation + model-fallback pattern:
  Stage 1: Try current provider, on failure rotate auth profiles
  Stage 2: If all profiles exhausted, advance to next model in fallback chain

Also handles cooldown escalation (1st: 30s, 2nd: 60s, 3rd+: 300s cap).
"""

import logging
import time

from app.infrastructure.llm.error_classifier import (
    ClassifiedError,
    ErrorCategory,
    SuggestedAction,
    classify_error,
)
from app.infrastructure.llm.client import LLMClient
from app.application.provisioning.key_resolver import KeyResolver

logger = logging.getLogger(__name__)

# ── Cooldown escalation (OpenClaw pattern) ───────────────────────────────
COOLDOWN_SCHEDULE = [30.0, 60.0, 300.0]  # seconds: 1st, 2nd, 3rd+ failure


class ProviderHealth:
    """Per-provider health tracking with cooldown escalation."""

    __slots__ = ("consecutive_failures", "cooldown_until", "disabled_until", "disabled_reason")

    def __init__(self):
        self.consecutive_failures: int = 0
        self.cooldown_until: float = 0.0
        self.disabled_until: float | None = None
        self.disabled_reason: str | None = None

    def is_available(self, now: float) -> bool:
        if self.disabled_until and now < self.disabled_until:
            return False
        if now < self.cooldown_until:
            return False
        return True

    def record_success(self) -> None:
        self.consecutive_failures = 0
        self.cooldown_until = 0.0
        self.disabled_until = None
        self.disabled_reason = None

    def record_failure(self, category: ErrorCategory) -> None:
        now = time.monotonic()
        self.consecutive_failures += 1

        if category in (ErrorCategory.BILLING_EXHAUSTED, ErrorCategory.AUTH_FAILED):
            self.disabled_until = now + 300.0
            self.disabled_reason = category.value
        else:
            idx = min(self.consecutive_failures - 1, len(COOLDOWN_SCHEDULE) - 1)
            self.cooldown_until = now + COOLDOWN_SCHEDULE[idx]


class FailoverEngine:
    """Two-stage failover: try primary model, then fallback chain.

    Usage:
        engine = FailoverEngine(key_resolver)
        result = await engine.execute(task, messages, user_id, route)
    """

    def __init__(self, key_resolver: KeyResolver | None = None):
        self.key_resolver = key_resolver or KeyResolver()
        self._health: dict[str, ProviderHealth] = {}

    def _get_health(self, provider: str) -> ProviderHealth:
        if provider not in self._health:
            self._health[provider] = ProviderHealth()
        return self._health[provider]

    def _build_candidate_chain(self, route: dict) -> list[dict]:
        """Build ordered list: primary → fallback → cross-provider alternatives.

        Each candidate is a dict with keys: model, provider_hint (optional).
        """
        candidates = []

        # 1. Primary model
        candidates.append({"model": route["model"]})

        # 2. Fallback model from TASK_ROUTES
        fallback = route.get("fallback")
        if fallback and fallback != route["model"]:
            candidates.append({"model": fallback})

        # 3. Cross-provider: Groq models if not already in chain
        existing_models = {c["model"] for c in candidates}
        groq_models = ["qwen/qwen3-32b", "qwen/qwen3.6-27b"]
        for gm in groq_models:
            if gm not in existing_models:
                candidates.append({"model": gm})
                break  # Only add one Groq model

        return candidates

    async def execute(
        self,
        messages: list,
        user_id: str,
        route: dict,
        timeout: float | None = None,
        **kwargs,
    ) -> dict:
        """Execute LLM call with two-stage failover.

        Returns the result dict from LLMClient.generate() on success.
        Raises ClassifiedError if all candidates fail.
        """
        candidates = self._build_candidate_chain(route)
        now = time.monotonic()

        # Filter out providers in cooldown/disabled
        available_candidates = []
        for candidate in candidates:
            # Resolve which provider this model maps to
            try:
                _, provider = await self.key_resolver.resolve(user_id, candidate["model"])
            except Exception:
                provider = "unknown"

            health = self._get_health(provider)
            if health.is_available(now):
                available_candidates.append({**candidate, "_resolved_provider": provider})
            else:
                logger.info(
                    "skip_provider provider=%s model=%s cooldown_until=%.0f disabled=%s",
                    provider, candidate["model"],
                    health.cooldown_until, health.disabled_reason,
                )

        if not available_candidates:
            # All providers are in cooldown — try anyway with the primary
            available_candidates = [candidates[0]]

        last_error: ClassifiedError | None = None

        for candidate in available_candidates:
            model = candidate["model"]
            resolved_provider = candidate.get("_resolved_provider", "unknown")

            try:
                api_key, provider = await self.key_resolver.resolve(user_id, model)
                client = LLMClient(api_key=api_key, provider=provider, model=model)
                result = await client.generate(messages, timeout=timeout, **kwargs)

                # Record success
                self._get_health(provider).record_success()
                return result

            except Exception as exc:
                classified = classify_error(exc, resolved_provider, model)
                last_error = classified

                # Record failure
                health = self._get_health(resolved_provider)
                health.record_failure(classified.category)

                logger.warning(
                    "failover_candidate_failed provider=%s model=%s category=%s "
                    "consecutive=%d user_message=%s",
                    resolved_provider, model, classified.category.value,
                    health.consecutive_failures, classified.user_message,
                )

                # Don't try more candidates for context overflow or auth failures
                if classified.category in (
                    ErrorCategory.CONTEXT_OVERFLOW,
                    ErrorCategory.AUTH_FAILED,
                ):
                    break

        # All candidates exhausted
        if last_error:
            raise last_error
        raise ClassifiedError(
            category=ErrorCategory.UNKNOWN,
            provider="unknown",
            model=route.get("model", "unknown"),
            user_message="AI service is temporarily at capacity. Please try again in a few minutes.",
            technical_message="All failover candidates failed",
            suggested_action=SuggestedAction.RETRY,
        )

    async def execute_stream(
        self,
        messages: list,
        user_id: str,
        route: dict,
        timeout: float | None = None,
        **kwargs,
    ):
        """Execute LLM stream with failover. Yields tokens or error events.

        Yields:
            str: tokens from successful stream
            dict: {"type": "error", "error": str, "category": str, "suggested_action": str}
                  on failure
        """
        candidates = self._build_candidate_chain(route)
        now = time.monotonic()

        available_candidates = []
        for candidate in candidates:
            try:
                _, provider = await self.key_resolver.resolve(user_id, candidate["model"])
            except Exception:
                provider = "unknown"

            health = self._get_health(provider)
            if health.is_available(now):
                available_candidates.append({**candidate, "_resolved_provider": provider})

        if not available_candidates:
            available_candidates = [candidates[0]]

        last_error: ClassifiedError | None = None

        for candidate in available_candidates:
            model = candidate["model"]
            resolved_provider = candidate.get("_resolved_provider", "unknown")

            try:
                api_key, provider = await self.key_resolver.resolve(user_id, model)
                client = LLMClient(api_key=api_key, provider=provider, model=model)
                async for token in client.stream(messages, **kwargs):
                    yield token
                self._get_health(provider).record_success()
                return  # Success — stop failover

            except Exception as exc:
                classified = classify_error(exc, resolved_provider, model)
                last_error = classified
                health = self._get_health(resolved_provider)
                health.record_failure(classified.category)

                logger.warning(
                    "failover_stream_failed provider=%s model=%s category=%s",
                    resolved_provider, model, classified.category.value,
                )

                if classified.category in (
                    ErrorCategory.CONTEXT_OVERFLOW,
                    ErrorCategory.AUTH_FAILED,
                ):
                    break

        # All candidates failed — yield error event
        if last_error:
            yield {
                "type": "error",
                "error": last_error.user_message,
                "category": last_error.category.value,
                "suggested_action": last_error.suggested_action.value,
                "retry_after": last_error.retry_after,
            }
        else:
            yield {
                "type": "error",
                "error": "AI service is temporarily at capacity. Please try again in a few minutes.",
                "category": "unknown",
                "suggested_action": "retry",
                "retry_after": None,
            }
