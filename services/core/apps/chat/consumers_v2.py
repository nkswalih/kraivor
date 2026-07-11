"""
Chat v2 WebSocket consumer — global connection, seq-based protocol.

Single WebSocket per user (no room_id in URL). Subscribe to rooms
via SUBSCRIBE action. All message operations use the v2 DynamoDB
repository with type-discriminated sort keys and atomic seq counter.
"""

import json

import logging
import uuid
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from datetime import UTC, datetime
from django.db import transaction

from apps.chat.dynamodb.repository import ChatV2Repository
from apps.chat.models import Room, RoomMember
from core.infrastructure.redis import get_redis

logger = logging.getLogger(__name__)

TYPING_COOLDOWN = 2.5  # seconds
HEARTBEAT_TIMEOUT = 60  # seconds — presence TTL
HEARTBEAT_INTERVAL = 30  # seconds — client sends heartbeat every 30s


class ChatV2Consumer(AsyncWebsocketConsumer):
    """Global WebSocket consumer for Chat v2 — one connection per user."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_id: str | None = None
        self.user_group: str | None = None
        self.subscribed_rooms: set[str] = set()
        self.last_typing_at: dict[str, float] = {}
        self.repo = ChatV2Repository()

    # ── Connection ──────────────────────────────────────────────────────────

    async def connect(self) -> None:
        self.user_id = self.scope.get("user_id")
        if not self.user_id:
            logger.warning("chat_v2.connect.rejected.no_user")
            await self.close(code=4001)
            return

        self.user_group = f"user_{self.user_id}"
        await self.channel_layer.group_add(self.user_group, self.channel_name)
        await self._set_presence("ONLINE")
        await self.accept()

        # Send CONNECTED event with room list
        rooms_data = await self._get_user_rooms()
        await self.send(
            text_data=json.dumps(
                {
                    "type": "CONNECTED",
                    "user_id": self.user_id,
                    "rooms": rooms_data,
                    "server_time": datetime.now(tz=UTC).isoformat(),
                }
            )
        )

        logger.info("chat_v2.connect.accepted", extra={"user_id": self.user_id})

    async def disconnect(self, close_code: int) -> None:
        for room_id in self.subscribed_rooms:
            await self.channel_layer.group_discard(f"room_{room_id}", self.channel_name)
        self.subscribed_rooms.clear()

        if self.user_group:
            await self.channel_layer.group_discard(self.user_group, self.channel_name)

        await self._clear_presence()
        logger.info(
            "chat_v2.disconnected", extra={"user_id": self.user_id, "code": close_code}
        )

    # ── Message Router ──────────────────────────────────────────────────────

    async def receive(self, text_data: str) -> None:
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self._send_error("INVALID_JSON", "Malformed payload.")
            return

        action = data.get("action", "")
        handler = {
            "SUBSCRIBE": self._handle_subscribe,
            "SYNC_ROOMS": self._handle_sync_rooms,
            "SEND": self._handle_send,
            "THREAD_REPLY": self._handle_thread_reply,
            "REACT": self._handle_react,
            "EDIT": self._handle_edit,
            "DELETE": self._handle_delete,
            "MARK_READ": self._handle_mark_read,
            "TYPING": self._handle_typing,
            "PRESENCE": self._handle_presence,
            "HEARTBEAT": self._handle_heartbeat,
        }.get(action)

        if handler:
            await handler(data)
        else:
            await self._send_error("UNKNOWN_ACTION", f"No handler for '{action}'.")

    # ── Action Handlers ─────────────────────────────────────────────────────

    async def _handle_subscribe(self, data: dict) -> None:
        room_id = data.get("room_id")
        last_seen_seq = data.get("last_seen_seq") or 0
        if not room_id:
            await self._send_error("INVALID_REQUEST", "room_id is required.")
            return

        if room_id in self.subscribed_rooms:
            # Already subscribed — send SYNC if there are newer messages
            pass
        else:
            await self.channel_layer.group_add(f"room_{room_id}", self.channel_name)
            self.subscribed_rooms.add(room_id)

        # Send delta sync for messages since last_seen_seq
        if last_seen_seq > 0:
            messages = await self.repo.get_messages_since(room_id, last_seen_seq)
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "SYNC",
                        "room_id": room_id,
                        "messages": messages,
                        "upto_seq": max(
                            (m.get("seq", 0) for m in messages), default=last_seen_seq
                        ),
                    }
                )
            )

        logger.debug(
            "chat_v2.subscribe",
            extra={
                "user_id": self.user_id,
                "room_id": room_id,
                "since_seq": last_seen_seq,
            },
        )

    async def _handle_sync_rooms(self, data: dict) -> None:
        rooms = data.get("rooms", [])
        for entry in rooms:
            room_id = entry.get("room_id")
            last_seen_seq = entry.get("last_seen_seq") or 0
            if not room_id:
                continue

            if room_id not in self.subscribed_rooms:
                await self.channel_layer.group_add(f"room_{room_id}", self.channel_name)
                self.subscribed_rooms.add(room_id)

            messages = await self.repo.get_messages_since(room_id, last_seen_seq)
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "SYNC",
                        "room_id": room_id,
                        "messages": messages,
                        "upto_seq": max(
                            (m.get("seq", 0) for m in messages), default=last_seen_seq
                        ),
                    }
                )
            )

        logger.debug(
            "chat_v2.sync_rooms",
            extra={"user_id": self.user_id, "room_count": len(rooms)},
        )

    async def _handle_send(self, data: dict) -> None:
        room_id = data.get("room_id")
        content = (data.get("content") or "").strip()
        if not room_id or not content:
            await self._send_error(
                "INVALID_REQUEST", "room_id and content are required."
            )
            return

        is_member = await self._check_membership(room_id)
        if not is_member:
            await self._send_error(
                "PERMISSION_DENIED", "You are not a member of this room."
            )
            return

        # Allocate seq (atomic DynamoDB counter)
        seq = await self.repo.allocate_seq(room_id)
        sender_name = self.scope.get("user_name", "")

        # Write message to DynamoDB
        message_id = str(uuid.uuid4())
        msg = await self.repo.put_message(
            room_id=room_id,
            seq=seq,
            sender_id=self.user_id,
            sender_name=sender_name,
            content=content,
            reply_to_seq=data.get("reply_to_seq"),
            mention_user_ids=data.get("mention_user_ids", []),
            attachment_urls=data.get("attachment_urls", []),
            message_id=message_id,
        )

        # Update room metadata (async)
        await self._update_room_metadata(room_id, content, sender_name)

        # Broadcast to room group (exclude sender)
        await self.channel_layer.group_send(
            f"room_{room_id}",
            {
                "type": "chat_v2_message",
                "exclude_user_id": self.user_id,
                "room_id": room_id,
                "seq": seq,
                "message_id": message_id,
                "sender_id": self.user_id,
                "sender_name": sender_name,
                "content": content,
                "reply_to_seq": data.get("reply_to_seq"),
                "mention_user_ids": data.get("mention_user_ids", []),
                "attachment_urls": data.get("attachment_urls", []),
                "is_edited": False,
                "created_at": msg["created_at"],
            },
        )

        # Confirm to sender
        await self.send(
            text_data=json.dumps(
                {
                    "type": "MESSAGE_SENT",
                    "room_id": room_id,
                    "seq": seq,
                    "message_id": message_id,
                    "created_at": msg["created_at"],
                }
            )
        )

        logger.info(
            "chat_v2.message.sent",
            extra={"user_id": self.user_id, "room_id": room_id, "seq": seq},
        )

    async def _handle_thread_reply(self, data: dict) -> None:
        room_id = data.get("room_id")
        parent_seq = data.get("parent_seq")
        content = (data.get("content") or "").strip()
        if not room_id or not parent_seq or not content:
            await self._send_error(
                "INVALID_REQUEST", "room_id, parent_seq, and content are required."
            )
            return

        is_member = await self._check_membership(room_id)
        if not is_member:
            await self._send_error(
                "PERMISSION_DENIED", "You are not a member of this room."
            )
            return

        seq = await self.repo.allocate_seq(room_id)
        sender_name = self.scope.get("user_name", "")
        message_id = str(uuid.uuid4())

        reply = await self.repo.put_thread_reply(
            room_id=room_id,
            parent_seq=parent_seq,
            seq=seq,
            sender_id=self.user_id,
            sender_name=sender_name,
            content=content,
            mention_user_ids=data.get("mention_user_ids", []),
            message_id=message_id,
        )

        await self.channel_layer.group_send(
            f"room_{room_id}",
            {
                "type": "chat_v2_thread_reply",
                "exclude_user_id": self.user_id,
                "room_id": room_id,
                "parent_seq": parent_seq,
                "seq": seq,
                "message_id": message_id,
                "sender_id": self.user_id,
                "sender_name": sender_name,
                "content": content,
                "mention_user_ids": data.get("mention_user_ids", []),
                "created_at": reply["created_at"],
            },
        )

    async def _handle_react(self, data: dict) -> None:
        room_id = data.get("room_id")
        target_seq = data.get("target_seq")
        emoji = data.get("emoji")
        if not room_id or not target_seq or not emoji:
            await self._send_error(
                "INVALID_REQUEST", "room_id, target_seq, and emoji are required."
            )
            return

        user_name = self.scope.get("user_name", "")

        if data.get("remove"):
            await self.repo.delete_reaction(
                room_id=room_id,
                target_seq=target_seq,
                user_id=self.user_id,
                emoji=emoji,
            )
            await self.channel_layer.group_send(
                f"room_{room_id}",
                {
                    "type": "chat_v2_reaction",
                    "remove": True,
                    "room_id": room_id,
                    "target_seq": target_seq,
                    "user_id": self.user_id,
                    "user_name": user_name,
                    "emoji": emoji,
                },
            )
        else:
            await self.repo.put_reaction(
                room_id=room_id,
                target_seq=target_seq,
                user_id=self.user_id,
                user_name=user_name,
                emoji=emoji,
            )
            await self.channel_layer.group_send(
                f"room_{room_id}",
                {
                    "type": "chat_v2_reaction",
                    "remove": False,
                    "room_id": room_id,
                    "target_seq": target_seq,
                    "user_id": self.user_id,
                    "user_name": user_name,
                    "emoji": emoji,
                },
            )

    async def _handle_edit(self, data: dict) -> None:
        room_id = data.get("room_id")
        seq = data.get("seq")
        new_content = (data.get("content") or "").strip()
        if not room_id or not seq or not new_content:
            await self._send_error(
                "INVALID_REQUEST", "room_id, seq, and content are required."
            )
            return

        # Update message content in DynamoDB
        updated = await self.repo.update_message_content(room_id, seq, new_content)
        if not updated:
            await self._send_error("NOT_FOUND", "Message not found.")
            return

        await self.channel_layer.group_send(
            f"room_{room_id}",
            {
                "type": "chat_v2_message_edited",
                "room_id": room_id,
                "seq": seq,
                "content": new_content,
                "edited_at": datetime.now(tz=UTC).isoformat(),
            },
        )

    async def _handle_delete(self, data: dict) -> None:
        room_id = data.get("room_id")
        seq = data.get("seq")
        if not room_id or not seq:
            await self._send_error("INVALID_REQUEST", "room_id and seq are required.")
            return

        await self.repo.delete_message(room_id, seq, deleted_by=self.user_id)

        await self.channel_layer.group_send(
            f"room_{room_id}",
            {"type": "chat_v2_message_deleted", "room_id": room_id, "seq": seq},
        )

    async def _handle_mark_read(self, data: dict) -> None:
        room_id = data.get("room_id")
        upto_seq = data.get("upto_seq")
        if not room_id or not upto_seq:
            return

        await self._save_read_receipt(room_id, upto_seq)
        logger.debug(
            "chat_v2.mark_read",
            extra={"user_id": self.user_id, "room_id": room_id, "seq": upto_seq},
        )

    async def _handle_typing(self, data: dict) -> None:
        room_id = data.get("room_id")
        status = data.get("status")  # "START" or "STOP"
        if not room_id or not status:
            return

        if status == "START":
            redis = get_redis()
            if redis:
                last_key = f"typing:room:{room_id}:last:{self.user_id}"
                now = datetime.now(tz=UTC).timestamp()
                last = redis.get(last_key)
                if last and (now - float(last)) < TYPING_COOLDOWN:
                    return  # throttled
                redis.setex(last_key, 5, str(now))
                redis.sadd(f"typing:room:{room_id}", self.user_id)
                redis.expire(f"typing:room:{room_id}", 5)

        await self.channel_layer.group_send(
            f"room_{room_id}",
            {
                "type": "chat_v2_typing",
                "room_id": room_id,
                "user_id": self.user_id,
                "user_name": self.scope.get("user_name", ""),
                "status": status,
            },
        )

    async def _handle_presence(self, data: dict) -> None:
        status = data.get("status", "ONLINE")
        await self._set_presence(status)
        await self.channel_layer.group_send(
            self.user_group,
            {"type": "chat_v2_presence", "user_id": self.user_id, "status": status},
        )

    async def _handle_heartbeat(self, data: dict) -> None:
        redis = get_redis()
        if redis:
            redis.expire(f"presence:user:{self.user_id}", HEARTBEAT_TIMEOUT)

    # ── Broadcast Receivers (called by channel layer) ───────────────────────

    async def chat_v2_message(self, event: dict) -> None:
        if event.get("exclude_user_id") == self.user_id:
            return
        await self.send(
            text_data=json.dumps(
                {
                    "type": "MESSAGE",
                    "room_id": event["room_id"],
                    "seq": event["seq"],
                    "message_id": event["message_id"],
                    "sender_id": event["sender_id"],
                    "sender_name": event["sender_name"],
                    "content": event["content"],
                    "reply_to_seq": event.get("reply_to_seq"),
                    "mention_user_ids": event.get("mention_user_ids", []),
                    "attachment_urls": event.get("attachment_urls", []),
                    "is_edited": event.get("is_edited", False),
                    "created_at": event["created_at"],
                }
            )
        )

    async def chat_v2_thread_reply(self, event: dict) -> None:
        if event.get("exclude_user_id") == self.user_id:
            return
        await self.send(
            text_data=json.dumps(
                {
                    "type": "THREAD_REPLY",
                    "room_id": event["room_id"],
                    "parent_seq": event["parent_seq"],
                    "seq": event["seq"],
                    "message_id": event["message_id"],
                    "sender_id": event["sender_id"],
                    "sender_name": event["sender_name"],
                    "content": event["content"],
                    "mention_user_ids": event.get("mention_user_ids", []),
                    "created_at": event["created_at"],
                }
            )
        )

    async def chat_v2_reaction(self, event: dict) -> None:
        await self.send(
            text_data=json.dumps(
                {
                    "type": "REACTION",
                    "room_id": event["room_id"],
                    "target_seq": event["target_seq"],
                    "user_id": event["user_id"],
                    "user_name": event["user_name"],
                    "emoji": event["emoji"],
                    "remove": event.get("remove", False),
                }
            )
        )

    async def chat_v2_message_edited(self, event: dict) -> None:
        await self.send(
            text_data=json.dumps(
                {
                    "type": "MESSAGE_EDITED",
                    "room_id": event["room_id"],
                    "seq": event["seq"],
                    "content": event["content"],
                    "edited_at": event["edited_at"],
                }
            )
        )

    async def chat_v2_message_deleted(self, event: dict) -> None:
        await self.send(
            text_data=json.dumps(
                {
                    "type": "MESSAGE_DELETED",
                    "room_id": event["room_id"],
                    "seq": event["seq"],
                }
            )
        )

    async def chat_v2_typing(self, event: dict) -> None:
        await self.send(
            text_data=json.dumps(
                {
                    "type": "TYPING",
                    "room_id": event["room_id"],
                    "user_id": event["user_id"],
                    "user_name": event["user_name"],
                    "status": event["status"],
                }
            )
        )

    async def chat_v2_presence(self, event: dict) -> None:
        await self.send(
            text_data=json.dumps(
                {
                    "type": "PRESENCE",
                    "user_id": event["user_id"],
                    "status": event["status"],
                }
            )
        )

    # ── Helpers ─────────────────────────────────────────────────────────────

    async def _send_error(self, code: str, message: str) -> None:
        await self.send(
            text_data=json.dumps({"type": "ERROR", "code": code, "message": message})
        )

    async def _set_presence(self, status: str) -> None:
        redis = get_redis()
        if redis:
            redis.setex(f"presence:user:{self.user_id}", HEARTBEAT_TIMEOUT, status)

    async def _clear_presence(self) -> None:
        redis = get_redis()
        if redis:
            redis.delete(f"presence:user:{self.user_id}")

    @database_sync_to_async
    def _check_membership(self, room_id: str) -> bool:
        return RoomMember.objects.filter(
            room_id=room_id, user_id=self.user_id, deleted_at__isnull=True
        ).exists()

    @database_sync_to_async
    def _get_user_rooms(self) -> list[dict]:
        memberships = (
            RoomMember.objects.filter(user_id=self.user_id, deleted_at__isnull=True)
            .select_related("room")
            .order_by("-joined_at")
        )
        return [
            {
                "room_id": str(m.room_id),
                "room_type": m.room.room_type,
                "name": m.room.name,
                "last_seq": m.last_read_seq,
            }
            for m in memberships
        ]

    @database_sync_to_async
    @transaction.atomic
    def _update_room_metadata(
        self, room_id: str, content: str, sender_name: str
    ) -> None:
        Room.objects.filter(id=room_id).update(
            last_message_content=content,
            last_message_sender_name=sender_name,
            last_message_at=datetime.now(tz=UTC),
        )
        from django.db.models import F

        Room.objects.filter(id=room_id).update(message_count=F("message_count") + 1)

    @database_sync_to_async
    def _save_read_receipt(self, room_id: str, upto_seq: int) -> None:
        RoomMember.objects.update_or_create(
            room_id=room_id, user_id=self.user_id, defaults={"last_read_seq": upto_seq}
        )
