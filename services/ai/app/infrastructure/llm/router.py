FREE_MODELS = [
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "poolside/laguna-xs-2.1:free",
    "openai/gpt-oss-120b:free",
    "tencent/hy3:free",
    "poolside/laguna-m.1:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "cohere/north-mini-code:free",
]


class ModelRouter:
    TASK_ROUTES = {
        "intent_classify": {
            "model": "openai/gpt-4o-mini",
            "fallback": "mistralai/mistral-large",
            "max_tokens": 256,
        },
        "simple_qa": {
            "model": "openai/gpt-4o-mini",
            "fallback": "mistralai/mistral-large",
            "max_tokens": 4096,
        },
        "code_generation": {
            "model": "openai/gpt-4o-mini",
            "fallback": "mistralai/mistral-large",
            "max_tokens": 16384,
        },
        "code_review": {
            "model": "openai/gpt-4o-mini",
            "fallback": "mistralai/mistral-large",
            "max_tokens": 4096,
        },
        "security_analysis": {
            "model": "openai/gpt-4o-mini",
            "fallback": "mistralai/mistral-large",
            "max_tokens": 4096,
        },
        "architecture_review": {
            "model": "openai/gpt-4o-mini",
            "fallback": "mistralai/mistral-large",
            "max_tokens": 8192,
        },
        "performance_analysis": {
            "model": "openai/gpt-4o-mini",
            "fallback": "mistralai/mistral-large",
            "max_tokens": 4096,
        },
        "tool_calling": {
            "model": "openai/gpt-4o-mini",
            "fallback": "mistralai/mistral-large",
            "max_tokens": 4096,
        },
        "embeddings": {
            "model": "openai/gpt-4o-mini",
            "fallback": None,
            "max_tokens": 8192,
        },
    }

    TIER_ACCESS = {
        "free": [
            "google/gemma-4-31b-it:free",
            "nvidia/nemotron-3-nano-30b-a3b:free",
            "poolside/laguna-xs-2.1:free",
            "openai/gpt-oss-120b:free",
            "tencent/hy3:free",
            "poolside/laguna-m.1:free",
            "nvidia/nemotron-3-ultra-550b-a55b:free",
            "cohere/north-mini-code:free",
        ],
        "pro": [
            "openai/gpt-4o",
            "anthropic/claude-3.5-sonnet",
            "mistralai/mistral-large",
        ],
        "enterprise": ["*"],
    }

    def get_route(self, task: str) -> dict:
        route = self.TASK_ROUTES.get(task, self.TASK_ROUTES["simple_qa"])
        return {**route, "fallback_models": FREE_MODELS}

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
