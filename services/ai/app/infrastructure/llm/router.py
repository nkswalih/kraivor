FREE_MODELS = [
    "cohere/north-mini-code:free",
    "poolside/laguna-xs-2.1:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "tencent/hy3:free",
    "poolside/laguna-m.1:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "openai/gpt-oss-120b:free",
]

# ── Per-provider BYOK models ────────────────────────────────
# Keys: frontend model ID → backend model string (OpenRouter path)
BYOK_MODELS = {
    # Anthropic (via native API or OpenRouter fallback)
    "claude-fable-5": "anthropic/claude-fable-5",
    "claude-opus-4-8": "anthropic/claude-opus-4-8",
    "claude-opus-4-7": "anthropic/claude-opus-4-7",
    "claude-sonnet-5": "anthropic/claude-sonnet-5",
    "claude-sonnet-4-6": "anthropic/claude-sonnet-4-6",
    # OpenAI (via native API or OpenRouter fallback)
    "gpt-5.6-sol": "openai/gpt-5.6-sol",
    "gpt-5.6-terra": "openai/gpt-5.6-terra",
    "gpt-5.5": "openai/gpt-5.5",
    "gpt-5.4": "openai/gpt-5.4",
    # Google (via native API or OpenRouter fallback)
    "gemini-3.5-flash": "google/gemini-3.5-flash",
    "gemini-3.1-pro": "google/gemini-3.1-pro",
    # DeepSeek (via native API or OpenRouter fallback)
    "deepseek-v4-pro": "deepseek/deepseek-v4-pro",
    # xAI (via native API or OpenRouter fallback)
    "grok-4.3": "xai/grok-4.3",
}

# ── Kraivor AI built-in model ────────────────────────────────
KRAIVOR_MODEL = "krait-2.0"

# ── All known model IDs (for /models endpoint) ──────────────
ALL_MODEL_IDS = [KRAIVOR_MODEL] + [
    # Free (OpenRouter) — frontend IDs
    "cohere-north-mini-code",
    "nvidia-nemotron-ultra",
    "tencent-hy3",
    "poolside-laguna-xs",
    "poolside-laguna-m",
    "nvidia-nemotron-super",
    "google-gemma-4",
    "nvidia-nemotron-nano",
    "openai-gpt-oss",
] + list(BYOK_MODELS.keys())

# ── Frontend ID → backend model string ───────────────────────
MODEL_BACKEND_MAP = {
    KRAIVOR_MODEL: "openrouter/auto",
    "cohere-north-mini-code": "cohere/north-mini-code:free",
    "nvidia-nemotron-ultra": "nvidia/nemotron-3-ultra-550b-a55b:free",
    "tencent-hy3": "tencent/hy3:free",
    "poolside-laguna-xs": "poolside/laguna-xs-2.1:free",
    "poolside-laguna-m": "poolside/laguna-m.1:free",
    "nvidia-nemotron-super": "nvidia/nemotron-3-super-120b-a12b:free",
    "google-gemma-4": "google/gemma-4-31b-it:free",
    "nvidia-nemotron-nano": "nvidia/nemotron-3-nano-30b-a3b:free",
    "openai-gpt-oss": "openai/gpt-oss-120b:free",
    **BYOK_MODELS,
}

# ── Intent → default route task name mapping ─────────────────
_INTENT_ROUTE_MAP = {
    "code_generation": "code_generation",
    "documentation": "code_generation",
    "writing": "code_generation",
}


class ModelRouter:
    TASK_ROUTES = {
        "intent_classify": {
            "model": "cohere/north-mini-code:free",
            "fallback": "nvidia/nemotron-3-nano-30b-a3b:free",
            "max_tokens": 256,
        },
        "simple_qa": {
            "model": "cohere/north-mini-code:free",
            "fallback": "nvidia/nemotron-3-nano-30b-a3b:free",
            "max_tokens": 4096,
        },
        "code_generation": {
            "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
            "fallback": "cohere/north-mini-code:free",
            "max_tokens": 16384,
        },
        "code_review": {
            "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
            "fallback": "cohere/north-mini-code:free",
            "max_tokens": 4096,
        },
        "security_analysis": {
            "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
            "fallback": "poolside/laguna-m.1:free",
            "max_tokens": 4096,
        },
        "architecture_review": {
            "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
            "fallback": "cohere/north-mini-code:free",
            "max_tokens": 8192,
        },
        "performance_analysis": {
            "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
            "fallback": "poolside/laguna-m.1:free",
            "max_tokens": 4096,
        },
        "tool_calling": {
            "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
            "fallback": "cohere/north-mini-code:free",
            "max_tokens": 4096,
        },
        "embeddings": {
            "model": "openai/gpt-oss-120b:free",
            "fallback": None,
            "max_tokens": 8192,
        },
    }

    TIER_ACCESS = {
        "free": FREE_MODELS,
        "pro": [
            "openai/gpt-4o",
            "anthropic/claude-5-sonnet",
            "mistralai/mistral-large",
        ],
        "enterprise": ["*"],
    }

    def get_route(self, task: str) -> dict:
        route = self.TASK_ROUTES.get(task, self.TASK_ROUTES["simple_qa"])
        return {**route, "fallback_models": FREE_MODELS}

    def get_route_for_user(self, task: str, user_model: str | None = None) -> dict:
        """Return route for a task, overridden by the user's selected model if valid.

        Priority:
          1. If user_model is in BYOK_MODELS → use that model (user has key or OpenRouter fallback)
          2. If user_model is KRAIVOR_MODEL → use default Kraivor route
          3. Otherwise → use default free route for the task
        """
        route = self.get_route(task)

        if not user_model:
            return route

        # Kraivor built-in — use default free route (Krait routes through OpenRouter auto)
        if user_model == KRAIVOR_MODEL:
            return route

        # BYOK model — override the route model
        backend_model = BYOK_MODELS.get(user_model)
        if backend_model:
            return {**route, "model": backend_model}

        # Unknown model — fall through to default free route
        return route

    def get_model(self, task: str, tier: str = "free") -> str:
        route = self.get_route(task)
        model = route["model"]
        tier_models = self.TIER_ACCESS.get(tier, self.TIER_ACCESS["free"])
        if "*" in tier_models or model in tier_models:
            return model
        fallback = route.get("fallback")
        if fallback:
            return fallback
        return model
