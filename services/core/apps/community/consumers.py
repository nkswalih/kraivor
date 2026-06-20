import logging

from .tasks import update_author_denormalization

logger = logging.getLogger(__name__)


def handle_profile_updated(event: dict):
    data = event.get("data", {})
    user_id = data.get("user_id")
    username = data.get("username")
    display_name = data.get("display_name")
    avatar_url = data.get("avatar_url", "")
    if not all([user_id, username, display_name]):
        logger.warning("consumer.profile_updated.incomplete", extra={"data": data})
        return
    update_author_denormalization.delay(user_id, username, display_name, avatar_url)


EVENT_HANDLERS = {
    "profile.updated": handle_profile_updated,
}


def dispatch_event(event_type: str, event: dict):
    handler = EVENT_HANDLERS.get(event_type)
    if handler:
        handler(event)
    else:
        logger.debug("consumer.no_handler", extra={"event_type": event_type})
