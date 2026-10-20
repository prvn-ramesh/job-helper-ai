from __future__ import annotations

"""Celery application configuration."""

from celery import Celery

from core.config import settings

celery_app = Celery(
    "auto_job",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "infrastructure.celery.tasks.discover_task",
        "infrastructure.celery.tasks.triage_task",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "infrastructure.celery.tasks.discover_task.*": {"queue": "discover"},
        "infrastructure.celery.tasks.triage_task.*": {"queue": "triage"},
    },
)
