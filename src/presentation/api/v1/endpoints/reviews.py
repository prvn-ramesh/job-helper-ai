from __future__ import annotations

"""Human Review Gate API Endpoints."""

import logging
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from container.container import container
from core.entities.job import JobStatus

log = logging.getLogger(__name__)

router = APIRouter(prefix="/reviews", tags=["reviews"])


class RejectRequest(BaseModel):
    reason: str = "Rejected by candidate in review gate"


@router.get("/pending")
async def list_pending_reviews() -> list[dict[str, Any]]:
    """Fetch all jobs awaiting human review before submission."""
    items = container.review_gate.list_pending_reviews()
    # Filter only pending items
    pending = [asdict(i) for i in items if i.status == "pending"]
    return pending


@router.post("/{job_uid}/approve")
async def approve_and_submit(job_uid: str) -> dict[str, Any]:
    """Approve a pending application and execute final submission."""
    job = await container.job_repo.get_by_uid(job_uid)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_uid} not found")

    container.review_gate.approve(job_uid)

    # Execute applier with auto-submit enabled for this action
    applier = container.apply_workflow.get_applier_for_url(job.apply_url)
    if not applier:
        raise HTTPException(status_code=400, detail="No supported ATS applier for this job URL")

    # Temporarily set auto-submit to True to perform submission
    original_mode = container.settings.application_mode
    try:
        container.settings.application_mode = "full-auto"
        result = await applier.apply(job, container.profile)
    finally:
        container.settings.application_mode = original_mode

    # Update job status
    if result.status == "applied":
        await container.job_repo.update_application_result(
            job_uid=job.job_uid,
            status=JobStatus.APPLIED,
            screenshot_path=result.screenshot_path,
            notes=result.confirmation_text or "Approved and submitted by candidate",
        )
        try:
            await container.tracker.update_status(
                job.job_uid,
                JobStatus.APPLIED,
                notes=result.confirmation_text or "Approved and submitted",
            )
        except Exception as e:
            log.warning("Could not sync approval to sheets: %s", e)

    return {
        "success": result.success,
        "status": result.status,
        "screenshot_path": result.screenshot_path,
        "confirmation": result.confirmation_text,
    }


@router.post("/{job_uid}/reject")
async def reject_application(job_uid: str, req: RejectRequest) -> dict[str, Any]:
    """Reject a pending application with feedback."""
    job = await container.job_repo.get_by_uid(job_uid)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_uid} not found")

    container.review_gate.reject(job_uid, reason=req.reason)
    await container.job_repo.update_status(
        job_uid=job.job_uid,
        status=JobStatus.REJECTED,
        filter_reason=req.reason,
    )

    try:
        await container.tracker.update_status(
            job.job_uid,
            JobStatus.REJECTED,
            notes=f"Candidate rejected: {req.reason}",
        )
    except Exception as e:
        log.warning("Could not sync rejection to sheets: %s", e)

    return {"status": "rejected", "job_uid": job_uid, "reason": req.reason}
