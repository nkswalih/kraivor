from collections.abc import AsyncGenerator

import asyncio
import hashlib
import logging
import time
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI, APITimeoutError, APIConnectionError, RateLimitError, APIStatusError

try:
    from google import genai as google_genai
    from google.genai import types as google_types
    _HAS_GOOGLE_GENAI = True
except ImportError:
    google_genai = None  # type: ignore[assignment]
    google_types = None  # type: ignore[assignment]
    _HAS_GOOGLE_GENAI = False

from app.infrastructure.llm.cost import estimate_cost
from app.infrastructure.llm.error_classifier import classify_error, ClassifiedError
from app.monitoring.metrics import llm_calls
from app.monitoring.metrics import llm_cost as llm_cost_counter
from app.monitoring.metrics import llm_duration, llm_tokens

logger = logging.getLogger(__name__)

# Fix C: Default timeout for LLM calls (seconds). Prevents a single slow provider
# from stalling the entire pipeline for 60+ seconds.
LLM_DEFAULT_TIMEOUT = 45
LLM_SHORT_TIMEOUT = 25

# Fix E: Retry settings for transient LLM failures.
LLM_MAX_RETRIES = 2
LLM_RETRY_BACKOFF = [1.0, 3.0]  # seconds between retries

_client_cache: dict[str, object] = {}

_OPENAI_COMPATIBLE = {
    "openrouter": "https://openrouter.ai/api/v1",
    "groq": "https://api.groq.com/openai/v1",
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "xai": "https://api.x.ai/v1",
}


def _get_cached_client(provider: str, api_key: str, model: str) -> object:
    """Return a cached client for the given provider+key combo."""
    cache_key = hashlib.sha256(f"{provider}:{api_key}".encode()).hexdigest()[:16]

    if cache_key in _client_cache:
        return _client_cache[cache_key]

    if provider in _OPENAI_COMPATIBLE:
        # Fix C: Per-call timeout so a slow provider doesn't stall the pipeline.
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=_OPENAI_COMPATIBLE[provider],
            timeout=__import__("httpx").Timeout(LLM_DEFAULT_TIMEOUT, connect=10.0),
            max_retries=0,  # We handle retries ourselves for observability
        )
    elif provider == "anthropic":
        client = AsyncAnthropic(
            api_key=api_key,
            timeout=__import__("httpx").Timeout(LLM_DEFAULT_TIMEOUT, connect=10.0),
            max_retries=0,
        )
    elif provider == "google":
        if not _HAS_GOOGLE_GENAI:
            raise ValueError("google-genai package not installed. Install with: pip install google-genai")
        client = google_genai.Client(api_key=api_key)
    else:
        raise ValueError(f"Unknown provider: {provider}")

    _client_cache[cache_key] = client
    return client


class LLMClient:
    def __init__(self, api_key: str, provider: str, model: str):
        self.provider = provider
        self.model = model
        self.client = _get_cached_client(provider, api_key, model)

    async def generate(self, messages: list, timeout: float | None = None, **kwargs) -> dict:
        metrics = {
            "provider": self.provider,
            "model": self.model,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost": 0.0,
            "latency_ms": 0,
        }
        start = time.monotonic()
        result = ""
        tool_calls = []

        # Fix E: Retry with backoff for transient LLM failures (timeouts, rate limits, connection errors).
        for attempt in range(1 + LLM_MAX_RETRIES):
            try:
                result, tool_calls, metrics = await self._generate_once(messages, timeout=timeout, **kwargs)
                break
            except APIStatusError as e:
                # NEW: Classify 402/403/429/5xx and raise as ClassifiedError
                classified = classify_error(e, self.provider, self.model)
                raise classified from e
            except (APITimeoutError, APIConnectionError, RateLimitError) as e:
                if attempt < LLM_MAX_RETRIES:
                    wait = LLM_RETRY_BACKOFF[min(attempt, len(LLM_RETRY_BACKOFF) - 1)]
                    logger.warning(
                        "LLM call failed (attempt %d/%d): %s — retrying in %.1fs",
                        attempt + 1, 1 + LLM_MAX_RETRIES, e, wait,
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error(
                        "LLM call failed after %d attempts: %s",
                        1 + LLM_MAX_RETRIES, e,
                    )
                    # Classify the final error
                    classified = classify_error(e, self.provider, self.model)
                    raise classified from e
            except ClassifiedError:
                # Already classified (e.g., from a wrapped call) — re-raise
                raise
            except Exception as e:
                # Non-transient errors: classify and raise
                classified = classify_error(e, self.provider, self.model)
                raise classified from e

        metrics["latency_ms"] = int((time.monotonic() - start) * 1000)
        metrics["cost"] = estimate_cost(
            self.provider, self.model, metrics["input_tokens"], metrics["output_tokens"]
        )

        try:
            llm_calls.labels(self.provider, self.model, "ok").inc()
            llm_duration.labels(self.model).observe(metrics["latency_ms"] / 1000)
            if metrics["cost"] > 0:
                llm_cost_counter.labels(self.model, "unknown").inc(metrics["cost"])
            llm_tokens.labels(self.model, "input").inc(metrics["input_tokens"])
            llm_tokens.labels(self.model, "output").inc(metrics["output_tokens"])
        except Exception as e:
            logger.warning("Failed to record LLM metrics", exc_info=e)

        return {"content": result, "tool_calls": tool_calls or [], **metrics}

    async def _generate_once(self, messages: list, timeout: float | None = None, **kwargs) -> tuple:
        """Single LLM call without retry. Returns (content, tool_calls, metrics)."""
        result = ""
        tool_calls = []
        metrics = {"input_tokens": 0, "output_tokens": 0}

        # Fix 2: Per-call timeout override (e.g., 25s for intent classification vs 45s default)
        effective_timeout = timeout or LLM_DEFAULT_TIMEOUT

        if self.provider in ("openrouter", "groq", "openai", "deepseek", "xai"):
            # Override the client timeout for this call if a specific timeout was requested
            httpx_timeout = __import__("httpx").Timeout(effective_timeout, connect=10.0)
            response = await self.client.chat.completions.create(
                model=self.model, messages=messages, timeout=httpx_timeout, **kwargs
            )
            message = response.choices[0].message
            result = message.content
            raw_calls = getattr(message, "tool_calls", None)
            tool_calls = []
            if raw_calls:
                for tc in raw_calls:
                    tool_calls.append(
                        {
                            "id": tc.id,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                    )
            if result is None and not tool_calls:
                # Some providers return finish_reason=tool_calls even without tools.
                # Fall back to empty content rather than crashing the pipeline.
                logger.warning(
                    "LLM returned null content (finish_reason=%s, model=%s, provider=%s) — "
                    "falling back to empty response",
                    response.choices[0].finish_reason, self.model, self.provider,
                )
                result = ""
            metrics["input_tokens"] = response.usage.prompt_tokens
            metrics["output_tokens"] = response.usage.completion_tokens

        elif self.provider == "anthropic":
            msg = await self.client.messages.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": m["content"]}
                    for m in messages
                    if m["role"] == "user"
                ],
                **kwargs,
            )
            result = msg.content[0].text
            metrics["input_tokens"] = msg.usage.input_tokens
            metrics["output_tokens"] = msg.usage.output_tokens

        elif self.provider == "google":
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=messages[-1]["content"] if messages else "",
            )
            result = response.text or ""
            if hasattr(response, "usage_metadata"):
                metrics["input_tokens"] = getattr(
                    response.usage_metadata, "prompt_token_count", 0
                )
                metrics["output_tokens"] = getattr(
                    response.usage_metadata, "candidates_token_count", 0
                )

        return result, tool_calls, metrics

    async def stream(self, messages: list, **kwargs) -> AsyncGenerator[str, None]:
        """Stream tokens from the LLM. Raises ClassifiedError on provider failures."""
        try:
            if self.provider in ("openrouter", "groq", "openai", "deepseek", "xai"):
                stream = await self.client.chat.completions.create(
                    model=self.model, messages=messages, stream=True, **kwargs
                )
                async for chunk in stream:
                    if delta := chunk.choices[0].delta.content:
                        yield delta
            elif self.provider == "anthropic":
                async with self.client.messages.stream(
                    model=self.model,
                    messages=[
                        {"role": "user", "content": m["content"]}
                        for m in messages
                        if m["role"] == "user"
                    ],
                    **kwargs,
                ) as stream:
                    async for text in stream.text_stream:
                        yield text
            elif self.provider == "google":
                async for chunk in await self.client.aio.models.generate_content_stream(
                    model=self.model,
                    contents=messages[-1]["content"] if messages else "",
                ):
                    if chunk.text:
                        yield chunk.text
        except APIStatusError as e:
            classified = classify_error(e, self.provider, self.model)
            raise classified from e
        except (APITimeoutError, APIConnectionError) as e:
            classified = classify_error(e, self.provider, self.model)
            raise classified from e
        except RateLimitError as e:
            classified = classify_error(e, self.provider, self.model)
            raise classified from e
        except ClassifiedError:
            raise
        except Exception as e:
            classified = classify_error(e, self.provider, self.model)
            raise classified from e
