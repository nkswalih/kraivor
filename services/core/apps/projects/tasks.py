import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    name="projects.check_overdue_tasks",
    queue="default",
    max_retries=3,
    default_retry_delay=60,
    bind=True,
)
def check_overdue_tasks(self) -> dict:
    from .constants import TERMINAL_TASK_STATUSES
    from .events import TaskEventPublisher
    from .models import Task

    try:
        today = timezone.now().date()

        overdue_tasks = Task.objects.filter(
            due_date__lt=today,
            deleted_at__isnull=True,
        ).exclude(
            status__in=list(TERMINAL_TASK_STATUSES)
        ).select_related("project")

        count = 0
        for task in overdue_tasks.iterator(chunk_size=100):
            TaskEventPublisher.publish_task_overdue(task)
            count += 1

        logger.info("check_overdue_tasks: published %d overdue events", count)
        return {"overdue_count": count, "checked_at": timezone.now().isoformat()}

    except Exception as exc:
        logger.exception("check_overdue_tasks failed: %s", exc)
        raise self.retry(exc=exc)
