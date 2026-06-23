"""Celery application for background jobs (ingestion, retraining, maintenance)."""
from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "chatbot",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_time_limit=1800,
    task_soft_time_limit=1500,
    worker_max_tasks_per_child=50,
    task_acks_late=True,
    task_default_queue="default",
    task_routes={
        "app.workers.tasks.ingest_document": {"queue": "ingestion"},
        "app.workers.tasks.reprocess_document": {"queue": "ingestion"},
    },
)

# Ensure tasks are registered.
celery_app.autodiscover_tasks(["app.workers"])

import app.workers.tasks  # noqa: E402,F401
