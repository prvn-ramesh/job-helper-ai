from __future__ import annotations

"""Celery worker task for automated job applications."""

import asyncio
import logging

from container.container import container
from infrastructure.celery.app import celery_app

log = logging.getLogger(__name__)


@celery_app.task(name="infrastructure.celery.tasks.apply_task.run_apply_batch", queue="apply")
def run_apply_batch(limit: int = 5) -> dict[str, int]:
    """Execute application batch workflow asynchronously in Celery."""
    log.info("Celery apply batch task triggered (limit: %d)", limit)
    results = asyncio.run(container.apply_workflow.apply_approved_batch(limit=limit))
    applied_count = sum(1 for r in results if r.status == "applied")
    pending_count = sum(1 for r in results if r.status == "pending_review")
    failed_count = sum(1 for r in results if r.status == "failed")

    summary = {
        "processed": len(results),
        "applied": applied_count,
        "pending_review": pending_count,
        "failed": failed_count,
    }
    log.info("Celery apply batch task completed: %s", summary)
    return summary
