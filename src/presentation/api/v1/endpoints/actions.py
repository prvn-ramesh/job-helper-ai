from __future__ import annotations

"""Worker Control and Trigger Endpoints."""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from container.container import container

router = APIRouter(prefix="/actions", tags=["actions"])


class ApplyRequest(BaseModel):
    limit: int = 5


@router.post("/discover")
async def trigger_discovery() -> dict[str, Any]:
    """Trigger Worker 1: ATS and job board scraping on-demand."""
    new_jobs_count = await container.discover_workflow.execute()
    return {
        "status": "completed",
        "worker": "discover",
        "new_jobs_discovered": new_jobs_count,
    }


@router.post("/triage")
async def trigger_triage() -> dict[str, Any]:
    """Trigger Worker 2: Scoring, Visa, Location, and Experience filtering on-demand."""
    result = await container.triage_workflow.execute(container.profile)
    return {
        "status": "completed",
        "worker": "triage",
        "results": result,
    }


@router.post("/apply")
async def trigger_apply_batch(req: ApplyRequest) -> dict[str, Any]:
    """Trigger Worker 3: Form filling, screenshot capture, and review gate."""
    results = await container.apply_workflow.apply_approved_batch(limit=req.limit)
    applied_count = sum(1 for r in results if r.status == "applied")
    pending_count = sum(1 for r in results if r.status == "pending_review")
    failed_count = sum(1 for r in results if r.status == "failed")

    return {
        "status": "completed",
        "worker": "apply",
        "processed": len(results),
        "applied": applied_count,
        "pending_review": pending_count,
        "failed": failed_count,
    }
