from __future__ import annotations

"""Celery worker task for job discovery."""

import asyncio
import logging

from container.container import container
from infrastructure.celery.app import celery_app

log = logging.getLogger(__name__)


@celery_app.task(name="infrastructure.celery.tasks.discover_task.run_discovery", queue="discover")
def run_discovery() -> dict[str, int]:
    """Execute the discovery workflow asynchronously in Celery."""
    log.info("Celery discover task triggered")
    result = asyncio.run(container.discover_workflow.execute(container.profile))
    log.info("Celery discover task completed: %s", result)
    return result
