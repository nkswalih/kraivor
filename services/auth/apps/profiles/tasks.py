import logging

from celery import shared_task
from django.db.models import F

from profiles.models import Profile

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60, queue="identity")
def apply_reputation_event(self, user_id: str, event_type: str, delta: int):
    try:
        updated = Profile.objects.filter(user_id=user_id).update(
            reputation_score=F("reputation_score") + delta
        )
        if not updated:
            logger.warning("reputation.profile_not_found", extra={"user_id": user_id})
            return
        logger.info(
            "reputation.updated",
            extra={"user_id": user_id, "event_type": event_type, "delta": delta},
        )
    except Exception as exc:
        logger.exception("reputation.apply_failed", extra={"user_id": user_id, "event_type": event_type})
        raise self.retry(exc=exc)
