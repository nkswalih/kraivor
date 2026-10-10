import logging
import time

from fastapi import APIRouter

from app.api.dependencies.backpressure import get_backpressure_stats
from app.api.schemas.health import HealthResponse
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse()


@router.get("/health/ready", response_model=HealthResponse)
async def readiness():
    return HealthResponse()


@router.get("/health/load")
async def load_stats():
    return get_backpressure_stats()


@router.get("/health/providers")
async def provider_health():
    """Check connectivity to all configured LLM providers.

    Inspired by Claw-code's /doctor command — tests each provider with a minimal
    request and reports status + latency.
    """
    results = {}
    providers_to_check = []

    if settings.openrouter__master__key:
        providers_to_check.append(("openrouter", settings.openrouter__master__key, "openrouter", "openai/gpt-oss-120b:free"))
    if settings.groq_api_key:
        providers_to_check.append(("groq", settings.groq_api_key, "groq", "qwen/qwen3.6-27b"))

    for name, api_key, provider, model in providers_to_check:
        start = time.monotonic()
        try:
            from app.infrastructure.llm.client import LLMClient
            client = LLMClient(api_key=api_key, provider=provider, model=model)
            await client.generate(
                [{"role": "user", "content": "ping"}],
                max_tokens=5,
                timeout=15.0,
            )
            elapsed = int((time.monotonic() - start) * 1000)
            results[name] = {
                "status": "healthy",
                "latency_ms": elapsed,
                "model": model,
            }
        except Exception as e:
            elapsed = int((time.monotonic() - start) * 1000)
            results[name] = {
                "status": "unhealthy",
                "error": str(e)[:200],
                "latency_ms": elapsed,
                "model": model,
            }

    return {"providers": results}
