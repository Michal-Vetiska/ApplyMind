"""Celery application and beat schedule."""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "applymind",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "discover-jobs-every-3h": {
            "task": "app.workers.tasks.discover_jobs",
            "schedule": 3 * 60 * 60,
        },
        "sync-inbox-every-10m": {
            "task": "app.workers.tasks.sync_inbox",
            "schedule": 10 * 60,
        },
        "suggest-followups-daily": {
            "task": "app.workers.tasks.suggest_followups",
            "schedule": crontab(hour=8, minute=0),
        },
        "refresh-source-health-hourly": {
            "task": "app.workers.tasks.refresh_source_health",
            "schedule": 60 * 60,
        },
        "update-analytics-hourly": {
            "task": "app.workers.tasks.update_analytics",
            "schedule": 60 * 60,
        },
    },
)
