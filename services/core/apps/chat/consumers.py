"""
WebSocket consumers for real-time chat, notifications, and presence.
"""

import json

import asyncio
import html
import logging
import uuid
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from datetime import UTC, datetime
from django.utils import timezone

from apps.chat.dynamodb import delete_message as dynamodb_delete_message
from apps.chat.services import ChatRoomService
from apps.chat.tasks import persist_to_dynamodb, trigger_ai_response
from apps.notifications.tasks import dispatch_notification as dispatch_notification_task
from core.infrastructure.redis import get_redis

logger = logging.getLogger(__name__)


def select_ws_subprotocol(scope: dict) -> str | None:
    """Echo the web client's ``auth`` subprotocol, when it offered one.

    The client passes the JWT as a WebSocket subprotocol (``['auth', token]``)
    to keep it out of the URL. RFC 6455 requires the server to *select* one of
    the offered protocols — when it selects none, the browser treats the
    handshake as failed and closes the socket milliseconds after ``accept()``.
    That is exactly what happened here: every connection was accepted and
    immediately dropped, the client retried ten times and gave up, and no
    presence broadcast ever survived. Clients that offer no subprotocol
    (server-to-server, tests) are unaffected.
    """
    offered = scope.get("subprotocols") or []
    return "auth" if "auth" in offered else None


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self) -> None:
        self.room_id: str = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group: str = f"chat_{self.room_id}"
        self.user_id: str | None = self.scope.get("user_id")

        if not self.user_id:
            logger.warning("chat.connect.rejected.no_user")
            await self.close(code=4001)
            return

        await self.channel_layer.group_add(self.room_group, self.channel_name)
        await self._add_presence()
        await database_sync_to_async(ChatRoomService.mark_room_read)(
            room_id=self.room_id, user_id=self.user_id
        )
        await self.accept(subprotocol=select_ws_subprotocol(self.scope))
        logger.info(
            "chat.connect.accepted",
            extra={"room_id": self.room_id, "user_id": self.user_id},
        )

    async def disconnect(self, close_code: int) -> None:
        await self._remove_presence()
        await self.channel_layer.group_discard(self.room_group, self.channel_name)
        logger.info(
            "chat.disconnected",
            extra={
                "room_id": self.room_id,
                "user_id": self.user_id,
                "code": close_code,
            },
        )

    async def receive(self, text_data: str) -> None:
        try:
            data: dict = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"error": "invalid_json"}))
            return

        action: str = data.get("action", "message")

        if action == "message":
            await self._handle_message(data)
        elif action == "typing.start":
            await self._handle_typing(data, "typing.start")
        elif action == "typing.stop":
            await self._handle_typing(data, "typing.stop")
        elif action == "mark_read":
            await self._handle_mark_read(data)
        elif action == "delete":
            await self._handle_delete(data)
        else:
            await self.send(
                text_data=json.dumps({"error": f"unknown_action: {action}"})
            )

    async def chat_message(self, event: dict) -> None:
        content: str = html.escape(event.get("content", ""))
        await self.send(
            text_data=json.dumps(
                {
                    "type": "message",
                    "message_id": event["message_id"],
                    "sender_id": event["sender_id"],
                    "sender_name": event["sender_name"],
                    "content": content,
                    "content_type": event["content_type"],
                    "reply_to": event.get("reply_to", ""),
                    "mentions": event.get("mentions", []),
                    "created_at": event["created_at"],
                }
            )
        )

    async def typing_event(self, event: dict) -> None:
        await self.send(
            text_data=json.dumps(
                {
                    "type": event["event_type"],
                    "user_id": event["user_id"],
                    "user_name": event["user_name"],
                }
            )
        )

    async def presence_update(self, event: dict) -> None:
        await self.send(
            text_data=json.dumps(
                {
                    "type": "presence",
                    "user_id": event["user_id"],
                    "status": event["status"],
                }
            )
        )

    async def _update_last_message(
        self, room_id: str, content: str, sender_name: str
    ) -> None:
        await database_sync_to_async(ChatRoomService.update_last_message)(
            room_id=room_id, content=content, sender_name=sender_name
        )
        await database_sync_to_async(ChatRoomService.increment_message_count)(
            room_id=room_id
        )

    async def _handle_message(self, data: dict) -> None:
        content: str = html.escape(data.get("content", "").strip())
        if not content:
            return

        message_id: str = str(uuid.uuid4())
        now: str = datetime.now(tz=UTC).isoformat()
        mentions: list[str] = data.get("mentions", [])

        await self._update_last_message(
            room_id=self.room_id,
            content=content,
            sender_name=self.scope.get("user_name", ""),
        )

        await self.channel_layer.group_send(
            self.room_group,
            {
                "type": "chat_message",
                "message_id": message_id,
                "sender_id": self.user_id,
                "sender_name": self.scope.get("user_name", ""),
                "content": content,
                "content_type": data.get("content_type", "text"),
                "reply_to": data.get("reply_to", ""),
                "mentions": mentions,
                "created_at": now,
            },
        )

        persist_to_dynamodb.delay(
            room_id=self.room_id,
            sender_id=self.user_id,
            sender_name=self.scope.get("user_name", ""),
            content=content,
            content_type=data.get("content_type", "text"),
            reply_to=data.get("reply_to"),
            mentions=mentions,
        )

        if "ai" in mentions or "assistant" in mentions:
            trigger_ai_response.delay(
                room_id=self.room_id,
                message_id=message_id,
                content=content,
                workspace_id=(
                    self.scope.get("workspace_ids", [None])[0]
                    if self.scope.get("workspace_ids")
                    else ""
                ),
            )

        for mentioned_user_id in mentions:
            if mentioned_user_id and mentioned_user_id != self.user_id:
                dispatch_notification_task.delay(
                    user_id=mentioned_user_id,
                    notification_type="chat.mention",
                    title=f"{self.scope.get('user_name', 'Someone')} mentioned you",
                    body=content[:200],
                    link=f"/chat/{self.room_id}",
                    workspace_id=(
                        self.scope.get("workspace_ids", [None])[0]
                        if self.scope.get("workspace_ids")
                        else None
                    ),
                    actor_id=self.user_id,
                )

    async def _handle_typing(self, data: dict, event_type: str) -> None:
        await self.channel_layer.group_send(
            self.room_group,
            {
                "type": "typing_event",
                "event_type": event_type,
                "user_id": self.user_id,
                "user_name": self.scope.get("user_name", ""),
            },
        )

    async def _handle_mark_read(self, data: dict) -> None:
        message_id: str | None = data.get("message_id")
        if not message_id or not self.user_id:
            return
        await database_sync_to_async(ChatRoomService.mark_room_read)(
            room_id=self.room_id, user_id=self.user_id
        )
        await self.channel_layer.group_send(
            self.room_group,
            {"type": "chat_message", "message_id": message_id, "read_by": self.user_id},
        )

    async def _handle_delete(self, data: dict) -> None:
        message_id: str | None = data.get("message_id")
        if not message_id:
            return
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, dynamodb_delete_message, self.room_id, message_id
        )
        await self.channel_layer.group_send(
            self.room_group,
            {
                "type": "chat_message",
                "message_id": message_id,
                "deleted": True,
                "sender_id": self.user_id,
            },
        )

    async def _add_presence(self) -> None:
        redis = get_redis()
        if redis:
            key: str = f"presence:room:{self.room_id}"
            redis.sadd(key, self.user_id)
            redis.expire(key, 120)
            await self.channel_layer.group_send(
                self.room_group,
                {
                    "type": "presence_update",
                    "user_id": self.user_id,
                    "status": "online",
                },
            )

    async def _remove_presence(self) -> None:
        redis = get_redis()
        if redis:
            key: str = f"presence:room:{self.room_id}"
            redis.srem(key, self.user_id)
            await self.channel_layer.group_send(
                self.room_group,
                {
                    "type": "presence_update",
                    "user_id": self.user_id,
                    "status": "offline",
                },
            )


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self) -> None:
        self.user_id: str | None = self.scope.get("user_id")
        if not self.user_id:
            await self.close(code=4001)
            return

        self.notification_group: str = f"notify_user_{self.user_id}"
        await self.channel_layer.group_add(self.notification_group, self.channel_name)
        await self.accept(subprotocol=select_ws_subprotocol(self.scope))
        logger.info("notif.connect.accepted", extra={"user_id": self.user_id})

    async def disconnect(self, close_code: int) -> None:
        await self.channel_layer.group_discard(
            self.notification_group, self.channel_name
        )

    async def receive(self, text_data: str) -> None:
        try:
            data: dict = json.loads(text_data)
        except json.JSONDecodeError:
            return

        action: str | None = data.get("action")
        if action == "mark_read":
            await self._mark_read(data.get("notification_id"))
        elif action == "mark_all_read":
            await self._mark_all_read()
        elif action == "dismiss":
            await self._dismiss(data.get("notification_id"))

    async def send_notification(self, event: dict) -> None:
        await self.send(
            text_data=json.dumps(
                {
                    "type": "notification",
                    "id": event["id"],
                    "notification_type": event["notification_type"],
                    "title": event["title"],
                    "body": event["body"],
                    "link": event.get("link", ""),
                    "metadata": event.get("metadata", {}),
                    "workspace_id": event.get("workspace_id", ""),
                    "actor_id": event.get("actor_id", ""),
                    "created_at": event["created_at"],
                }
            )
        )

    @database_sync_to_async
    def _mark_read(self, notification_id: str) -> None:
        from apps.notifications.models import Notification

        Notification.objects.filter(id=notification_id, user_id=self.user_id).update(
            read_at=timezone.now()
        )

    @database_sync_to_async
    def _mark_all_read(self) -> None:
        from apps.notifications.models import Notification

        Notification.objects.filter(user_id=self.user_id, read_at__isnull=True).update(
            read_at=timezone.now()
        )

    @database_sync_to_async
    def _dismiss(self, notification_id: str) -> None:
        from apps.notifications.models import Notification

        Notification.objects.filter(id=notification_id, user_id=self.user_id).delete()


class PresenceConsumer(AsyncWebsocketConsumer):
    """App-level presence: one live socket marks the user online.

    This replaces the room-scoped broadcast that used to feed the members
    rail: a workspace member sitting in another room (or on any other page)
    read as offline. Online now means "has a session open somewhere in the
    dashboard", which is what a workspace members list should show.

    Two guarantees the old flow lacked:

    * **Roster on connect** — presence used to broadcast transitions only,
      so anyone who connected before you stayed invisible until they
      happened to reconnect. The joiner now receives the current online set
      as a ``presence.sync`` frame.
    * **Sticky across tabs** — online-ness is a per-user connection counter
      with a TTL, so a second tab does not flip the user offline when the
      first one closes, and a crashed session expires on its own instead of
      haunting the rail.

    Keys (all self-expiring; the client heartbeats every 30s):
        presence:conn:{user_id} -> open socket count (integer)
    """

    GROUP = "ws_presence"
    PRESENCE_TTL = 60  # seconds; client heartbeat interval is half this

    async def connect(self) -> None:
        self.user_id: str | None = self.scope.get("user_id")
        if not self.user_id:
            await self.close(code=4001)
            return

        self.conn_key: str = f"presence:conn:{self.user_id}"
        await self.channel_layer.group_add(self.GROUP, self.channel_name)

        first_connection = False
        redis = get_redis()
        if redis:
            connections = redis.incr(self.conn_key)
            redis.expire(self.conn_key, self.PRESENCE_TTL)
            first_connection = connections == 1

        await self.accept(subprotocol=select_ws_subprotocol(self.scope))

        # Roster first: tell the joiner who is *already* online.
        await self.send(
            text_data=json.dumps(
                {"type": "presence.sync", "user_ids": self._current_online(redis)}
            )
        )

        if first_connection:
            await self.channel_layer.group_send(
                self.GROUP,
                {
                    "type": "presence_event",
                    "user_id": self.user_id,
                    "status": "online",
                },
            )
        logger.info("presence.connect", extra={"user_id": self.user_id})

    async def disconnect(self, close_code: int) -> None:
        await self.channel_layer.group_discard(self.GROUP, self.channel_name)

        redis = get_redis()
        went_offline = False
        if redis:
            remaining = redis.decr(self.conn_key)
            if remaining <= 0:
                redis.delete(self.conn_key)
                went_offline = True

        if went_offline:
            await self.channel_layer.group_send(
                self.GROUP,
                {
                    "type": "presence_event",
                    "user_id": self.user_id,
                    "status": "offline",
                },
            )
        logger.info(
            "presence.disconnect", extra={"user_id": self.user_id, "code": close_code}
        )

    async def receive(self, text_data: str) -> None:
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        if data.get("action") == "heartbeat":
            redis = get_redis()
            if redis:
                redis.expire(self.conn_key, self.PRESENCE_TTL)

    @staticmethod
    def _current_online(redis) -> list[str]:
        if not redis:
            return []
        prefix = "presence:conn:"
        online: list[str] = []
        for key in redis.scan_iter(match=f"{prefix}*"):
            uid = key.decode() if isinstance(key, bytes) else key
            uid = uid.removeprefix(prefix)
            if uid:
                online.append(uid)
        return online

    async def presence_event(self, event: dict) -> None:
        await self.send(
            text_data=json.dumps(
                {
                    "type": "presence",
                    "user_id": event["user_id"],
                    "status": event["status"],
                }
            )
        )
