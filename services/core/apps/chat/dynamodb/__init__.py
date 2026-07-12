# Legacy exports (backward compat)
# V2 exports
from apps.chat.dynamodb.repository import ChatV2Repository
from apps.chat.dynamodb_legacy import (
    ChatMessageRepository,
    batch_get_messages,
    delete_message,
    get_message_by_id,
    get_messages,
    get_repository,
    put_message,
    search_messages,
    update_message,
)

# V2 convenience — import directly from .repository for the singleton getter

__all__ = [
    "ChatMessageRepository",
    "ChatV2Repository",
    "put_message",
    "get_messages",
    "delete_message",
    "get_message_by_id",
    "update_message",
    "batch_get_messages",
    "search_messages",
    "get_repository",
]
