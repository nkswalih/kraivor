"""
Kafka consumer management command.

Listens to external service events (analysis, ai, workspace, community,
project, task, repository) and dispatches Celery tasks for notification delivery.

Usage:
    python manage.py consume_events

Subscribes to topics:
    - analysis.events  (analysis.completed, analysis.failed)
    - ai.events        (ai.index.completed, ai.analysis.completed)
    - workspace.events (workspace.member.invited)
    - community        (discussion.created, discussion.upvoted, comment.created)
    - project.events   (project.created, project.updated, project.archived)
    - task.events      (task.created, task.assigned, task.completed, task.blocked, task.overdue)
    - repository.events (repository.connected, repository.disconnected)

Events that Core publishes internally via transaction.on_commit() are the
primary delivery path. This Kafka consumer acts as a durable fallback —
it catches events that may have been missed if the on_commit handler
failed.
"""

import json
import time

import logging
import requests
import signal
import sys
from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

# ── Event type → Celery task dispatch map ──────────────────────────────────────

DISPATCH_TABLE: dict[str, str] = {
    # Analysis events
    "analysis.completed": "notifications.dispatch_notification",
    "analysis.failed": "notifications.dispatch_notification",
    # AI events
    "ai.index.completed": "notifications.dispatch_notification",
    "ai.analysis.completed": "notifications.dispatch_notification",
    # Profile events
    "profile.follow.new": "notifications.dispatch_notification",
    # Community events (single-user only — primary dispatch happens in service code)
    "discussion.upvoted": "notifications.dispatch_notification",
    "comment.created": "notifications.dispatch_notification",
    # Project events (single-user fallback — primary dispatch happens in service code)
    "project.created": "notifications.dispatch_notification",
    # Task events (single-user fallback — primary dispatch happens in service code)
    "task.assigned": "notifications.dispatch_notification",
    "task.completed": "notifications.dispatch_notification",
    "task.blocked": "notifications.dispatch_notification",
    "task.overdue": "notifications.dispatch_notification",
    # Repository events
    "repository.connected": "notifications.dispatch_notification",
    "repository.disconnected": "notifications.dispatch_notification",
}

# Fan-out events: dispatched to every member of the workspace (fallback)
FANOUT_EVENT_TYPES: set[str] = {
    "analysis.completed",
    "analysis.failed",
    "discussion.created",
    "project.created",
    "task.created",
    "repository.connected",
    "repository.disconnected",
}

# Workspace events are dispatched via a separate handler that
# resolves email → user_id via the Identity service.
WORKSPACE_EVENT_DISPATCH: dict[str, str] = {
    "workspace.member.invited": "notifications.dispatch_notification"
}

TOPICS = [
    "analysis.events",
    "ai.events",
    "workspace.events",
    "profiles",
    "community",
    "project.events",
    "task.events",
    "repository.events",
]
POLL_TIMEOUT = 1.0
_shutdown = False


def _signal_handler(signum, frame):
    global _shutdown
    logger.info("consumer.shutdown.signal_received", extra={"signal": signum})
    _shutdown = True


def _dispatch_task(event_type: str, data: dict) -> None:
    """Dispatch a Celery task based on the event type."""
    task_name = DISPATCH_TABLE.get(event_type)
    if not task_name:
        logger.debug("consumer.event.unknown_type", extra={"event_type": event_type})
        return

    user_id = data.get("user_id") or data.get("workspace_id")
    if not user_id:
        logger.warning("consumer.event.no_recipient", extra={"event_type": event_type})
        return

    from celery import current_app

    task = current_app.tasks.get(task_name)
    if task is None:
        logger.error("consumer.task.not_found", extra={"task_name": task_name})
        return

    title = _build_title(event_type, data)
    body = _build_body(event_type, data)
    metadata = _build_metadata(event_type, data)

    # Map event-specific actor_id fields
    actor_id = data.get("actor_id")
    if not actor_id and event_type == "profile.follow.new":
        actor_id = data.get("follower_id")

    task.delay(
        user_id=str(user_id),
        notification_type=event_type,
        title=title,
        body=body,
        link=data.get("link", ""),
        metadata=metadata,
        workspace_id=data.get("workspace_id"),
        actor_id=actor_id,
    )
    logger.info(
        "consumer.event.dispatched",
        extra={"event_type": event_type, "user_id": str(user_id)},
    )


def _dispatch_workspace_event(event_type: str, data: dict) -> None:
    """
    Dispatch a workspace event that needs email → user_id resolution.
    Workspace events carry an email (not a user_id) because the invited
    user may not have an account yet. This function resolves the email
    via the Identity service's internal API before dispatching.
    """
    task_name = WORKSPACE_EVENT_DISPATCH.get(event_type)
    if not task_name:
        logger.debug(
            "consumer.workspace_event.unknown_type", extra={"event_type": event_type}
        )
        return

    email = data.get("email")
    if not email:
        logger.warning(
            "consumer.workspace_event.no_email", extra={"event_type": event_type}
        )
        return

    # Resolve email → user_id via Identity service
    identity_url = getattr(settings, "IDENTITY_SERVICE_URL", "http://identity:8001")
    endpoint = f"{identity_url}/api/auth/internal/resolve-users/"

    try:
        response = requests.post(
            endpoint,
            json={"emails": [email]},
            headers={settings.INTERNAL_REQUEST_HEADER: settings.INTERNAL_REQUEST_SECRET},
            timeout=5,
        )
    except requests.exceptions.RequestException as exc:
        logger.warning(
            "consumer.workspace_event.resolve_failed",
            extra={"event_type": event_type, "email": email, "error": str(exc)},
        )
        return

    if response.status_code != 200:
        logger.warning(
            "consumer.workspace_event.resolve_error",
            extra={
                "event_type": event_type,
                "email": email,
                "status_code": response.status_code,
            },
        )
        return

    result = response.json()
    users = result.get("users", {})
    user_info = users.get(email)
    if not user_info:
        logger.debug(
            "consumer.workspace_event.user_not_found",
            extra={"event_type": event_type, "email": email},
        )
        return

    user_id = user_info["id"]
    from celery import current_app

    task = current_app.tasks.get(task_name)
    if task is None:
        logger.error("consumer.task.not_found", extra={"task_name": task_name})
        return

    workspace_name = data.get("workspace_name", "a workspace")
    invited_by_name = data.get("invited_by_name", "A team member")
    role = data.get("role", "member")
    accept_url = data.get("accept_url", "")
    # Extract token from accept_url: "https://kraivor.com/invitations/{token}"
    token = accept_url.rstrip("/").split("/")[-1] if accept_url else ""

    task.delay(
        user_id=str(user_id),
        notification_type=event_type,
        title=f"You've been invited to {workspace_name}",
        body=f"{invited_by_name} invited you to {workspace_name} as {role}.",
        link=f"/invitations/{token}",
        workspace_id=data.get("workspace_id"),
        actor_id=data.get("actor_id"),
    )
    logger.info(
        "consumer.workspace_event.dispatched",
        extra={"event_type": event_type, "user_id": user_id, "email": email},
    )


def _dispatch_fanout_event(event_type: str, data: dict) -> None:
    """
    Dispatch a workspace-wide fan-out notification (fallback path).

    Sends the notification to every active member of the workspace
    referenced in the event data.
    """
    workspace_id = data.get("workspace_id")
    if not workspace_id:
        logger.warning("consumer.fanout.no_workspace", extra={"event_type": event_type})
        return

    from apps.notifications.utils import fanout_to_workspace_members

    title = _build_title(event_type, data)
    body = _build_body(event_type, data)
    metadata = _build_metadata(event_type, data)

    exclude_user_id = data.get("actor_id") or data.get("user_id")
    notified = fanout_to_workspace_members(
        workspace_id=workspace_id,
        notification_type=event_type,
        title=title,
        body=body,
        link=data.get("link", ""),
        metadata=metadata,
        actor_id=str(exclude_user_id) if exclude_user_id else None,
        exclude_user_id=str(exclude_user_id) if exclude_user_id else None,
    )
    logger.info(
        "consumer.fanout.dispatched",
        extra={
            "event_type": event_type,
            "workspace_id": workspace_id,
            "notified": notified,
        },
    )


def _build_title(event_type: str, data: dict) -> str:
    titles = {
        "analysis.completed": "Analysis Complete",
        "analysis.failed": "Analysis Failed",
        "ai.index.completed": "Indexing Complete",
        "ai.analysis.completed": "AI Analysis Complete",
        "profile.follow.new": "New Follower",
        "discussion.created": f"New Discussion: {data.get('title', '')}",
        "discussion.upvoted": "Your discussion was upvoted",
        "comment.created": "New comment on your discussion",
        "project.created": f"New Project: {data.get('project_name', '')}",
        "task.created": f"New Task: {data.get('title', '')}",
        "task.assigned": f"Task assigned: {data.get('title', '')}",
        "task.completed": f"Task completed: {data.get('title', '')}",
        "task.blocked": f"Task blocked: {data.get('title', '')}",
        "task.overdue": f"Task overdue: {data.get('title', '')}",
        "repository.connected": f"Repository connected: {data.get('name', '')}",
        "repository.disconnected": f"Repository disconnected: {data.get('name', '')}",
    }
    return titles.get(event_type, f"Event: {event_type}")


def _build_body(event_type: str, data: dict) -> str:
    bodies = {
        "analysis.completed": f"Repository {data.get('github_repo', '')} analysis is complete.",
        "analysis.failed": f"Repository analysis failed: {data.get('error', 'Unknown error')}",
        "ai.index.completed": f"Repository {data.get('github_repo', '')} has been indexed.",
        "ai.analysis.completed": f"AI analysis report is ready for {data.get('github_repo', '')}.",
        "profile.follow.new": f"{data.get('follower_username', 'Someone')} started following you.",
        "discussion.created": f"A new discussion '{data.get('title', '')}' was created.",
        "discussion.upvoted": "Someone upvoted your discussion.",
        "comment.created": "Someone commented on your discussion.",
        "project.created": f"Project '{data.get('project_name', '')}' was created in your workspace.",
        "task.created": f"Task '{data.get('title', '')}' was created with priority {data.get('priority', 'medium')}.",
        "task.assigned": f"You were assigned task '{data.get('title', '')}'.",
        "task.completed": f"Task '{data.get('title', '')}' has been completed.",
        "task.blocked": f"Task '{data.get('title', '')}' is blocked.",
        "task.overdue": f"Task '{data.get('title', '')}' is overdue.",
        "repository.connected": f"Repository '{data.get('name', '')}' has been connected.",
        "repository.disconnected": f"Repository '{data.get('name', '')}' has been disconnected.",
    }
    return bodies.get(event_type, json.dumps(data))


def _build_metadata(event_type: str, data: dict) -> dict:
    """Build structured metadata for task/analysis/follow notifications."""
    metadata = {}
    if event_type == "profile.follow.new":
        metadata["follower_id"] = data.get("follower_id", "")
        metadata["follower_username"] = data.get("follower_username", "")
    if event_type.startswith("task.") or event_type == "task.created":
        metadata["status"] = data.get("status", "")
        metadata["priority"] = data.get("priority", "medium")
        metadata["task_id"] = data.get("task_id", "")
        metadata["project_id"] = data.get("project_id", "")
        metadata["assignee_id"] = data.get("assignee_id", "")
    if event_type.startswith("analysis."):
        metadata["github_repo"] = data.get("github_repo", "")
        metadata["status"] = "completed" if "completed" in event_type else "failed"
    if event_type.startswith("repository."):
        metadata["repository_id"] = data.get("repository_id", "")
        metadata["name"] = data.get("name", "")
    if event_type == "project.created":
        metadata["project_name"] = data.get("project_name", "")
        metadata["project_status"] = data.get("status", "planning")
    return metadata


class Command(BaseCommand):
    help = "Consume Kafka events from analysis/ai topics and dispatch Celery tasks"

    def add_arguments(self, parser):
        parser.add_argument(
            "--topics",
            nargs="+",
            default=TOPICS,
            help="Kafka topics to subscribe to (default: analysis.events ai.events)",
        )
        parser.add_argument(
            "--poll-timeout",
            type=float,
            default=POLL_TIMEOUT,
            help=f"Consumer poll timeout in seconds (default: {POLL_TIMEOUT})",
        )

    def handle(self, *args, **options):
        topics = options["topics"]
        poll_timeout = options["poll_timeout"]

        # Register graceful shutdown
        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)

        consumer = self._create_consumer_with_retry(topics)
        if consumer is None:
            sys.exit(1)

        self.stdout.write(f"Consumer started. Subscribed to: {', '.join(topics)}")

        consecutive_errors = 0
        max_consecutive_errors = 50

        while not _shutdown:
            try:
                msg = consumer.poll(timeout=poll_timeout)
                if msg is None:
                    consecutive_errors = 0
                    continue
                if msg.error():
                    err = msg.error()
                    logger.error("consumer.poll.error", extra={"error": str(err)})
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        logger.error(
                            "consumer.too_many_errors",
                            extra={"count": consecutive_errors},
                        )
                        break
                    time.sleep(min(consecutive_errors * 0.1, 5.0))
                    continue

                consecutive_errors = 0
                self._process_message(msg)
            except KeyboardInterrupt:
                break
            except Exception as exc:
                logger.error("consumer.loop.error", extra={"error": str(exc)})
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    logger.error(
                        "consumer.too_many_errors",
                        extra={"count": consecutive_errors},
                    )
                    break
                time.sleep(min(consecutive_errors * 0.1, 5.0))

        self._close(consumer)

    def _create_consumer_with_retry(self, topics: list[str], max_retries: int = 30):
        """Create consumer with exponential backoff retry for Kafka startup races."""
        for attempt in range(max_retries):
            consumer = self._create_consumer(topics)
            if consumer is not None:
                return consumer
            if _shutdown:
                return None
            wait = min(2 ** attempt, 15)
            self.stderr.write(
                f"Kafka not ready, retrying in {wait}s "
                f"(attempt {attempt + 1}/{max_retries})..."
            )
            time.sleep(wait)
        self.stderr.write("Failed to connect to Kafka after all retries.")
        return None

    def _create_consumer(self, topics: list[str]):
        try:
            from confluent_kafka import Consumer as KafkaConsumer
            from confluent_kafka import KafkaException

            conf = {
                "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
                "group.id": settings.KAFKA_CONSUMER_GROUP,
                "auto.offset.reset": "earliest",
                "enable.auto.commit": True,
                "auto.commit.interval.ms": 5000,
            }
            consumer = KafkaConsumer(conf)
            consumer.subscribe(topics)
            return consumer
        except ImportError:
            self.stderr.write(
                "confluent-kafka is not installed. Cannot start consumer."
            )
            return None
        except KafkaException as exc:
            logger.warning(
                "consumer.create.failed",
                extra={"error": str(exc)},
            )
            return None

    def _process_message(self, msg):
        try:
            value = msg.value()
            if value is None:
                return

            event = json.loads(value.decode("utf-8"))
            event_type = event.get("event_type")
            data = event.get("data", {})

            if not event_type:
                logger.warning("consumer.event.missing_type", extra={"event": event})
                return

            logger.info(
                "consumer.event.received",
                extra={"topic": msg.topic(), "event_type": event_type},
            )

            # Route workspace events through the email-resolution handler
            if event_type.startswith("workspace."):
                _dispatch_workspace_event(event_type, data)
            elif event_type in FANOUT_EVENT_TYPES:
                _dispatch_fanout_event(event_type, data)
            else:
                _dispatch_task(event_type, data)
        except json.JSONDecodeError as exc:
            logger.error("consumer.event.decode_failed", extra={"error": str(exc)})
        except Exception as exc:
            logger.error("consumer.event.process_failed", extra={"error": str(exc)})

    def _close(self, consumer):
        if consumer:
            consumer.close()
            self.stdout.write("Consumer stopped gracefully.")
