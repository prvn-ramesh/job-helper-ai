from __future__ import annotations

"""Jobs Query and Management Endpoints."""

import contextlib
import json
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from container.container import container
from infrastructure.database.sqlite import get_db

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("")
async def list_jobs(
    status: str | None = Query(None, description="Job status to filter by (or 'all')"),
    platform: str | None = Query(None, description="Platform filter"),
    work_mode: str | None = Query(None, description="remote, onsite, hybrid"),
    search: str | None = Query(None, description="Keyword search in title or company"),
    min_score: float | None = Query(None, description="Minimum fit score"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """List jobs with rich filtering, search, and pagination."""
    query = "SELECT * FROM jobs WHERE 1=1"
    count_query = "SELECT COUNT(*) FROM jobs WHERE 1=1"
    params: list[Any] = []

    if status and status.lower() != "all":
        query += " AND status = ?"
        count_query += " AND status = ?"
        params.append(status.lower())

    if platform:
        query += " AND platform = ?"
        count_query += " AND platform = ?"
        params.append(platform.lower())

    if work_mode:
        query += " AND work_mode = ?"
        count_query += " AND work_mode = ?"
        params.append(work_mode.lower())

    if min_score is not None:
        query += " AND score >= ?"
        count_query += " AND score >= ?"
        params.append(min_score)

    if search:
        search_pattern = f"%{search.strip()}%"
        query += " AND (title LIKE ? OR company LIKE ?)"
        count_query += " AND (title LIKE ? OR company LIKE ?)"
        params.extend([search_pattern, search_pattern])

    with get_db() as conn:
        total_matching = conn.execute(count_query, params).fetchone()[0]

        query += " ORDER BY score DESC, discovered_at DESC LIMIT ? OFFSET ?"
        rows = conn.execute(query, params + [limit, offset]).fetchall()

        jobs_list = []
        for r in rows:
            d = dict(r)
            # Parse filled fields if JSON
            if d.get("filled_fields"):
                with contextlib.suppress(Exception):
                    d["filled_fields"] = json.loads(d["filled_fields"])
            jobs_list.append(d)

    return {
        "total": total_matching,
        "limit": limit,
        "offset": offset,
        "jobs": jobs_list,
    }


@router.get("/{job_uid}")
async def get_job_detail(job_uid: str) -> dict[str, Any]:
    """Retrieve full details of a specific job."""
    job = await container.job_repo.get_by_uid(job_uid)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_uid} not found")

    res = dict(job.__dict__)
    # Convert enums to string values
    res["status"] = res["status"].value
    res["work_mode"] = res["work_mode"].value
    res["eligibility"] = res["eligibility"].value
    res["discovered_at"] = res["discovered_at"].isoformat()
    if res.get("applied_at"):
        res["applied_at"] = res["applied_at"].isoformat()

    return res
