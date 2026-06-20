"""
DynamoDB chat message repository.

Provides CRUD operations for the kraivor-chat-messages table.
Uses the shared DynamoDB client from core.infrastructure.dynamodb.
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from botocore.exceptions import ClientError
from django.conf import settings

from core.infrastructure.dynamodb import get_dynamodb

logger = logging.getLogger(__name__)


class ChatMessageRepository:
    def __init__(self, table_name: str | None = None) -> None:
        self._table_name: str = table_name or settings.DYNAMODB_CHAT_TABLE

    def _table(self):
        return get_dynamodb().Table(self._table_name)

    def put_message(
        self,
        *,
        room_id: str,
        sender_id: str,
        sender_name: str,
        content: str,
        content_type: str = "text",
        reply_to: str | None = None,
        mentions: list[str] | None = None,
        attachment_url: str | None = None,
        message_id: str | None = None,
    ) -> dict[str, Any]:
        now: str = datetime.now(tz=UTC).isoformat()
        message_id = message_id or f"{uuid.uuid4()}"
        item: dict[str, Any] = {
            "room_id": room_id,
            "message_id": message_id,
            "sender_id": sender_id,
            "sender_name": sender_name,
            "content": content,
            "content_type": content_type,
            "reply_to": reply_to or "",
            "mentions": mentions or [],
            "attachment_url": attachment_url or "",
            "created_at": now,
            "edited_at": "",
            "deleted_at": "",
        }
        try:
            self._table().put_item(Item=item)
            logger.debug(
                "dynamodb.message.put", extra={"room_id": room_id, "message_id": message_id}
            )
        except ClientError as exc:
            logger.error(
                "dynamodb.message.put_failed", extra={"room_id": room_id, "error": str(exc)}
            )
            raise
        return item

    def get_messages(
        self, room_id: str, limit: int = 50, start_key: dict[str, Any] | None = None
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        kwargs: dict[str, Any] = {
            "KeyConditionExpression": "room_id = :room_id",
            "ExpressionAttributeValues": {":room_id": room_id},
            "Limit": limit,
            "ScanIndexForward": False,
        }
        if start_key:
            kwargs["ExclusiveStartKey"] = start_key
        try:
            response: dict[str, Any] = self._table().query(**kwargs)
            items: list[dict[str, Any]] = response.get("Items", [])
            last_key: dict[str, Any] | None = response.get("LastEvaluatedKey")
            logger.debug(
                "dynamodb.messages.query", extra={"room_id": room_id, "count": len(items)}
            )
            return items, last_key
        except ClientError as exc:
            logger.error(
                "dynamodb.messages.query_failed",
                extra={"room_id": room_id, "error": str(exc)},
            )
            raise

    def delete_message(self, room_id: str, message_id: str) -> None:
        now: str = datetime.now(tz=UTC).isoformat()
        try:
            self._table().update_item(
                Key={"room_id": room_id, "message_id": message_id},
                UpdateExpression="SET deleted_at = :now",
                ExpressionAttributeValues={":now": now},
            )
            logger.debug(
                "dynamodb.message.deleted",
                extra={"room_id": room_id, "message_id": message_id},
            )
        except ClientError as exc:
            logger.error(
                "dynamodb.message.delete_failed",
                extra={"room_id": room_id, "message_id": message_id, "error": str(exc)},
            )
            raise

    def get_message_by_id(self, room_id: str, message_id: str) -> dict[str, Any] | None:
        try:
            response: dict[str, Any] = self._table().get_item(
                Key={"room_id": room_id, "message_id": message_id}
            )
            item: dict[str, Any] | None = response.get("Item")
            if item:
                logger.debug(
                    "dynamodb.message.get",
                    extra={"room_id": room_id, "message_id": message_id},
                )
                return item
            logger.debug(
                "dynamodb.message.not_found",
                extra={"room_id": room_id, "message_id": message_id},
            )
            return None
        except ClientError as exc:
            logger.error(
                "dynamodb.message.get_failed",
                extra={"room_id": room_id, "message_id": message_id, "error": str(exc)},
            )
            raise

    def update_message(self, room_id: str, message_id: str, content: str) -> dict[str, Any] | None:
        now: str = datetime.now(tz=UTC).isoformat()
        try:
            response: dict[str, Any] = self._table().update_item(
                Key={"room_id": room_id, "message_id": message_id},
                UpdateExpression="SET content = :content, edited_at = :now",
                ExpressionAttributeValues={":content": content, ":now": now},
                ReturnValues="ALL_NEW",
            )
            updated: dict[str, Any] = response.get("Attributes", {})
            logger.debug(
                "dynamodb.message.updated",
                extra={"room_id": room_id, "message_id": message_id},
            )
            return updated
        except ClientError as exc:
            logger.error(
                "dynamodb.message.update_failed",
                extra={"room_id": room_id, "message_id": message_id, "error": str(exc)},
            )
            raise

    def batch_get_messages(
        self, room_id: str, message_ids: list[str]
    ) -> list[dict[str, Any]]:
        if not message_ids:
            return []
        try:
            keys: list[dict[str, str]] = [
                {"room_id": room_id, "message_id": mid} for mid in message_ids
            ]
            response: dict[str, Any] = self._table().meta.client.batch_get_item(
                RequestItems={self._table().name: {"Keys": keys, "ConsistentRead": False}}
            )
            items: list[dict[str, Any]] = response.get("Responses", {}).get(
                self._table().name, []
            )
            logger.debug(
                "dynamodb.messages.batch_get",
                extra={"room_id": room_id, "count": len(items)},
            )
            return items
        except ClientError as exc:
            logger.error(
                "dynamodb.messages.batch_get_failed",
                extra={"room_id": room_id, "error": str(exc)},
            )
            raise

    def search_messages(
        self, room_id: str, query: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        try:
            kwargs: dict[str, Any] = {
                "KeyConditionExpression": "room_id = :room_id",
                "FilterExpression": "contains(content, :query) AND deleted_at = :empty",
                "ExpressionAttributeValues": {
                    ":room_id": room_id,
                    ":query": query,
                    ":empty": "",
                },
                "Limit": limit,
                "ScanIndexForward": False,
            }
            response: dict[str, Any] = self._table().query(**kwargs)
            items: list[dict[str, Any]] = response.get("Items", [])
            logger.debug(
                "dynamodb.messages.search",
                extra={"room_id": room_id, "query": query, "count": len(items)},
            )
            return items
        except ClientError as exc:
            logger.error(
                "dynamodb.messages.search_failed",
                extra={"room_id": room_id, "query": query, "error": str(exc)},
            )
            raise


_repository: ChatMessageRepository | None = None


def get_repository(table_name: str | None = None) -> ChatMessageRepository:
    global _repository
    if _repository is None:
        _repository = ChatMessageRepository(table_name=table_name)
    return _repository


# ---------------------------------------------------------------------------
# Backward-compatible module-level convenience functions
# ---------------------------------------------------------------------------
def put_message(**kwargs: Any) -> dict[str, Any]:
    return get_repository().put_message(**kwargs)


def get_messages(
    room_id: str, limit: int = 50, start_key: dict[str, Any] | None = None
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    return get_repository().get_messages(room_id=room_id, limit=limit, start_key=start_key)


def delete_message(room_id: str, message_id: str) -> None:
    get_repository().delete_message(room_id=room_id, message_id=message_id)


def get_message_by_id(room_id: str, message_id: str) -> dict[str, Any] | None:
    return get_repository().get_message_by_id(room_id=room_id, message_id=message_id)


def update_message(room_id: str, message_id: str, content: str) -> dict[str, Any] | None:
    return get_repository().update_message(room_id=room_id, message_id=message_id, content=content)


def batch_get_messages(room_id: str, message_ids: list[str]) -> list[dict[str, Any]]:
    return get_repository().batch_get_messages(room_id=room_id, message_ids=message_ids)


def search_messages(room_id: str, query: str, limit: int = 50) -> list[dict[str, Any]]:
    return get_repository().search_messages(room_id=room_id, query=query, limit=limit)
