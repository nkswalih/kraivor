"""
Knowledge Space event publisher — KRV-022.

Publishes domain events to Kafka topic: knowledge.events
Event schema follows platform standard (system design §14).

Events:
  knowledge.created — knowledge space created
  knowledge.updated — canvas data or metadata updated
  knowledge.deleted — knowledge space soft-deleted

Publishing contract:
  - Fire-and-forget: failed publish NEVER rolls back the DB transaction
  - Events are registered via transaction.on_commit so they only fire
    after the DB write has durably committed
  - In dev (no Kafka), events are logged to stdout for visibility
"""

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import KnowledgeSpace

logger = logging.getLogger(__name__)

TOPIC_KNOWLEDGE = "knowledge.events"
KAFKA_FLUSH_TIMEOUT_SECONDS = 2.0


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _envelope(
    event_type: str,
    workspace_id: uuid.UUID,
    actor_id: uuid.UUID,
    data: dict,
) -> dict:
    """
    Standard platform event envelope (system design §14).
    All events share the same outer shape — consumers route on event_type
    without needing to parse the inner data payload.
    """
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


class KnowledgeEventPublisher:
    """
    Stateless event publisher. Instantiate per-request.

    Kafka producer is fetched from the shared connection pool.
    Falls back to structured logging when Kafka is unavailable (local dev).
    """

    def __init__(self):
        self._producer = self._get_producer()

    # ── Infrastructure ────────────────────────────────────────────────────────

    def _get_producer(self):
        try:
            from core.infrastructure.kafka import get_producer

            return get_producer()
        except (ImportError, Exception) as exc:
            logger.warning("kafka.producer.unavailable", extra={"reason": str(exc)})
            return None

    def _publish(self, topic: str, event: dict) -> None:
        event_type = event.get("event_type", "unknown")
        workspace_id = event.get("workspace_id", "unknown")

        if self._producer is None:
            logger.info(
                "event.published.dev_fallback",
                extra={"topic": topic, "event_type": event_type, "payload": event},
            )
            return

        try:
            self._producer.produce(
                topic=topic,
                key=workspace_id.encode("utf-8"),
                value=json.dumps(event, default=str).encode("utf-8"),
            )
            # Short flush timeout — never block the request on Kafka latency.
            self._producer.flush(timeout=KAFKA_FLUSH_TIMEOUT_SECONDS)
            logger.debug(
                "event.published",
                extra={"topic": topic, "event_type": event_type, "workspace_id": workspace_id},
            )
        except Exception as exc:
            # IMPORTANT: log and continue — event failure must never crash a request
            logger.error(
                "event.publish.failed",
                extra={
                    "topic": topic,
                    "event_type": event_type,
                    "workspace_id": workspace_id,
                    "error": str(exc),
                },
            )

    # ── Knowledge Space events (KRV-022) ──────────────────────────────────────

    def knowledge_created(
        self,
        *,
        knowledge_space: "KnowledgeSpace",
        actor_id: uuid.UUID,
    ) -> None:
        """
        Published after a knowledge space is created.
        Consumed by: Notifications (team activity feed), Analytics.
        """
        event = _envelope(
            event_type="knowledge.created",
            workspace_id=knowledge_space.workspace_id,
            actor_id=actor_id,
            data={
                "knowledge_space_id": str(knowledge_space.id),
                "workspace_id": str(knowledge_space.workspace_id),
                "name": knowledge_space.name,
                "created_by": str(actor_id),
            },
        )
        self._publish(TOPIC_KNOWLEDGE, event)

    def knowledge_updated(
        self,
        *,
        knowledge_space: "KnowledgeSpace",
        actor_id: uuid.UUID,
    ) -> None:
        """
        Published after a knowledge space's metadata or canvas_data is updated.
        Consumed by: Realtime (live collaboration cursor/presence updates),
                     Analytics.
        """
        event = _envelope(
            event_type="knowledge.updated",
            workspace_id=knowledge_space.workspace_id,
            actor_id=actor_id,
            data={
                "knowledge_space_id": str(knowledge_space.id),
                "workspace_id": str(knowledge_space.workspace_id),
                "name": knowledge_space.name,
                "updated_by": str(actor_id),
            },
        )
        self._publish(TOPIC_KNOWLEDGE, event)

    def knowledge_deleted(
        self,
        *,
        knowledge_space: "KnowledgeSpace",
        actor_id: uuid.UUID,
    ) -> None:
        """
        Published after a knowledge space is soft-deleted.
        Consumed by: AI Service (remove canvas embeddings if indexed),
                     Analytics.
        """
        event = _envelope(
            event_type="knowledge.deleted",
            workspace_id=knowledge_space.workspace_id,
            actor_id=actor_id,
            data={
                "knowledge_space_id": str(knowledge_space.id),
                "workspace_id": str(knowledge_space.workspace_id),
                "name": knowledge_space.name,
                "deleted_by": str(actor_id),
            },
        )
        self._publish(TOPIC_KNOWLEDGE, event)
