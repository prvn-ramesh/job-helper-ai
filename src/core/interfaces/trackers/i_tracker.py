from __future__ import annotations

from abc import ABC, abstractmethod

from core.entities.job import JobRecord, JobStatus


class ITracker(ABC):
    """Port for external tracking (Google Sheets, Telegram, etc.)."""

    @abstractmethod
    async def upsert_job(self, job: JobRecord) -> None:
        """Sync job row to the external tracker."""

    @abstractmethod
    async def update_status(self, job_uid: str, status: JobStatus, **extra) -> None:
        """Update only the status (and any extra fields) of an existing row."""

    async def batch_upsert_jobs(self, jobs: list[JobRecord]) -> None:
        """Batch sync multiple job rows (default fallback loops upsert_job)."""
        for job in jobs:
            await self.upsert_job(job)
