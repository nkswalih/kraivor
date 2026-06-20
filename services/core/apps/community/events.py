import json
import logging
import uuid

from django.db import transaction

logger = logging.getLogger(__name__)


def _build_envelope(event_type, data, user_id=None, workspace_id=None):
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "source_service": "core",
        "workspace_id": workspace_id,
        "user_id": user_id,
        "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "version": 1,
        "data": data,
    }


def _get_producer():
    try:
        from core.infrastructure.kafka import get_producer

        return get_producer()
    except ImportError:
        return None


def _publish(topic, event, user_id=None):
    producer = _get_producer()
    if producer is None:
        logger.info(
            "kafka.event.skipped",
            extra={
                "topic": topic,
                "event_type": event.get("event_type"),
                "reason": "no_producer",
            },
        )
        return
    try:
        key = str(user_id).encode() if user_id else event["event_id"].encode()
        producer.produce(
            topic=topic,
            key=key,
            value=json.dumps(event).encode(),
            callback=_delivery_report,
        )
        producer.flush(timeout=2.0)
    except Exception as exc:
        logger.error(
            "kafka.publish.failed",
            extra={"topic": topic, "event_type": event.get("event_type"), "error": str(exc)},
        )


def _delivery_report(err, msg):
    if err is not None:
        logger.error("kafka.delivery.failed", extra={"error": str(err), "topic": msg.topic()})


def publish_discussion_created(discussion, user_id):
    envelope = _build_envelope(
        event_type="discussion.created",
        data={
            "discussion_id": str(discussion.id),
            "author_id": str(discussion.author_id),
            "title": discussion.title,
        },
        user_id=user_id,
    )
    transaction.on_commit(lambda: _publish("community", envelope, user_id=user_id))


def publish_discussion_deleted(discussion_id, author_id):
    envelope = _build_envelope(
        event_type="discussion.deleted",
        data={
            "discussion_id": discussion_id,
            "author_id": author_id,
        },
        user_id=author_id,
    )
    transaction.on_commit(lambda: _publish("community", envelope, user_id=author_id))


def publish_discussion_upvoted(discussion, user_id):
    envelope = _build_envelope(
        event_type="discussion.upvoted",
        data={
            "discussion_id": str(discussion.id),
            "author_id": str(discussion.author_id),
            "voter_id": user_id,
        },
        user_id=user_id,
    )
    transaction.on_commit(lambda: _publish("community", envelope, user_id=user_id))


def publish_comment_created(comment, user_id):
    envelope = _build_envelope(
        event_type="comment.created",
        data={
            "comment_id": str(comment.id),
            "discussion_id": str(comment.discussion_id),
            "author_id": str(comment.author_id),
        },
        user_id=user_id,
    )
    transaction.on_commit(lambda: _publish("community", envelope, user_id=user_id))
