from dataclasses import dataclass, field
from enum import StrEnum

from datetime import datetime


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class Message:
    role: MessageRole
    content: str
    conversation_id: str | None = None
    user_id: str | None = None
    model: str | None = None
    tokens_input: int | None = None
    tokens_output: int | None = None
    metadata: dict | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
