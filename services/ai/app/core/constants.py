from enum import StrEnum


class Provider(StrEnum):
    OPENROUTER = "openrouter"
    GROQ = "groq"
    GOOGLE = "google"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"


class AgentType(StrEnum):
    ORCHESTRATOR = "orchestrator"
    CODE_ANALYST = "code_analyst"
    SECURITY = "security"
    ARCHITECTURE = "architecture"
    PERFORMANCE = "performance"
    EXPLAINER = "explainer"


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


TIER_MODEL_ACCESS = {
    "free": [
        "google/gemini-flash-1.5",
        "groq/llama3-70b",
        "openrouter/auto",
    ],
    "pro": [
        "anthropic/claude-3.5-sonnet",
        "openai/gpt-4o-mini",
        "google/gemini-pro-1.5",
        "deepseek/deepseek-coder",
    ],
    "enterprise": ["*"],
}

TIER_BUDGET_LIMITS = {
    "free": 0.50,
    "pro": 10.00,
    "enterprise": 100.00,
}

TIER_RATE_LIMITS = {
    "free": {"requests": 30, "interval": "1m"},
    "pro": {"requests": 120, "interval": "1m"},
    "enterprise": {"requests": 500, "interval": "1m"},
}
