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
            "openai/gpt-4o-mini",
            "mistralai/mistral-large",
            "openrouter/auto",
        ],
        "pro": [
            "openai/gpt-4o",
            "anthropic/claude-3.5-sonnet",
            "mistralai/mistral-large",
        ],
        "enterprise": ["*"],
    }

    def get_route(self, task: str) -> dict:
        return self.TASK_ROUTES.get(task, self.TASK_ROUTES["simple_qa"])

    def get_model(self, task: str, tier: str = "free") -> str:
        route = self.get_route(task)
        model = route["model"]
        tier_models = self.TIER_ACCESS.get(tier, self.TIER_ACCESS["free"])
        if "*" in tier_models or model in tier_models:
            return model
        return route["fallback"] or model
