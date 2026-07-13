from collections.abc import AsyncGenerator

import google.generativeai as genai
import logging
import time
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from app.infrastructure.llm.cost import estimate_cost
from app.monitoring.metrics import llm_calls
from app.monitoring.metrics import llm_cost as llm_cost_counter
from app.monitoring.metrics import llm_duration, llm_tokens

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, api_key: str, provider: str, model: str):
        self.provider = provider
        self.model = model
        self._init_client(api_key)

    def _init_client(self, api_key: str):
        _OPENAI_COMPATIBLE = {
            "openrouter": "https://openrouter.ai/api/v1",
            "groq": "https://api.groq.com/openai/v1",
            "openai": "https://api.openai.com/v1",
            "deepseek": "https://api.deepseek.com/v1",
            "xai": "https://api.x.ai/v1",
        }
        if self.provider in _OPENAI_COMPATIBLE:
            self.client = AsyncOpenAI(
                api_key=api_key, base_url=_OPENAI_COMPATIBLE[self.provider]
            )
        elif self.provider == "anthropic":
            self.client = AsyncAnthropic(api_key=api_key)
        elif self.provider == "google":
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(self.model)

    async def generate(self, messages: list, **kwargs) -> dict:
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

        if self.provider in ("openrouter", "groq", "openai", "deepseek", "xai"):
            response = await self.client.chat.completions.create(
                model=self.model, messages=messages, **kwargs
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
            response = await self.client.generate_content_async(
                messages[-1]["content"] if messages else "", **kwargs
            )
            result = response.text
            if hasattr(response, "usage_metadata"):
                metrics["input_tokens"] = getattr(
                    response.usage_metadata, "prompt_token_count", 0
                )
                metrics["output_tokens"] = getattr(
                    response.usage_metadata, "candidates_token_count", 0
                )

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

    async def stream(self, messages: list, **kwargs) -> AsyncGenerator[str, None]:
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
            response = await self.client.generate_content_async(
                messages[-1]["content"] if messages else "", stream=True, **kwargs
            )
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
