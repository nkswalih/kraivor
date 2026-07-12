"""Kafka event publishing for project and task domain events.

Architecture:
  - Events use a standardised envelope (``_build_envelope``) with ``event_id``,
    ``event_type``, ``source_service`` (always "core"), ``workspace_id``,
    ``user_id``, ``timestamp``, ``version`` ("1.0"), and ``data``.
  - Publication is wrapped in ``transaction.on_commit`` (except ``task.overdue``)
    so events are only emitted after the database transaction commits.
  - If Kafka is unavailable (``get_producer()`` returns ``None``), events are
    silently logged at INFO level as a dev fallback.

ADR: ``task.overdue`` bypasses ``transaction.on_commit`` because it is published
from a Celery task that runs outside any active database transaction.
"""

import json

import logging
import uuid
from datetime import UTC, datetime
from django.db import transaction

logger = logging.getLogger(__name__)

KAFKA_FLUSH_TIMEOUT_SECONDS = 2.0


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _build_envelope(
    event_type: str, workspace_id: str, user_id: str, data: dict
) -> dict:
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "source_service": "core",
        "workspace_id": str(workspace_id),
        "user_id": str(user_id),
        "timestamp": _now_iso(),
        "version": "1.0",
        "data": data,
    }


def _publish(topic: str, payload: dict) -> None:
    try:
        from core.infrastructure.kafka import get_producer

        producer = get_producer()
        if producer is None:
            logger.info(
                "event.dev_fallback",
                extra={"topic": topic, "event_type": payload.get("event_type")},
            )
            return

        producer.produce(
            topic=topic,
            key=payload.get("workspace_id", "unknown").encode("utf-8"),
            value=json.dumps(payload, default=str).encode("utf-8"),
        )
        producer.flush(timeout=KAFKA_FLUSH_TIMEOUT_SECONDS)

        logger.debug(
            "event.published",
            extra={
                "topic": topic,
                "event_type": payload.get("event_type"),
                "workspace_id": payload.get("workspace_id"),
            },
        )
    except Exception as exc:
        logger.error(
            "event.publish.failed",
            extra={
                "topic": topic,
                "event_type": payload.get("event_type"),
                "error": str(exc),
            },
        )


class ProjectEventPublisher:
    """Publishes project lifecycle events (created, updated, archived) to ``project.events`` topic."""

    TOPIC = "project.events"

    @staticmethod
    def publish_project_created(project, user_id: str) -> None:
        payload = _build_envelope(
            event_type="project.created",
            workspace_id=project.workspace_id,
            user_id=user_id,
            data={
                "project_id": str(project.id),
                "name": project.name,
                "status": project.status,
                "workspace_id": str(project.workspace_id),
            },
        )
        transaction.on_commit(lambda: _publish(ProjectEventPublisher.TOPIC, payload))

    @staticmethod
    def publish_project_updated(project, user_id: str) -> None:
        payload = _build_envelope(
            event_type="project.updated",
            workspace_id=project.workspace_id,
            user_id=user_id,
            data={
                "project_id": str(project.id),
                "name": project.name,
                "status": project.status,
                "workspace_id": str(project.workspace_id),
            },
        )
        transaction.on_commit(lambda: _publish(ProjectEventPublisher.TOPIC, payload))

    @staticmethod
    def publish_project_archived(project, user_id: str) -> None:
        payload = _build_envelope(
            event_type="project.archived",
            workspace_id=project.workspace_id,
            user_id=user_id,
            data={
                "project_id": str(project.id),
                "name": project.name,
                "workspace_id": str(project.workspace_id),
            },
        )
        transaction.on_commit(lambda: _publish(ProjectEventPublisher.TOPIC, payload))


class TaskEventPublisher:
    """Publishes task domain events (created, assigned, completed, blocked, overdue) to ``task.events``."""

    TOPIC = "task.events"

    @staticmethod
    def publish_task_created(task, user_id: str) -> None:
        payload = _build_envelope(
            event_type="task.created",
            workspace_id=task.project.workspace_id,
            user_id=user_id,
            data={
                "task_id": str(task.id),
                "title": task.title,
                "status": task.status,
                "priority": task.priority,
                "task_type": task.task_type,
                "project_id": str(task.project_id),
                "workspace_id": str(task.project.workspace_id),
                "assignee_id": str(task.assignee_id) if task.assignee_id else None,
            },
        )
        transaction.on_commit(lambda: _publish(TaskEventPublisher.TOPIC, payload))

    @staticmethod
    def publish_task_assigned(task, assigned_by: str) -> None:
        payload = _build_envelope(
            event_type="task.assigned",
            workspace_id=task.project.workspace_id,
            user_id=assigned_by,
            data={
                "task_id": str(task.id),
                "title": task.title,
                "project_id": str(task.project_id),
                "workspace_id": str(task.project.workspace_id),
                "assignee_id": str(task.assignee_id),
                "assigned_by": assigned_by,
            },
        )
        transaction.on_commit(lambda: _publish(TaskEventPublisher.TOPIC, payload))

    @staticmethod
    def publish_task_completed(task, user_id: str) -> None:
        payload = _build_envelope(
            event_type="task.completed",
            workspace_id=task.project.workspace_id,
            user_id=user_id,
            data={
                "task_id": str(task.id),
                "title": task.title,
                "project_id": str(task.project_id),
                "workspace_id": str(task.project.workspace_id),
                "completed_by": user_id,
            },
        )
        transaction.on_commit(lambda: _publish(TaskEventPublisher.TOPIC, payload))

    @staticmethod
    def publish_task_blocked(task, user_id: str) -> None:
        payload = _build_envelope(
            event_type="task.blocked",
            workspace_id=task.project.workspace_id,
            user_id=user_id,
            data={
                "task_id": str(task.id),
                "title": task.title,
                "priority": task.priority,
                "project_id": str(task.project_id),
                "workspace_id": str(task.project.workspace_id),
                "assignee_id": str(task.assignee_id) if task.assignee_id else None,
            },
        )
        transaction.on_commit(lambda: _publish(TaskEventPublisher.TOPIC, payload))

    @staticmethod
    def publish_task_overdue(task) -> None:
        payload = _build_envelope(
            event_type="task.overdue",
            workspace_id=task.project.workspace_id,
            user_id="system",
            data={
                "task_id": str(task.id),
                "title": task.title,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "priority": task.priority,
                "project_id": str(task.project_id),
                "workspace_id": str(task.project.workspace_id),
                "assignee_id": str(task.assignee_id) if task.assignee_id else None,
            },
        )
        _publish(TaskEventPublisher.TOPIC, payload)
