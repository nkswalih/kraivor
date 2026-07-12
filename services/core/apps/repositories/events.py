"""
Repository event publisher — KRV-021.

Publishes domain events to Kafka topic: repository.events
Event schema follows platform standard (system design §14).

Events:
  repository.connected    — repository linked to a workspace
  repository.disconnected — repository unlinked from a workspace

Publishing contract:
  - Fire-and-forget: failed publish NEVER rolls back the DB transaction
  - Events are registered via transaction.on_commit so they only fire
    after the DB write has durably committed
  - In dev (no Kafka), events are logged to stdout for visibility
"""

import json
from typing import TYPE_CHECKING

import logging
import uuid
from datetime import UTC, datetime

if TYPE_CHECKING:
    from .models import Repository

logger = logging.getLogger(__name__)

TOPIC_REPOSITORY = "repository.events"
KAFKA_FLUSH_TIMEOUT_SECONDS = 2.0


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _envelope(
    event_type: str, workspace_id: uuid.UUID, actor_id: uuid.UUID, data: dict
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


class RepositoryEventPublisher:
    """
    Stateless event publisher. Instantiate per-request.

    Kafka producer is fetched from the shared connection pool.
    In environments without Kafka (local dev without full docker-compose),
    falls back to structured logging so events are still visible.
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
            # Dev fallback — log the full event payload so developers can inspect it
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
            # Unflushed messages sit in the local producer buffer; Kafka
            # guarantees delivery on next flush or process exit.
            self._producer.flush(timeout=KAFKA_FLUSH_TIMEOUT_SECONDS)
            logger.debug(
                "event.published",
                extra={
                    "topic": topic,
                    "event_type": event_type,
                    "workspace_id": workspace_id,
                },
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

    # ── Repository events (KRV-021) ───────────────────────────────────────────

    def repository_connected(
        self, *, repository: "Repository", actor_id: uuid.UUID
    ) -> None:
        """
        Published after a repository is connected to a workspace.
        Consumed by: Analysis Service (schedule initial scan),
                     AI Service (queue repository indexing).
        """
        event = _envelope(
            event_type="repository.connected",
            workspace_id=repository.workspace_id,
            actor_id=actor_id,
            data={
                "repository_id": str(repository.id),
                "workspace_id": str(repository.workspace_id),
                "github_repo": repository.github_repo,
                "github_id": repository.github_id,
                "default_branch": repository.default_branch,
                "is_private": repository.is_private,
            },
        )
        self._publish(TOPIC_REPOSITORY, event)

    def repository_disconnected(
        self, *, repository: "Repository", actor_id: uuid.UUID
    ) -> None:
        """
        Published after a repository is disconnected from a workspace.
        Consumed by: Analysis Service (cancel/archive pending jobs),
                     AI Service (remove embeddings from vector store).
        """
        event = _envelope(
            event_type="repository.disconnected",
            workspace_id=repository.workspace_id,
            actor_id=actor_id,
            data={
                "repository_id": str(repository.id),
                "workspace_id": str(repository.workspace_id),
                "github_repo": repository.github_repo,
            },
        )
        self._publish(TOPIC_REPOSITORY, event)
