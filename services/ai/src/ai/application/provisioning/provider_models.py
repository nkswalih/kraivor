"""BYOK model-provider mapping.

Defines which providers each BYOK model can route through.
Users select which provider to use for each model, and enter
the API key for that provider.
"""

PROVIDER_DISPLAY_NAMES = {
    "openrouter": "OpenRouter",
    "anthropic": "Anthropic",
    "openai": "OpenAI",
    "google": "Google",
    "deepseek": "DeepSeek",
    "xai": "xAI",
    "groq": "Groq",
}

PROVIDER_KEY_COLUMN = {
    "openrouter": "openrouter_subkey_encrypted",
    "groq": "groq_key_encrypted",
    "google": "google_key_encrypted",
    "anthropic": "anthropic_key_encrypted",
    "openai": "openai_key_encrypted",
    "deepseek": "deepseek_key_encrypted",
    "xai": "xai_key_encrypted",
}

PROVIDER_URL_COLUMN = {
    "openrouter": "openrouter_custom_url",
    "groq": "groq_custom_url",
    "google": "google_custom_url",
    "anthropic": "anthropic_custom_url",
    "openai": "openai_custom_url",
    "deepseek": "deepseek_custom_url",
    "xai": "xai_custom_url",
}

PROVIDER_VALIDATED_COLUMN = {
    "openrouter": "openrouter_last_validated",
    "groq": "groq_last_validated",
    "google": "google_last_validated",
    "anthropic": "anthropic_last_validated",
    "openai": "openai_last_validated",
    "deepseek": "deepseek_last_validated",
    "xai": "xai_last_validated",
}

DEFAULT_PROVIDER_URLS = {
    "openrouter": "https://openrouter.ai/api/v1",
    "anthropic": "https://api.anthropic.com",
    "openai": "https://api.openai.com/v1",
    "google": "https://generativelanguage.googleapis.com",
    "deepseek": "https://api.deepseek.com",
    "xai": "https://api.x.ai/v1",
    "groq": "https://api.groq.com/openai/v1",
}

# Maps each BYOK model to the providers it can route through.
# Order matters: first provider is the default/preferred one.
BYOK_MODEL_PROVIDERS: dict[str, list[dict[str, str]]] = {
    # Anthropic models — native API or OpenRouter
    "claude-fable-5": [
        {"provider": "anthropic", "default_url": DEFAULT_PROVIDER_URLS["anthropic"]},
        {"provider": "openrouter", "default_url": DEFAULT_PROVIDER_URLS["openrouter"]},
    ],
    "claude-opus-4-8": [
        {"provider": "anthropic", "default_url": DEFAULT_PROVIDER_URLS["anthropic"]},
        {"provider": "openrouter", "default_url": DEFAULT_PROVIDER_URLS["openrouter"]},
    ],
    "claude-opus-4-7": [
        {"provider": "anthropic", "default_url": DEFAULT_PROVIDER_URLS["anthropic"]},
        {"provider": "openrouter", "default_url": DEFAULT_PROVIDER_URLS["openrouter"]},
    ],
    "claude-sonnet-5": [
        {"provider": "anthropic", "default_url": DEFAULT_PROVIDER_URLS["anthropic"]},
        {"provider": "openrouter", "default_url": DEFAULT_PROVIDER_URLS["openrouter"]},
    ],
    "claude-sonnet-4-6": [
        {"provider": "anthropic", "default_url": DEFAULT_PROVIDER_URLS["anthropic"]},
        {"provider": "openrouter", "default_url": DEFAULT_PROVIDER_URLS["openrouter"]},
    ],
    # OpenAI models — only via OpenRouter (not available on native API)
    "gpt-5.6-sol": [
        {"provider": "openrouter", "default_url": DEFAULT_PROVIDER_URLS["openrouter"]},
    ],
    "gpt-5.6-terra": [
        {"provider": "openrouter", "default_url": DEFAULT_PROVIDER_URLS["openrouter"]},
    ],
    "gpt-5.5": [
        {"provider": "openrouter", "default_url": DEFAULT_PROVIDER_URLS["openrouter"]},
    ],
    "gpt-5.4": [
        {"provider": "openrouter", "default_url": DEFAULT_PROVIDER_URLS["openrouter"]},
    ],
    # Google models — native API or OpenRouter
    "gemini-3.5-flash": [
        {"provider": "google", "default_url": DEFAULT_PROVIDER_URLS["google"]},
        {"provider": "openrouter", "default_url": DEFAULT_PROVIDER_URLS["openrouter"]},
    ],
    "gemini-3.1-pro": [
        {"provider": "google", "default_url": DEFAULT_PROVIDER_URLS["google"]},
        {"provider": "openrouter", "default_url": DEFAULT_PROVIDER_URLS["openrouter"]},
    ],
    # DeepSeek models — native API or OpenRouter
    "deepseek-v4-pro": [
        {"provider": "deepseek", "default_url": DEFAULT_PROVIDER_URLS["deepseek"]},
        {"provider": "openrouter", "default_url": DEFAULT_PROVIDER_URLS["openrouter"]},
    ],
    # xAI models — native API or OpenRouter
    "grok-4.3": [
        {"provider": "xai", "default_url": DEFAULT_PROVIDER_URLS["xai"]},
        {"provider": "openrouter", "default_url": DEFAULT_PROVIDER_URLS["openrouter"]},
    ],
}

# Maps each BYOK model to its display info
BYOK_MODEL_INFO: dict[str, dict[str, str]] = {
    "claude-fable-5": {"name": "Claude Fable 5", "provider": "anthropic"},
    "claude-opus-4-8": {"name": "Claude Opus 4.8", "provider": "anthropic"},
    "claude-opus-4-7": {"name": "Claude Opus 4.7", "provider": "anthropic"},
    "claude-sonnet-5": {"name": "Claude Sonnet 5", "provider": "anthropic"},
    "claude-sonnet-4-6": {"name": "Claude Sonnet 4.6", "provider": "anthropic"},
    "gpt-5.6-sol": {"name": "GPT 5.6 Sol", "provider": "openai"},
    "gpt-5.6-terra": {"name": "GPT 5.6 Terra", "provider": "openai"},
    "gpt-5.5": {"name": "GPT 5.5", "provider": "openai"},
    "gpt-5.4": {"name": "GPT 4.5", "provider": "openai"},
    "gemini-3.5-flash": {"name": "Gemini 3.5 Flash", "provider": "google"},
    "gemini-3.1-pro": {"name": "Gemini 3.1 Pro", "provider": "google"},
    "deepseek-v4-pro": {"name": "DeepSeek V4 Pro", "provider": "deepseek"},
    "grok-4.3": {"name": "Grok 4.3", "provider": "xai"},
}


def get_providers_for_model(model_id: str) -> list[dict[str, str]]:
    """Return available providers for a given BYOK model ID."""
    return BYOK_MODEL_PROVIDERS.get(model_id, [])


def get_models_for_provider(provider: str) -> list[str]:
    """Return all BYOK model IDs that can route through the given provider."""
    return [
        model_id
        for model_id, providers in BYOK_MODEL_PROVIDERS.items()
        if any(p["provider"] == provider for p in providers)
    ]


def get_all_providers() -> list[str]:
    """Return all unique provider names."""
    seen = set()
    result = []
    for providers in BYOK_MODEL_PROVIDERS.values():
        for p in providers:
            if p["provider"] not in seen:
                seen.add(p["provider"])
                result.append(p["provider"])
    return result
