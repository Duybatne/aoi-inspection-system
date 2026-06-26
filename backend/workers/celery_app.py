import os
from celery import Celery
from backend.config import settings

# Initialize Celery app
celery_app = Celery(
    "aoi_workers",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.REDIS_URL,
    include=["backend.workers.tasks"]
)

# Optional configuration updates
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    # Make sure we don't have task timeout issues for large images
    task_time_limit=300, 
    task_soft_time_limit=240,
)

if __name__ == "__main__":
    celery_app.start()
