"""Celery application — three queues: video, genai, reports."""
from celery import Celery
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "surveillance",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.video_tasks", "app.tasks.genai_tasks", "app.tasks.report_tasks"],
)

celery_app.conf.update(
    task_routes={
        "app.tasks.video_tasks.*": {"queue": "video"},
        "app.tasks.genai_tasks.*": {"queue": "genai"},
        "app.tasks.report_tasks.*": {"queue": "reports"},
    },
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)
