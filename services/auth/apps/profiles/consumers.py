import logging

from profiles.constants import REPUTATION_EVENTS
from profiles.tasks import apply_reputation_event

logger = logging.getLogger(__name__)


def handle_community_event(event: dict):
    event_type = event.get("event_type")
    data = event.get("data", {})
    delta = REPUTATION_EVENTS.get(event_type)
    if delta is None:
        logger.debug("consumer.reputation.no_delta", extra={"event_type": event_type})
        return
    author_id = data.get("author_id")
    if not author_id:
        logger.warning("consumer.reputation.missing_author", extra={"event_type": event_type})
        return
    apply_reputation_event.delay(author_id, event_type, delta)


EVENT_HANDLERS = {
    "discussion.created": handle_community_event,
    "discussion.deleted": handle_community_event,
    "discussion.upvoted": handle_community_event,
    "discussion.downvoted": handle_community_event,
    "comment.created": handle_community_event,
    "comment.deleted": handle_community_event,
    "comment.upvoted": handle_community_event,
    "comment.downvoted": handle_community_event,
}


def dispatch_event(event_type: str, event: dict):
    handler = EVENT_HANDLERS.get(event_type)
    if handler:
        handler(event)
    else:
        logger.debug("consumer.reputation.no_handler", extra={"event_type": event_type})
