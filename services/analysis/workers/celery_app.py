from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "analysis",
    broker=str(settings.celery.broker_url),
    backend=str(settings.celery.result_backend),
)

celery_app.conf.update(
    task_acks_late=settings.celery.task_acks_late,
    worker_prefetch_multiplier=settings.celery.worker_prefetch_multiplier,
    worker_concurrency=settings.celery.worker_concurrency,
    task_soft_time_limit=settings.celery.task_soft_time_limit,
    task_time_limit=settings.celery.task_time_limit,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_send_sent_event=True,
    worker_send_task_events=True,
    result_expires=86400,
)

celery_app.autodiscover_tasks(["app.application.tasks"])
