import json
import logging
import uuid

from django.db import transaction

logger = logging.getLogger(__name__)


def _build_envelope(event_type, data, user_id=None, workspace_id=None):
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "source_service": "identity",
        "workspace_id": workspace_id,
        "user_id": user_id,
        "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "version": 1,
        "data": data,
    }


def _get_producer():
    try:
        from auth.infrastructure.kafka import get_producer

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


def publish_profile_updated(profile, old_values=None):
    envelope = _build_envelope(
        event_type="profile.updated",
        data={
            "user_id": str(profile.user_id),
            "username": profile.username,
            "display_name": profile.display_name,
            "avatar_url": profile.avatar_url,
            "bio": profile.bio,
            "old_values": old_values or {},
        },
        user_id=str(profile.user_id),
    )
    transaction.on_commit(
        lambda: _publish("profiles", envelope, user_id=profile.user_id)
    )


def publish_follow_new(follower_id: str, target_user_id: str, follower_username: str):
    envelope = _build_envelope(
        event_type="profile.follow.new",
        data={
            "follower_id": follower_id,
            "follower_username": follower_username,
            "target_user_id": target_user_id,
        },
        user_id=target_user_id,
    )
    transaction.on_commit(
        lambda: _publish("profiles", envelope, user_id=target_user_id)
    )
