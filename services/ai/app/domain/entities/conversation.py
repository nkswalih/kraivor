from dataclasses import dataclass, field

from datetime import datetime


@dataclass
class Conversation:
    id: str
    user_id: str
    workspace_id: str
    title: str
    model: str | None = None
    message_count: int = 0
    is_archived: bool = False
    is_pinned: bool = False
    last_message_at: datetime | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
