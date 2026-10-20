from __future__ import annotations

"""Celery beat schedule for automated periodic execution."""

from celery.schedules import crontab

from infrastructure.celery.app import celery_app

celery_app.conf.beat_schedule = {
    "run-discovery-every-6-hours": {
        "task": "infrastructure.celery.tasks.discover_task.run_discovery",
        "schedule": crontab(minute="0", hour="*/6"),
        "options": {"queue": "discover"},
    },
    "run-triage-every-hour": {
        "task": "infrastructure.celery.tasks.triage_task.run_triage",
        "schedule": crontab(minute="30", hour="*"),
        "options": {"queue": "triage"},
    },
}
