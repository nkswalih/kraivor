from dataclasses import dataclass
from enum import StrEnum


class AgentType(StrEnum):
    ORCHESTRATOR = "orchestrator"
    CODE_ANALYST = "code_analyst"
    SECURITY = "security"
    ARCHITECTURE = "architecture"
    PERFORMANCE = "performance"
    EXPLAINER = "explainer"


@dataclass
class Agent:
    name: str
    agent_type: AgentType
    model: str
    provider: str
    system_prompt: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4096
    enabled: bool = True
