from __future__ import annotations

"""Stats and KPI Metrics Endpoint."""

from fastapi import APIRouter

from container.container import container
from core.config import settings
from infrastructure.database.sqlite import get_db

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("")
async def get_stats() -> dict:
    """Retrieve system KPIs, application numbers, and configuration state."""
    counts = {}
    with get_db() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) FROM jobs GROUP BY status"
        ).fetchall()
        counts = {r[0]: r[1] for r in rows}

        total_jobs = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]

    applied_today = await container.job_repo.count_applied_today()
    pending_reviews = len(container.review_gate.list_pending_reviews())

    sheet_url = (
        f"https://docs.google.com/spreadsheets/d/{settings.google_sheets_id}/edit"
        if settings.google_sheets_id
        else "https://docs.google.com/spreadsheets/d/16N4kXGHWP9KhyKyRoqvjNJTMX20W5LaM5gfs3AiQOzg/edit"
    )

    return {
        "total_jobs": total_jobs,
        "discovered": counts.get("discovered", 0),
        "triaged": counts.get("triaged", 0),
        "approved": counts.get("approved", 0),
        "filtered_out": counts.get("filtered_out", 0),
        "applied": counts.get("applied", 0),
        "pending_reviews": pending_reviews,
        "applied_today": applied_today,
        "daily_limit": settings.daily_apply_limit,
        "application_mode": settings.application_mode,
        "google_sheets_url": sheet_url,
    }
