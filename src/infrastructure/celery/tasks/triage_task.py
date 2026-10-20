from __future__ import annotations

"""Celery worker task for job triage and filtering."""

import asyncio
import logging

from container.container import container
from infrastructure.celery.app import celery_app

log = logging.getLogger(__name__)


@celery_app.task(name="infrastructure.celery.tasks.triage_task.run_triage", queue="triage")
def run_triage() -> dict[str, int]:
    """Execute triage workflow asynchronously in Celery."""
    log.info("Celery triage task triggered")
    result = asyncio.run(container.triage_workflow.execute(container.profile))
    log.info("Celery triage task completed: %s", result)
    return result
