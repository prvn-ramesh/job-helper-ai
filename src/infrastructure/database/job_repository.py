from __future__ import annotations

from datetime import UTC, datetime

from core.entities.job import EligibilityVerdict, JobRecord, JobStatus, WorkMode
from core.interfaces.repositories.i_job_repository import IJobRepository
from infrastructure.database.sqlite import get_db


def _row_to_job(row) -> JobRecord:
    d = dict(row)
    return JobRecord(
        job_uid=d["job_uid"],
        title=d["title"],
        company=d["company"],
        location=d["location"],
        platform=d["platform"],
        apply_url=d["apply_url"],
        job_id_external=d.get("job_id_external", ""),
        description=d.get("description", ""),
        content_hash=d.get("content_hash", ""),
        work_mode=WorkMode(d.get("work_mode", "unknown")),
        city=d.get("city", ""),
        country=d.get("country", ""),
        min_experience_years=d.get("min_experience_years"),
        max_experience_years=d.get("max_experience_years"),
        salary_min=d.get("salary_min"),
        salary_max=d.get("salary_max"),
        salary_currency=d.get("salary_currency", "INR"),
        status=JobStatus(d["status"]),
        score=d.get("score"),
        filter_reason=d.get("filter_reason"),
        eligibility=EligibilityVerdict(d.get("eligibility", "unknown")),
        discovered_at=datetime.fromisoformat(d["discovered_at"]),
        applied_at=datetime.fromisoformat(d["applied_at"]) if d.get("applied_at") else None,
        resume_used=d.get("resume_used"),
        cover_note=d.get("cover_note"),
        notes=d.get("notes", ""),
        screenshot_path=d.get("screenshot_path"),
        filled_fields=d.get("filled_fields"),
    )


class SQLiteJobRepository(IJobRepository):
    """Sync SQLite implementation of IJobRepository."""

    async def upsert(self, job: JobRecord) -> bool:
        with get_db() as conn:
            existing = conn.execute(
                "SELECT job_uid FROM jobs WHERE job_uid = ?", (job.job_uid,)
            ).fetchone()

            if existing:
                # Update only content_hash + description if changed
                conn.execute(
                    """
                    UPDATE jobs SET
                        description   = COALESCE(NULLIF(?, ''), description),
                        content_hash  = COALESCE(NULLIF(?, ''), content_hash),
                        apply_url     = ?
                    WHERE job_uid = ?
                    """,
                    (job.description, job.content_hash, job.apply_url, job.job_uid),
                )
                return False

            conn.execute(
                """
                INSERT INTO jobs (
                    job_uid, title, company, location, city, country, platform, apply_url,
                    job_id_external, description, content_hash,
                    work_mode, min_experience_years, max_experience_years,
                    salary_min, salary_max, salary_currency,
                    status, score, filter_reason, eligibility,
                    discovered_at, applied_at, resume_used, cover_note, notes
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?, ?
                )
                """,
                (
                    job.job_uid,
                    job.title,
                    job.company,
                    job.location,
                    job.city,
                    job.country,
                    job.platform,
                    job.apply_url,
                    job.job_id_external,
                    job.description,
                    job.content_hash,
                    job.work_mode.value,
                    job.min_experience_years,
                    job.max_experience_years,
                    job.salary_min,
                    job.salary_max,
                    job.salary_currency,
                    job.status.value,
                    job.score,
                    job.filter_reason,
                    job.eligibility.value,
                    job.discovered_at.isoformat(),
                    job.applied_at.isoformat() if job.applied_at else None,
                    job.resume_used,
                    job.cover_note,
                    job.notes,
                ),
            )
            return True

    async def exists(self, job_uid: str) -> bool:
        with get_db() as conn:
            row = conn.execute("SELECT 1 FROM jobs WHERE job_uid = ?", (job_uid,)).fetchone()
            return row is not None

    async def get_by_status(self, status: JobStatus) -> list[JobRecord]:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE status = ? ORDER BY discovered_at DESC",
                (status.value,),
            ).fetchall()
            return [_row_to_job(r) for r in rows]

    async def update_status(
        self,
        job_uid: str,
        status: JobStatus,
        *,
        score: float | None = None,
        filter_reason: str | None = None,
        applied_at=None,
        resume_used: str | None = None,
    ) -> None:
        with get_db() as conn:
            conn.execute(
                """
                UPDATE jobs SET
                    status        = ?,
                    score         = COALESCE(?, score),
                    filter_reason = COALESCE(?, filter_reason),
                    applied_at    = COALESCE(?, applied_at),
                    resume_used   = COALESCE(?, resume_used)
                WHERE job_uid = ?
                """,
                (
                    status.value,
                    score,
                    filter_reason,
                    applied_at.isoformat() if applied_at else None,
                    resume_used,
                    job_uid,
                ),
            )

    async def count_applied_today(self) -> int:
        today = datetime.now(UTC).date().isoformat()
        with get_db() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM jobs WHERE status = 'applied' AND applied_at LIKE ?",
                (f"{today}%",),
            ).fetchone()
            return row[0] if row else 0

    async def get_by_uid(self, job_uid: str) -> JobRecord | None:
        with get_db() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE job_uid = ?", (job_uid,)).fetchone()
            return _row_to_job(row) if row else None

    async def update_application_result(
        self,
        job_uid: str,
        status: JobStatus,
        *,
        screenshot_path: str | None = None,
        filled_fields: str | None = None,
        notes: str | None = None,
        applied_at=None,
    ) -> None:
        with get_db() as conn:
            conn.execute(
                """
                UPDATE jobs SET
                    status          = ?,
                    screenshot_path = COALESCE(?, screenshot_path),
                    filled_fields   = COALESCE(?, filled_fields),
                    notes           = COALESCE(?, notes),
                    applied_at      = COALESCE(?, applied_at)
                WHERE job_uid = ?
                """,
                (
                    status.value,
                    screenshot_path,
                    filled_fields,
                    notes,
                    applied_at.isoformat() if applied_at else None,
                    job_uid,
                ),
            )
