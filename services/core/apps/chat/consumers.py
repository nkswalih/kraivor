"""
WebSocket consumers for real-time chat, notifications, and presence.
"""

import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone

from core.infrastructure.redis import get_redis

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group = f"chat_{self.room_id}"
        self.user_id = self.scope.get("user_id")

        if not self.user_id:
            logger.warning("chat.connect.rejected.no_user")
            await self.close(code=4001)
            return

        # Join room group
        await self.channel_layer.group_add(self.room_group, self.channel_name)

        # Track presence in Redis
        await self._add_presence()

        await self.accept()
        logger.info(
            "chat.connect.accepted",
            extra={"room_id": self.room_id, "user_id": self.user_id},
        )

    async def disconnect(self, close_code):
        # Remove from presence set
        await self._remove_presence()

        # Leave room group
        await self.channel_layer.group_discard(self.room_group, self.channel_name)
        logger.info(
            "chat.disconnected",
            extra={
                "room_id": self.room_id,
                "user_id": self.user_id,
                "code": close_code,
            },
        )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"error": "invalid_json"}))
            return

        action = data.get("action", "message")

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

    async def chat_message(self, event):
        """Broadcast chat message to room."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "message",
                    "message_id": event["message_id"],
                    "sender_id": event["sender_id"],
                    "sender_name": event["sender_name"],
                    "content": event["content"],
                    "content_type": event["content_type"],
                    "reply_to": event.get("reply_to", ""),
                    "mentions": event.get("mentions", []),
                    "created_at": event["created_at"],
                }
            )
        )

    async def typing_event(self, event):
        """Broadcast typing indicator."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": event["event_type"],
                    "user_id": event["user_id"],
                    "user_name": event["user_name"],
                }
            )
        )

    async def presence_update(self, event):
        """Broadcast presence change."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "presence",
                    "user_id": event["user_id"],
                    "status": event["status"],
                }
            )
        )

    async def _handle_message(self, data):
        content = data.get("content", "").strip()
        if not content:
            return

        import uuid
        from datetime import UTC, datetime

        message_id = str(uuid.uuid4())
        now = datetime.now(tz=UTC).isoformat()
        mentions = data.get("mentions", [])

        # Broadcast to room group
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

        # Persist to DynamoDB via Celery
        from apps.chat.tasks import persist_to_dynamodb

        persist_to_dynamodb.delay(
            room_id=self.room_id,
            sender_id=self.user_id,
            sender_name=self.scope.get("user_name", ""),
            content=content,
            content_type=data.get("content_type", "text"),
            reply_to=data.get("reply_to"),
            mentions=mentions,
        )

        # Trigger AI response if AI bot mentioned
        if "ai" in mentions or "assistant" in mentions:
            from apps.chat.tasks import trigger_ai_response

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

    async def _handle_typing(self, data, event_type):
        await self.channel_layer.group_send(
            self.room_group,
            {
                "type": "typing_event",
                "event_type": event_type,
                "user_id": self.user_id,
                "user_name": self.scope.get("user_name", ""),
            },
        )

    async def _handle_mark_read(self, data):
        message_id = data.get("message_id")
        if not message_id:
            return
        await self.channel_layer.group_send(
            self.room_group,
            {"type": "chat_message", "message_id": message_id, "read_by": self.user_id},
        )

    async def _handle_delete(self, data):
        message_id = data.get("message_id")
        if not message_id:
            return
        from apps.chat.dynamodb import delete_message

        delete_message(self.room_id, message_id)
        await self.channel_layer.group_send(
            self.room_group,
            {
                "type": "chat_message",
                "message_id": message_id,
                "deleted": True,
                "sender_id": self.user_id,
            },
        )

    async def _add_presence(self):
        redis = get_redis()
        if redis:
            key = f"presence:room:{self.room_id}"
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

    async def _remove_presence(self):
        redis = get_redis()
        if redis:
            key = f"presence:room:{self.room_id}"
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
    async def connect(self):
        self.user_id = self.scope.get("user_id")
        if not self.user_id:
            await self.close(code=4001)
            return

        self.notification_group = f"notify_user_{self.user_id}"
        await self.channel_layer.group_add(self.notification_group, self.channel_name)
        await self.accept()
        logger.info("notif.connect.accepted", extra={"user_id": self.user_id})

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.notification_group, self.channel_name
        )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        action = data.get("action")
        if action == "mark_read":
            await self._mark_read(data.get("notification_id"))
        elif action == "mark_all_read":
            await self._mark_all_read()
        elif action == "dismiss":
            await self._dismiss(data.get("notification_id"))

    async def send_notification(self, event):
        """Send notification payload to the client."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "notification",
                    "id": event["id"],
                    "notification_type": event["notification_type"],
                    "title": event["title"],
                    "body": event["body"],
                    "link": event.get("link", ""),
                    "workspace_id": event.get("workspace_id", ""),
                    "actor_id": event.get("actor_id", ""),
                    "created_at": event["created_at"],
                }
            )
        )

    @database_sync_to_async
    def _mark_read(self, notification_id):
        from apps.notifications.models import Notification

        Notification.objects.filter(id=notification_id, user_id=self.user_id).update(
            read_at=timezone.now()
        )

    @database_sync_to_async
    def _mark_all_read(self):
        from apps.notifications.models import Notification

        Notification.objects.filter(user_id=self.user_id, read_at__isnull=True).update(
            read_at=timezone.now()
        )

    @database_sync_to_async
    def _dismiss(self, notification_id):
        from apps.notifications.models import Notification

        Notification.objects.filter(id=notification_id, user_id=self.user_id).delete()


class PresenceConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope.get("user_id")
        if not self.user_id:
            await self.close(code=4001)
            return

        self.presence_key = f"presence:user:{self.user_id}"
        redis = get_redis()
        if redis:
            redis.setex(self.presence_key, 60, "online")

        await self.accept()
        logger.debug("presence.connect", extra={"user_id": self.user_id})

    async def disconnect(self, close_code):
        redis = get_redis()
        if redis:
            redis.delete(self.presence_key)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        if data.get("action") == "heartbeat":
            redis = get_redis()
            if redis:
                redis.expire(self.presence_key, 60)
