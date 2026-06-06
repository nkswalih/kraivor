"""
Kafka consumer management command.

Listens to external service events (analysis, ai) and dispatches
Celery tasks for notification delivery.

Usage:
    python manage.py consume_events

Subscribes to topics:
    - analysis.events  (analysis.completed, analysis.failed)
    - ai.events        (ai.index.completed, ai.analysis.completed)

Events that Core publishes internally are NOT consumed here — they
are dispatched directly via transaction.on_commit() in service code.
"""

import json
import logging
import signal
import sys

from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

# ── Event type → Celery task dispatch map ──────────────────────────────────────

DISPATCH_TABLE: dict[str, str] = {
    # Analysis events
    "analysis.completed": "notifications.tasks.dispatch_notification",
    "analysis.failed": "notifications.tasks.dispatch_notification",
    # AI events
    "ai.index.completed": "notifications.tasks.dispatch_notification",
    "ai.analysis.completed": "notifications.tasks.dispatch_notification",
}

TOPICS = ["analysis.events", "ai.events"]
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

    task.delay(
        user_id=str(user_id),
        notification_type=event_type,
        title=title,
        body=body,
        link=data.get("link", ""),
        workspace_id=data.get("workspace_id"),
        actor_id=data.get("actor_id"),
    )
    logger.info("consumer.event.dispatched", extra={"event_type": event_type, "user_id": str(user_id)})


def _build_title(event_type: str, data: dict) -> str:
    titles = {
        "analysis.completed": "Analysis Complete",
        "analysis.failed": "Analysis Failed",
        "ai.index.completed": "Indexing Complete",
        "ai.analysis.completed": "AI Analysis Complete",
    }
    return titles.get(event_type, f"Event: {event_type}")


def _build_body(event_type: str, data: dict) -> str:
    bodies = {
        "analysis.completed": f"Repository {data.get('github_repo', '')} analysis is complete.",
        "analysis.failed": f"Repository analysis failed: {data.get('error', 'Unknown error')}",
        "ai.index.completed": f"Repository {data.get('github_repo', '')} has been indexed.",
        "ai.analysis.completed": f"AI analysis report is ready for {data.get('github_repo', '')}.",
    }
    return bodies.get(event_type, json.dumps(data))


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

        consumer = self._create_consumer(topics)
        if consumer is None:
            sys.exit(1)

        self.stdout.write(f"Consumer started. Subscribed to: {', '.join(topics)}")

        while not _shutdown:
            try:
                msg = consumer.poll(timeout=poll_timeout)
                if msg is None:
                    continue
                if msg.error():
                    logger.error("consumer.poll.error", extra={"error": msg.error()})
                    continue

                self._process_message(msg)
            except KeyboardInterrupt:
                break
            except Exception as exc:
                logger.error("consumer.loop.error", extra={"error": str(exc)})

        self._close(consumer)

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
            self.stderr.write("confluent-kafka is not installed. Cannot start consumer.")
            return None
        except KafkaException as exc:
            self.stderr.write(f"Failed to create Kafka consumer: {exc}")
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
            _dispatch_task(event_type, data)
        except json.JSONDecodeError as exc:
            logger.error("consumer.event.decode_failed", extra={"error": str(exc)})
        except Exception as exc:
            logger.error("consumer.event.process_failed", extra={"error": str(exc)})

    def _close(self, consumer):
        if consumer:
            consumer.close()
            self.stdout.write("Consumer stopped gracefully.")
