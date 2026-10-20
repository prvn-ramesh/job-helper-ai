from __future__ import annotations

from abc import ABC, abstractmethod

from core.entities.job import JobRecord, JobStatus


class IJobRepository(ABC):
    @abstractmethod
    async def upsert(self, job: JobRecord) -> bool:
        """Insert or update a job. Returns True if it was new."""

    @abstractmethod
    async def exists(self, job_uid: str) -> bool:
        """Check if a job already exists."""

    @abstractmethod
    async def get_by_status(self, status: JobStatus) -> list[JobRecord]:
        """Get all jobs with a given status."""

    @abstractmethod
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
        """Update job status and optional metadata."""

    @abstractmethod
    async def count_applied_today(self) -> int:
        """Count applications submitted today (UTC)."""

    @abstractmethod
    async def get_by_uid(self, job_uid: str) -> JobRecord | None:
        """Fetch single job by uid."""

    @abstractmethod
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
        """Update job with application result details."""
