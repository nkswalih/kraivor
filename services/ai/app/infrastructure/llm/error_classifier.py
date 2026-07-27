"""Priority-ordered error classification with exclusion chains.

Inspired by OpenClaw's error taxonomy and Claw-code's context-aware hints.
Classifies raw SDK exceptions into structured ClassifiedError objects with
user-friendly messages and actionable suggestions.
"""

import re
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    CONTEXT_OVERFLOW = "context_overflow"
    AUTH_FAILED = "auth_failed"
    BILLING_EXHAUSTED = "billing_exhausted"
    RATE_LIMITED = "rate_limited"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class SuggestedAction(Enum):
    ADD_KEY = "add_key"
    SWITCH_MODEL = "switch_model"
    WAIT = "wait"
    RETRY = "retry"
    NEW_CONVERSATION = "new_conversation"
    CHECK_KEY = "check_key"


class ClassifiedError(Exception):
    """LLM provider error with structured metadata for frontend-friendly messages."""
    def __init__(
        self,
        category: ErrorCategory,
        provider: str,
        model: str,
        user_message: str,
        technical_message: str,
        suggested_action: SuggestedAction,
        retry_after: float | None = None,
        metadata: dict | None = None,
    ):
        super().__init__(user_message)
        self.category = category
        self.provider = provider
        self.model = model
        self.user_message = user_message
        self.technical_message = technical_message
        self.suggested_action = suggested_action
        self.retry_after = retry_after
        self.metadata = metadata or {}


# ── Exclusion patterns (checked FIRST to prevent misclassification) ──────
_RATE_LIMIT_PATTERNS = [
    re.compile(r"rate.?limit", re.IGNORECASE),
    re.compile(r"too many requests", re.IGNORECASE),
    re.compile(r"throttl", re.IGNORECASE),
    re.compile(r"429", re.IGNORECASE),
]

# ── Classification patterns (priority-ordered) ───────────────────────────
_CONTEXT_OVERFLOW_PATTERNS = [
    re.compile(r"prompt is too long", re.IGNORECASE),
    re.compile(r"request_too_large", re.IGNORECASE),
    re.compile(r"exceeds? the context window", re.IGNORECASE),
    re.compile(r"exceeded model token limit", re.IGNORECASE),
    re.compile(r"context.?length.?exceeded", re.IGNORECASE),
    re.compile(r"too many tokens", re.IGNORECASE),
    re.compile(r"maximum context length", re.IGNORECASE),
    re.compile(r"token limit exceeded", re.IGNORECASE),
    re.compile(r"input is too long", re.IGNORECASE),
]

_BILLING_PATTERNS = [
    re.compile(r"insufficient.?credits?", re.IGNORECASE),
    re.compile(r"credits?.*(?:exhausted|empty|depleted|used up)", re.IGNORECASE),
    re.compile(r"payment required", re.IGNORECASE),
    re.compile(r"billing", re.IGNORECASE),
    re.compile(r"quota exceeded", re.IGNORECASE),
    re.compile(r"usage limit", re.IGNORECASE),
    re.compile(r"plan limit", re.IGNORECASE),
]

_AUTH_PATTERNS = [
    re.compile(r"invalid.?api.?key", re.IGNORECASE),
    re.compile(r"authentication.?failed", re.IGNORECASE),
    re.compile(r"unauthorized", re.IGNORECASE),
    re.compile(r"access.?denied", re.IGNORECASE),
    re.compile(r"invalid.?credentials?", re.IGNORECASE),
    re.compile(r"key.?not.?found", re.IGNORECASE),
    re.compile(r"key.?revoked", re.IGNORECASE),
    re.compile(r"invalid.?auth", re.IGNORECASE),
]

_PROVIDER_UNAVAILABLE_PATTERNS = [
    re.compile(r"server.?error", re.IGNORECASE),
    re.compile(r"service.?unavailable", re.IGNORECASE),
    re.compile(r"overloaded", re.IGNORECASE),
    re.compile(r"capacity", re.IGNORECASE),
    re.compile(r"internal.?error", re.IGNORECASE),
]

_TIMEOUT_PATTERNS = [
    re.compile(r"timed?\s*out", re.IGNORECASE),
    re.compile(r"deadline.?exceeded", re.IGNORECASE),
    re.compile(r"connection.?timed?\s*out", re.IGNORECASE),
]

_MODEL_NOT_FOUND_PATTERNS = [
    re.compile(r"model.?not.?found", re.IGNORECASE),
    re.compile(r"invalid.?model", re.IGNORECASE),
    re.compile(r"model.*not.*available", re.IGNORECASE),
    re.compile(r"model.*not.*supported", re.IGNORECASE),
    re.compile(r"unknown.?model", re.IGNORECASE),
]


def _matches_any(text: str, patterns: list[re.Pattern]) -> bool:
    return any(p.search(text) for p in patterns)


def _is_rate_limit_exclusion(text: str) -> bool:
    """Check if error text matches rate-limit patterns (used as exclusion for context overflow)."""
    return _matches_any(text, _RATE_LIMIT_PATTERNS)


def _extract_retry_after(exc) -> float | None:
    """Extract Retry-After header value from SDK exceptions."""
    response = getattr(exc, "response", None)
    if response is None:
        return None
    retry_after = getattr(response, "headers", {}).get("retry-after")
    if retry_after:
        try:
            return float(retry_after)
        except (ValueError, TypeError):
            pass
    return None


def _extract_status_code(exc) -> int | None:
    """Extract HTTP status code from various SDK exception types."""
    response = getattr(exc, "response", None)
    if response is not None:
        status = getattr(response, "status_code", None)
        if status is not None:
            return int(status)
    status = getattr(exc, "status_code", None)
    if status is not None:
        return int(status)
    return None


def classify_error(exc, provider: str, model: str) -> ClassifiedError:
    """Classify a raw SDK exception into a structured ClassifiedError.

    Priority-ordered classification with exclusion chains:
    1. Context overflow (excludes rate-limit errors that mention tokens)
    2. Auth failures
    3. Billing/Credit exhaustion (402)
    4. Rate limits (429)
    5. Provider unavailable (5xx)
    6. Timeout
    7. Unknown
    """
    error_text = str(exc)
    status_code = _extract_status_code(exc)
    retry_after = _extract_retry_after(exc)

    # ── 1. Context overflow (excludes rate-limit) ────────────────────────
    if _matches_any(error_text, _CONTEXT_OVERFLOW_PATTERNS) and not _is_rate_limit_exclusion(error_text):
        return ClassifiedError(
            category=ErrorCategory.CONTEXT_OVERFLOW,
            provider=provider,
            model=model,
            user_message=(
                "Your message is too long for this model. "
                "Start a new conversation or shorten your message."
            ),
            technical_message=error_text,
            suggested_action=SuggestedAction.NEW_CONVERSATION,
            metadata={"status_code": status_code},
        )

    # ── 2. Auth failures ────────────────────────────────────────────────
    if status_code in (401, 403) or _matches_any(error_text, _AUTH_PATTERNS):
        return ClassifiedError(
            category=ErrorCategory.AUTH_FAILED,
            provider=provider,
            model=model,
            user_message=(
                "Authentication failed. "
                "Please check your API key in Settings."
            ),
            technical_message=error_text,
            suggested_action=SuggestedAction.CHECK_KEY,
            metadata={"status_code": status_code},
        )

    # ── 3. Billing / Credit exhaustion (402) ────────────────────────────
    if status_code == 402 or _matches_any(error_text, _BILLING_PATTERNS):
        return ClassifiedError(
            category=ErrorCategory.BILLING_EXHAUSTED,
            provider=provider,
            model=model,
            user_message=(
                "AI credits are exhausted for today. "
                "Add your own API key in Settings to continue, or try again tomorrow."
            ),
            technical_message=error_text,
            suggested_action=SuggestedAction.ADD_KEY,
            metadata={"status_code": status_code},
        )

    # ── 4. Rate limits (429) ────────────────────────────────────────────
    if status_code == 429 or _matches_any(error_text, _RATE_LIMIT_PATTERNS):
        wait_msg = ""
        if retry_after and retry_after > 0:
            wait_msg = f" Wait {int(retry_after)} seconds."
        return ClassifiedError(
            category=ErrorCategory.RATE_LIMITED,
            provider=provider,
            model=model,
            user_message=(
                f"Too many requests.{wait_msg} "
                "Please wait a moment and try again, or switch to a different model."
            ),
            technical_message=error_text,
            suggested_action=SuggestedAction.SWITCH_MODEL,
            retry_after=retry_after,
            metadata={"status_code": status_code},
        )

    # ── 5. Provider unavailable (5xx) ───────────────────────────────────
    if status_code and status_code >= 500:
        return ClassifiedError(
            category=ErrorCategory.PROVIDER_UNAVAILABLE,
            provider=provider,
            model=model,
            user_message=(
                "AI service is temporarily unavailable. "
                "Retrying with a backup..."
            ),
            technical_message=error_text,
            suggested_action=SuggestedAction.RETRY,
            metadata={"status_code": status_code},
        )
    if _matches_any(error_text, _PROVIDER_UNAVAILABLE_PATTERNS):
        return ClassifiedError(
            category=ErrorCategory.PROVIDER_UNAVAILABLE,
            provider=provider,
            model=model,
            user_message=(
                "AI service is temporarily unavailable. "
                "Retrying with a backup..."
            ),
            technical_message=error_text,
            suggested_action=SuggestedAction.RETRY,
            metadata={"status_code": status_code},
        )

    # ── 6. Timeout ──────────────────────────────────────────────────────
    if _matches_any(error_text, _TIMEOUT_PATTERNS):
        return ClassifiedError(
            category=ErrorCategory.TIMEOUT,
            provider=provider,
            model=model,
            user_message=(
                "Request took too long. "
                "Trying a faster model..."
            ),
            technical_message=error_text,
            suggested_action=SuggestedAction.RETRY,
            metadata={"status_code": status_code},
        )

    # ── 7. Model not found ─────────────────────────────────────────────
    if _matches_any(error_text, _MODEL_NOT_FOUND_PATTERNS):
        return ClassifiedError(
            category=ErrorCategory.UNKNOWN,
            provider=provider,
            model=model,
            user_message=(
                f"The model \"{model}\" is not available on {provider}. "
                "Please try a different model."
            ),
            technical_message=error_text,
            suggested_action=SuggestedAction.SWITCH_MODEL,
            metadata={"status_code": status_code},
        )

    # ── 8. OpenRouter-specific error fields ─────────────────────────────
    # OpenRouter embeds errors in the response body, not just HTTP status
    if hasattr(exc, "body") and isinstance(getattr(exc, "body", None), dict):
        body_error = exc.body.get("error", {})
        if isinstance(body_error, dict):
            message = body_error.get("message", "")
            code = body_error.get("code", "")
            if "insufficient" in message.lower() or "credits" in message.lower():
                return ClassifiedError(
                    category=ErrorCategory.BILLING_EXHAUSTED,
                    provider=provider,
                    model=model,
                    user_message=(
                        "AI credits are exhausted for today. "
                        "Add your own API key in Settings to continue, or try again tomorrow."
                    ),
                    technical_message=error_text,
                    suggested_action=SuggestedAction.ADD_KEY,
                    metadata={"status_code": status_code, "or_code": code},
                )

    # ── 9. Unknown — log raw error for diagnostics ───────────────────────
    logger.warning(
        "unclassified_error provider=%s model=%s status=%s error_type=%s error_text=%s",
        provider, model, status_code, type(exc).__name__, error_text[:500],
    )
    return ClassifiedError(
        category=ErrorCategory.UNKNOWN,
        provider=provider,
        model=model,
        user_message="Something went wrong. Please try again.",
        technical_message=error_text,
        suggested_action=SuggestedAction.RETRY,
        metadata={"status_code": status_code, "error_type": type(exc).__name__},
    )
