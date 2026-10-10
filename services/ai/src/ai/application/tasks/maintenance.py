from app.core.celery_app import celery_app


@celery_app.task(bind=True, queue="ai.maintenance")
def health_check_worker(self):
    return {"status": "ok", "worker": self.request.hostname}


@celery_app.task(bind=True, queue="ai.maintenance")
def clean_expired_cache(self):
    return {"status": "ok", "cleaned": 0}
