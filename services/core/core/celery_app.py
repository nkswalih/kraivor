"""
Celery app instance for the Core Service.

Usage:
    celery -A core.celery_app worker -Q notifications,default
    celery -A core.celery_app beat
"""

from celery import Celery

app = Celery("core")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
