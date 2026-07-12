"""
DynamoDB single-table repository for Chat v2.

Table: kraivor-chat-v2
  PK: room_id (String)
  SK: sort_key (String) — type-discriminated format

Sort Key Format:
  {type}#{seq:020d}
  type = MSG | THREAD | REACT | EDIT | READ | DELETE

Special Items:
  Counter: sort_key = "_counter", next_seq (Number)
"""

from typing import Any

import logging
import uuid
from botocore.exceptions import ClientError
from datetime import UTC, datetime
from django.conf import settings

from core.infrastructure.dynamodb import get_dynamodb

logger = logging.getLogger(__name__)


def _sort_key(prefix: str, seq: int, *parts: str) -> str:
    key = f"{prefix}#{seq:020d}"
    if parts:
        key += "#" + "#".join(parts)
    return key


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _seq_padded(seq: int) -> str:
    return f"{seq:020d}"


class ChatV2Repository:
    """Single-table DynamoDB repository for Chat v2 message operations."""

    def __init__(self, table_name: str | None = None) -> None:
        self._table_name = table_name or settings.DYNAMODB_CHAT_V2_TABLE

    def _table(self):
        return get_dynamodb().Table(self._table_name)

    # ── Counter Operations ──────────────────────────────────────────────────

    def init_counter(self, room_id: str) -> bool:
        """Seed the seq counter at 1. Idempotent — no-op if counter exists."""
        try:
            self._table().put_item(
                Item={"room_id": room_id, "sort_key": "_counter", "next_seq": 1},
                ConditionExpression="attribute_not_exists(sort_key)",
            )
            logger.debug("counter.init", extra={"room_id": room_id})
            return True
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                logger.debug("counter.exists", extra={"room_id": room_id})
                return False
            logger.warning(
                "counter.init_failed", extra={"room_id": room_id, "error": str(exc)}
            )
            return False

    def allocate_seq(self, room_id: str) -> int:
        """Atomically increment and return the next seq number for the room."""
        try:
            response = self._table().update_item(
                Key={"room_id": room_id, "sort_key": "_counter"},
                UpdateExpression="ADD next_seq :inc",
                ExpressionAttributeValues={":inc": 1},
                ReturnValues="UPDATED_NEW",
            )
            seq = response["Attributes"]["next_seq"]
            logger.debug("counter.allocated", extra={"room_id": room_id, "seq": seq})
            return seq
        except ClientError as exc:
            logger.error(
                "counter.alloc_failed", extra={"room_id": room_id, "error": str(exc)}
            )
            raise

    # ── Message Operations ──────────────────────────────────────────────────

    def put_message(
        self,
        *,
        room_id: str,
        seq: int,
        sender_id: str,
        sender_name: str,
        content: str,
        reply_to_seq: int | None = None,
        mention_user_ids: list[str] | None = None,
        attachment_urls: list[str] | None = None,
        message_id: str | None = None,
    ) -> dict[str, Any]:
        item: dict[str, Any] = {
            "room_id": room_id,
            "sort_key": _sort_key("MSG", seq),
            "message_id": message_id or str(uuid.uuid4()),
            "sender_id": sender_id,
            "sender_name": sender_name,
            "content": content,
            "reply_to_seq": reply_to_seq or 0,
            "mention_user_ids": mention_user_ids or [],
            "attachment_urls": attachment_urls or [],
            "is_edited": False,
            "created_at": _now(),
        }
        try:
            self._table().put_item(Item=item)
            logger.debug("message.put", extra={"room_id": room_id, "seq": seq})
            return item
        except ClientError as exc:
            logger.error(
                "message.put_failed",
                extra={"room_id": room_id, "seq": seq, "error": str(exc)},
            )
            raise

    def get_messages(
        self, room_id: str, limit: int = 50, start_key: dict[str, Any] | None = None
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        try:
            kwargs: dict[str, Any] = {
                "KeyConditionExpression": "room_id = :rid AND begins_with(sort_key, :prefix)",
                "ExpressionAttributeValues": {":rid": room_id, ":prefix": "MSG#"},
                "Limit": limit,
                "ScanIndexForward": False,
            }
            if start_key:
                kwargs["ExclusiveStartKey"] = start_key
            response = self._table().query(**kwargs)
            items = response.get("Items", [])
            last_key = response.get("LastEvaluatedKey")
            logger.debug(
                "messages.query", extra={"room_id": room_id, "count": len(items)}
            )
            return items, last_key
        except ClientError as exc:
            logger.error(
                "messages.query_failed", extra={"room_id": room_id, "error": str(exc)}
            )
            raise

    def get_messages_since(
        self, room_id: str, since_seq: int, limit: int = 200
    ) -> list[dict[str, Any]]:
        """Fetch messages with seq > since_seq (for reconnection sync)."""
        try:
            response = self._table().query(
                KeyConditionExpression="room_id = :rid AND sort_key > :sk",
                ExpressionAttributeValues={
                    ":rid": room_id,
                    ":sk": f"MSG#{_seq_padded(since_seq)}",
                },
                Limit=limit,
                ScanIndexForward=True,
            )
            items = response.get("Items", [])
            logger.debug(
                "messages.since",
                extra={"room_id": room_id, "since_seq": since_seq, "count": len(items)},
            )
            return items
        except ClientError as exc:
            logger.error(
                "messages.since_failed",
                extra={"room_id": room_id, "since_seq": since_seq, "error": str(exc)},
            )
            raise

    def get_message_by_seq(self, room_id: str, seq: int) -> dict[str, Any] | None:
        try:
            response = self._table().get_item(
                Key={"room_id": room_id, "sort_key": f"MSG#{_seq_padded(seq)}"}
            )
            return response.get("Item")
        except ClientError as exc:
            logger.error(
                "message.get_failed",
                extra={"room_id": room_id, "seq": seq, "error": str(exc)},
            )
            raise

    def update_message_content(
        self, room_id: str, seq: int, content: str
    ) -> dict[str, Any] | None:
        try:
            response = self._table().update_item(
                Key={"room_id": room_id, "sort_key": f"MSG#{_seq_padded(seq)}"},
                UpdateExpression="SET content = :content, is_edited = :edited",
                ExpressionAttributeValues={":content": content, ":edited": True},
                ReturnValues="ALL_NEW",
            )
            return response.get("Attributes")
        except ClientError as exc:
            logger.error(
                "message.update_failed",
                extra={"room_id": room_id, "seq": seq, "error": str(exc)},
            )
            raise

    def delete_message(self, room_id: str, seq: int, deleted_by: str) -> None:
        """Mark a message as deleted. Overwrites content."""
        try:
            self._table().update_item(
                Key={"room_id": room_id, "sort_key": f"MSG#{_seq_padded(seq)}"},
                UpdateExpression="SET content = :deleted, is_edited = :edited",
                ExpressionAttributeValues={":deleted": "[deleted]", ":edited": True},
            )
            logger.debug("message.deleted", extra={"room_id": room_id, "seq": seq})
        except ClientError as exc:
            logger.error(
                "message.delete_failed",
                extra={"room_id": room_id, "seq": seq, "error": str(exc)},
            )
            raise

    # ── Thread Reply Operations ─────────────────────────────────────────────

    def put_thread_reply(
        self,
        *,
        room_id: str,
        parent_seq: int,
        seq: int,
        sender_id: str,
        sender_name: str,
        content: str,
        mention_user_ids: list[str] | None = None,
        message_id: str | None = None,
    ) -> dict[str, Any]:
        item: dict[str, Any] = {
            "room_id": room_id,
            "sort_key": _sort_key("THREAD", parent_seq, _seq_padded(seq)),
            "message_id": message_id or str(uuid.uuid4()),
            "parent_seq": parent_seq,
            "seq": seq,
            "sender_id": sender_id,
            "sender_name": sender_name,
            "content": content,
            "mention_user_ids": mention_user_ids or [],
            "created_at": _now(),
        }
        try:
            self._table().put_item(Item=item)
            logger.debug(
                "thread_reply.put",
                extra={"room_id": room_id, "parent_seq": parent_seq, "seq": seq},
            )
            return item
        except ClientError as exc:
            logger.error(
                "thread_reply.put_failed", extra={"room_id": room_id, "error": str(exc)}
            )
            raise

    def get_thread_replies(self, room_id: str, parent_seq: int) -> list[dict[str, Any]]:
        try:
            response = self._table().query(
                KeyConditionExpression="room_id = :rid AND begins_with(sort_key, :prefix)",
                ExpressionAttributeValues={
                    ":rid": room_id,
                    ":prefix": f"THREAD#{_seq_padded(parent_seq)}#",
                },
                ScanIndexForward=True,
            )
            return response.get("Items", [])
        except ClientError as exc:
            logger.error(
                "thread_replies.query_failed",
                extra={"room_id": room_id, "parent_seq": parent_seq, "error": str(exc)},
            )
            raise

    # ── Reaction Operations ─────────────────────────────────────────────────

    def put_reaction(
        self, *, room_id: str, target_seq: int, user_id: str, user_name: str, emoji: str
    ) -> dict[str, Any]:
        item: dict[str, Any] = {
            "room_id": room_id,
            "sort_key": _sort_key("REACT", target_seq, user_id, emoji),
            "target_seq": target_seq,
            "user_id": user_id,
            "user_name": user_name,
            "emoji": emoji,
            "created_at": _now(),
        }
        try:
            self._table().put_item(Item=item)
            return item
        except ClientError as exc:
            logger.error(
                "reaction.put_failed",
                extra={"room_id": room_id, "target_seq": target_seq, "error": str(exc)},
            )
            raise

    def delete_reaction(
        self, *, room_id: str, target_seq: int, user_id: str, emoji: str
    ) -> None:
        try:
            self._table().delete_item(
                Key={
                    "room_id": room_id,
                    "sort_key": _sort_key("REACT", target_seq, user_id, emoji),
                }
            )
        except ClientError as exc:
            logger.error(
                "reaction.delete_failed",
                extra={"room_id": room_id, "target_seq": target_seq, "error": str(exc)},
            )
            raise

    def get_reactions(self, room_id: str, target_seq: int) -> list[dict[str, Any]]:
        try:
            response = self._table().query(
                KeyConditionExpression="room_id = :rid AND begins_with(sort_key, :prefix)",
                ExpressionAttributeValues={
                    ":rid": room_id,
                    ":prefix": f"REACT#{_seq_padded(target_seq)}#",
                },
            )
            return response.get("Items", [])
        except ClientError as exc:
            logger.error(
                "reactions.query_failed",
                extra={"room_id": room_id, "target_seq": target_seq, "error": str(exc)},
            )
            raise

    # ── Edit Record Operations ──────────────────────────────────────────────

    def put_edit_record(
        self,
        *,
        room_id: str,
        target_seq: int,
        edit_seq: int,
        previous_content: str,
        new_content: str,
        edited_by: str,
    ) -> dict[str, Any]:
        item: dict[str, Any] = {
            "room_id": room_id,
            "sort_key": _sort_key("EDIT", target_seq, _seq_padded(edit_seq)),
            "target_seq": target_seq,
            "edit_seq": edit_seq,
            "previous_content": previous_content,
            "new_content": new_content,
            "edited_by": edited_by,
            "edited_at": _now(),
        }
        try:
            self._table().put_item(Item=item)
            return item
        except ClientError as exc:
            logger.error(
                "edit_record.put_failed",
                extra={"room_id": room_id, "target_seq": target_seq, "error": str(exc)},
            )
            raise

    # ── Read Receipt Operations ─────────────────────────────────────────────

    def put_read_receipt(
        self, *, room_id: str, user_id: str, read_up_to_seq: int
    ) -> dict[str, Any]:
        try:
            response = self._table().update_item(
                Key={"room_id": room_id, "sort_key": f"READ#{user_id}"},
                UpdateExpression="SET read_up_to_seq = :seq, read_at = :now",
                ExpressionAttributeValues={":seq": read_up_to_seq, ":now": _now()},
                ReturnValues="ALL_NEW",
            )
            return response.get("Attributes", {})
        except ClientError as exc:
            logger.error(
                "read_receipt.put_failed",
                extra={"room_id": room_id, "user_id": user_id, "error": str(exc)},
            )
            raise

    def get_read_receipt(self, room_id: str, user_id: str) -> dict[str, Any] | None:
        try:
            response = self._table().get_item(
                Key={"room_id": room_id, "sort_key": f"READ#{user_id}"}
            )
            return response.get("Item")
        except ClientError as exc:
            logger.error(
                "read_receipt.get_failed",
                extra={"room_id": room_id, "user_id": user_id, "error": str(exc)},
            )
            raise

    # ── Deletion Record Operations ──────────────────────────────────────────

    def put_deletion_record(
        self, *, room_id: str, target_seq: int, delete_seq: int, deleted_by: str
    ) -> dict[str, Any]:
        item: dict[str, Any] = {
            "room_id": room_id,
            "sort_key": _sort_key("DELETE", target_seq, _seq_padded(delete_seq)),
            "target_seq": target_seq,
            "delete_seq": delete_seq,
            "deleted_by": deleted_by,
            "deleted_at": _now(),
        }
        try:
            self._table().put_item(Item=item)
            return item
        except ClientError as exc:
            logger.error(
                "deletion_record.put_failed",
                extra={"room_id": room_id, "target_seq": target_seq, "error": str(exc)},
            )
            raise

    # ── Search ──────────────────────────────────────────────────────────────

    def search_messages(
        self, room_id: str, query: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        try:
            response = self._table().query(
                KeyConditionExpression="room_id = :rid AND begins_with(sort_key, :prefix)",
                FilterExpression="contains(content, :query)",
                ExpressionAttributeValues={
                    ":rid": room_id,
                    ":prefix": "MSG#",
                    ":query": query,
                },
                Limit=limit,
                ScanIndexForward=False,
            )
            return response.get("Items", [])
        except ClientError as exc:
            logger.error(
                "messages.search_failed",
                extra={"room_id": room_id, "query": query, "error": str(exc)},
            )
            raise


_repository: ChatV2Repository | None = None


def get_repository(table_name: str | None = None) -> ChatV2Repository:
    global _repository
    if _repository is None:
        _repository = ChatV2Repository(table_name=table_name)
    return _repository
