"""
DynamoDB chat message operations.

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


def _table():
    return get_dynamodb().Table(settings.DYNAMODB_CHAT_TABLE)


def put_message(
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
    now = datetime.now(tz=UTC).isoformat()
    message_id = message_id or f"{uuid.uuid4()}"
    item = {
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
        _table().put_item(Item=item)
        logger.debug("dynamodb.message.put", extra={"room_id": room_id, "message_id": message_id})
    except ClientError as exc:
        logger.error("dynamodb.message.put_failed", extra={"room_id": room_id, "error": str(exc)})
        raise
    return item


def get_messages(
    room_id: str,
    limit: int = 50,
    start_key: dict | None = None,
) -> tuple[list[dict[str, Any]], dict | None]:
    kwargs = {
        "KeyConditionExpression": "room_id = :room_id",
        "ExpressionAttributeValues": {":room_id": room_id},
        "Limit": limit,
        "ScanIndexForward": False,
    }
    if start_key:
        kwargs["ExclusiveStartKey"] = start_key
    try:
        response = _table().query(**kwargs)
        items = response.get("Items", [])
        last_key = response.get("LastEvaluatedKey")
        logger.debug("dynamodb.messages.query", extra={"room_id": room_id, "count": len(items)})
        return items, last_key
    except ClientError as exc:
        logger.error("dynamodb.messages.query_failed", extra={"room_id": room_id, "error": str(exc)})
        raise


def delete_message(room_id: str, message_id: str) -> None:
    now = datetime.now(tz=UTC).isoformat()
    try:
        _table().update_item(
            Key={"room_id": room_id, "message_id": message_id},
            UpdateExpression="SET deleted_at = :now",
            ExpressionAttributeValues={":now": now},
        )
        logger.debug("dynamodb.message.deleted", extra={"room_id": room_id, "message_id": message_id})
    except ClientError as exc:
        logger.error("dynamodb.message.delete_failed", extra={"room_id": room_id, "message_id": message_id, "error": str(exc)})
        raise


def get_message_by_id(room_id: str, message_id: str) -> dict | None:
    try:
        response = _table().get_item(Key={"room_id": room_id, "message_id": message_id})
        item = response.get("Item")
        if item:
            logger.debug("dynamodb.message.get", extra={"room_id": room_id, "message_id": message_id})
            return item
        logger.debug("dynamodb.message.not_found", extra={"room_id": room_id, "message_id": message_id})
        return None
    except ClientError as exc:
        logger.error("dynamodb.message.get_failed", extra={"room_id": room_id, "message_id": message_id, "error": str(exc)})
        raise


def update_message(room_id: str, message_id: str, content: str) -> dict | None:
    now = datetime.now(tz=UTC).isoformat()
    try:
        response = _table().update_item(
            Key={"room_id": room_id, "message_id": message_id},
            UpdateExpression="SET content = :content, edited_at = :now",
            ExpressionAttributeValues={
                ":content": content,
                ":now": now,
            },
            ReturnValues="ALL_NEW",
        )
        updated = response.get("Attributes", {})
        logger.debug("dynamodb.message.updated", extra={"room_id": room_id, "message_id": message_id})
        return updated
    except ClientError as exc:
        logger.error("dynamodb.message.update_failed", extra={"room_id": room_id, "message_id": message_id, "error": str(exc)})
        raise


def batch_get_messages(room_id: str, message_ids: list[str]) -> list[dict]:
    if not message_ids:
        return []
    try:
        keys = [{"room_id": room_id, "message_id": mid} for mid in message_ids]
        response = _table().meta.client.batch_get_item(
            RequestItems={
                _table().name: {
                    "Keys": keys,
                    "ConsistentRead": False,
                }
            }
        )
        items = response.get("Responses", {}).get(_table().name, [])
        logger.debug("dynamodb.messages.batch_get", extra={"room_id": room_id, "count": len(items)})
        return items
    except ClientError as exc:
        logger.error("dynamodb.messages.batch_get_failed", extra={"room_id": room_id, "error": str(exc)})
        raise
