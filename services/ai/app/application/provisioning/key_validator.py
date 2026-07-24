"""BYOK key validation service.

Sends lightweight test requests to provider APIs to verify
that an API key is valid before storing it.
"""

import logging

import httpx

from app.api.schemas.byok import ValidateResult
from app.application.provisioning.provider_models import DEFAULT_PROVIDER_URLS

logger = logging.getLogger(__name__)

VALIDATION_TIMEOUT = 15.0


async def validate_key(
    provider: str,
    api_key: str,
    custom_url: str | None = None,
) -> ValidateResult:
    """Validate an API key by sending a lightweight test request.

    Returns a ValidateResult with validity status and available models.
    """
    base_url = custom_url or DEFAULT_PROVIDER_URLS.get(provider, "")
    if not base_url:
        return ValidateResult(valid=False, error=f"Unknown provider: {provider}")

    try:
        if provider == "anthropic":
            return await _validate_anthropic(api_key, base_url)
        if provider == "google":
            return await _validate_google(api_key, base_url)
        # OpenAI-compatible providers (openrouter, groq, openai, deepseek, xai)
        return await _validate_openai_compatible(provider, api_key, base_url)
    except httpx.TimeoutException:
        return ValidateResult(valid=False, error="Validation request timed out")
    except httpx.ConnectError:
        return ValidateResult(valid=False, error=f"Could not connect to {base_url}")
    except Exception as e:
        logger.warning("key_validation_error provider=%s error=%s", provider, e)
        return ValidateResult(valid=False, error=str(e))


async def _validate_anthropic(
    api_key: str, base_url: str
) -> ValidateResult:
    """Validate an Anthropic API key via messages.create with max_tokens=1."""
    url = f"{base_url}/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 1,
        "messages": [{"role": "user", "content": "hi"}],
    }
    async with httpx.AsyncClient(timeout=VALIDATION_TIMEOUT) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code in (200, 201):
            return ValidateResult(valid=True)
        if resp.status_code in (401, 403):
            return ValidateResult(valid=False, error="Invalid API key")
        if resp.status_code == 402:
            return ValidateResult(valid=False, error="Insufficient credits")
        if resp.status_code == 429:
            return ValidateResult(valid=False, error="Rate limited — key is valid but throttled")
        return ValidateResult(
            valid=False,
            error=f"Validation failed (HTTP {resp.status_code})",
        )


async def _validate_google(
    api_key: str, base_url: str
) -> ValidateResult:
    """Validate a Google API key via models.list."""
    url = f"{base_url}/v1beta/models?key={api_key}"
    async with httpx.AsyncClient(timeout=VALIDATION_TIMEOUT) as client:
        resp = await client.get(url)
        if resp.status_code == 200:
            data = resp.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            return ValidateResult(valid=True, models=models[:50])
        if resp.status_code in (401, 403):
            return ValidateResult(valid=False, error="Invalid API key")
        return ValidateResult(
            valid=False,
            error=f"Validation failed (HTTP {resp.status_code})",
        )


async def _validate_openai_compatible(
    provider: str, api_key: str, base_url: str
) -> ValidateResult:
    """Validate an OpenAI-compatible API key via /models endpoint."""
    url = f"{base_url}/models"
    headers = {"Authorization": f"Bearer {api_key}"}
    async with httpx.AsyncClient(timeout=VALIDATION_TIMEOUT) as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            models = [m.get("id", "") for m in data.get("data", [])]
            return ValidateResult(valid=True, models=models[:100])
        if resp.status_code in (401, 403):
            return ValidateResult(valid=False, error="Invalid API key")
        if resp.status_code == 402:
            return ValidateResult(valid=False, error="Insufficient credits")
        return ValidateResult(
            valid=False,
            error=f"Validation failed (HTTP {resp.status_code})",
        )
