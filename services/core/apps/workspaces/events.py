"""
Workspace event publisher.

Publishes domain events to Kafka after state changes.
Consumed by: Analysis Service, AI Service, Notification Service, Realtime Service.

Event schema follows the platform standard (system design §14):
  {
    event_id:       uuid
    event_type:     string
    source_service: "core"
    workspace_id:   uuid
    user_id:        uuid
    timestamp:      ISO-8601
    version:        "1.0"
    data:           { ... }
  }

Publishing is fire-and-forget from the service's perspective.
Kafka's durability guarantees delivery even if consumers are temporarily down.
Failed publishes are logged but do NOT roll back the database transaction —
the database is the source of truth; events are downstream notifications.
"""

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Workspace, WorkspaceMember

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _envelope(event_type: str, workspace_id: uuid.UUID, actor_id: uuid.UUID, data: dict) -> dict:
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "source_service": "core",
        "workspace_id": str(workspace_id),
        "user_id": str(actor_id),
        "timestamp": _now_iso(),
        "version": "1.0",
        "data": data,
    }


class WorkspaceEventPublisher:
    """
    Publishes workspace domain events to Kafka.

    In development (KAFKA_BOOTSTRAP_SERVERS not set), events are logged only.
    In production, uses the shared Kafka producer from core.infrastructure.kafka.
    """

    def __init__(self):
        self._producer = self._get_producer()

    def _get_producer(self):
        """
        Lazily initialize Kafka producer.
        Returns None in environments without Kafka (dev without Docker).
        """
        try:
            from core.infrastructure.kafka import get_producer
            return get_producer()
        except (ImportError, Exception) as e:
            logger.warning(
                "kafka.producer.unavailable",
                extra={"reason": str(e)},
            )
            return None

    def _publish(self, topic: str, event: dict) -> None:
        event_type = event.get("event_type", "unknown")
        workspace_id = event.get("workspace_id", "unknown")

        if self._producer is None:
            logger.info(
                "event.published.local",
                extra={
                    "topic": topic,
                    "event_type": event_type,
                    "workspace_id": workspace_id,
                    "event": event,
                },
            )
            return

        try:
            self._producer.produce(
                topic=topic,
                key=workspace_id.encode("utf-8"),
                value=json.dumps(event).encode("utf-8"),
            )
            self._producer.flush(timeout=2.0)  # non-blocking with short timeout
        except Exception as e:
            # Do NOT raise — event failure must not roll back DB transaction
            logger.error(
                "event.publish.failed",
                extra={
                    "topic": topic,
                    "event_type": event_type,
                    "workspace_id": workspace_id,
                    "error": str(e),
                },
            )

    def workspace_created(self, *, workspace: "Workspace", actor_id: uuid.UUID) -> None:
        event = _envelope(
            event_type="workspace.created",
            workspace_id=workspace.id,
            actor_id=actor_id,
            data={
                "workspace_id": str(workspace.id),
                "name": workspace.name,
                "slug": workspace.slug,
                "plan": workspace.plan,
                "owner_id": str(workspace.owner_id),
            },
        )
        self._publish("workspace.events", event)

    def workspace_deleted(self, *, workspace: "Workspace", actor_id: uuid.UUID) -> None:
        event = _envelope(
            event_type="workspace.deleted",
            workspace_id=workspace.id,
            actor_id=actor_id,
            data={
                "workspace_id": str(workspace.id),
                "slug": workspace.slug,
            },
        )
        self._publish("workspace.events", event)

    def member_added(
        self, *, workspace: "Workspace", member: "WorkspaceMember", actor_id: uuid.UUID
    ) -> None:
        event = _envelope(
            event_type="workspace.member.invited",
            workspace_id=workspace.id,
            actor_id=actor_id,
            data={
                "workspace_id": str(workspace.id),
                "user_id": str(member.user_id),
                "role": member.role,
            },
        )
        self._publish("workspace.events", event)