from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "ai",
    broker=settings.celery__broker__url,
    backend=settings.celery__result__backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,
    task_soft_time_limit=540,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_queue="ai.default",
    task_queues={
        "ai.inference": {"exchange": "ai", "routing_key": "ai.inference"},
        "ai.indexing": {"exchange": "ai", "routing_key": "ai.indexing"},
        "ai.maintenance": {"exchange": "ai", "routing_key": "ai.maintenance"},
    },
    beat_schedule={
        "health-check-every-5m": {
            "task": "app.application.tasks.maintenance.health_check_worker",
            "schedule": 300.0,
        },
        "clean-expired-cache-daily": {
            "task": "app.application.tasks.maintenance.clean_expired_cache",
            "schedule": 86400.0,
        },
    },
)

celery_app.autodiscover_tasks(["app.application.tasks"])
