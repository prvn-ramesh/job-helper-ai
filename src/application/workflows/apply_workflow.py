from __future__ import annotations

"""Application Workflow (Worker 3).

Coordinates the execution of automated job applications across Tier 1 ATS platforms,
handling human review gates, daily application pacing, and syncing status to
SQLite and Google Sheets.
"""

import asyncio
import json
import logging
import random
from datetime import UTC, datetime

from core.config import settings
from core.entities.job import JobStatus
from core.entities.profile import CandidateProfile
from core.interfaces.repositories.i_job_repository import IJobRepository
from core.interfaces.trackers.i_tracker import ITracker
from domain.appliers.base_applier import ApplyResult, BaseApplier
from domain.appliers.review_gate import ReviewGate

log = logging.getLogger(__name__)


class ApplyWorkflow:
    def __init__(
        self,
        job_repo: IJobRepository,
        tracker: ITracker,
        appliers: list[BaseApplier],
        profile: CandidateProfile,
        review_gate: ReviewGate,
    ) -> None:
        self.job_repo = job_repo
        self.tracker = tracker
        self.appliers = appliers
        self.profile = profile
        self.review_gate = review_gate

    def get_applier_for_url(self, url: str) -> BaseApplier | None:
        """Find the matching ATS applier for the target URL."""
        for applier in self.appliers:
            if applier.can_handle(url):
                return applier
        return None

    async def apply_to_job(
        self,
        job_uid: str,
        resume_path: str | None = None,
    ) -> ApplyResult:
        """Apply to a single job by uid."""
        job = await self.job_repo.get_by_uid(job_uid)
        if not job:
            log.error("Job %s not found in repository", job_uid)
            return ApplyResult(
                success=False,
                status="failed",
                screenshot_path="",
                error_message=f"Job {job_uid} not found",
            )

        applier = self.get_applier_for_url(job.apply_url)
        if not applier:
            log.warning("No supported ATS applier found for URL: %s", job.apply_url)
            return ApplyResult(
                success=False,
                status="failed",
                screenshot_path="",
                error_message=f"Unsupported ATS platform for {job.apply_url}",
            )

        log.info(
            "Executing %s applier for '%s' at %s (Mode: %s)",
            applier.platform_name,
            job.title,
            job.company,
            settings.application_mode,
        )

        result = await applier.apply(job, self.profile, resume_path)

        # Update SQLite and Google Sheets according to result
        if result.status == "applied":
            now = datetime.now(UTC)
            await self.job_repo.update_application_result(
                job_uid=job.job_uid,
                status=JobStatus.APPLIED,
                screenshot_path=result.screenshot_path,
                filled_fields=json.dumps(result.filled_fields),
                notes=result.confirmation_text or "Applied successfully",
                applied_at=now,
            )
            try:
                await self.tracker.update_status(
                    job.job_uid,
                    JobStatus.APPLIED,
                    applied_at=now,
                    notes=result.confirmation_text or "Applied",
                )
            except Exception as e:
                log.warning("Failed to sync status to Google Sheets: %s", e)

        elif result.status == "pending_review":
            await self.job_repo.update_application_result(
                job_uid=job.job_uid,
                status=JobStatus.TRIAGED,
                screenshot_path=result.screenshot_path,
                filled_fields=json.dumps(result.filled_fields),
                notes="Pending human review in semi-auto mode",
            )
            try:
                await self.tracker.update_status(
                    job.job_uid,
                    JobStatus.TRIAGED,
                    notes=f"Pending Review ({result.screenshot_path})",
                )
            except Exception as e:
                log.warning("Failed to sync review status to Google Sheets: %s", e)

        elif result.status == "failed":
            await self.job_repo.update_application_result(
                job_uid=job.job_uid,
                status=JobStatus.FAILED,
                screenshot_path=result.screenshot_path,
                notes=result.error_message,
            )

        return result

    async def apply_approved_batch(self, limit: int = 5) -> list[ApplyResult]:
        """Apply to a batch of approved jobs respecting the daily application limit."""
        applied_today = await self.job_repo.count_applied_today()
        remaining_quota = max(0, settings.daily_apply_limit - applied_today)

        if remaining_quota <= 0:
            log.info("Daily application limit reached (%d/%d)", applied_today, settings.daily_apply_limit)
            return []

        batch_size = min(limit, remaining_quota)
        approved_jobs = await self.job_repo.get_by_status(JobStatus.APPROVED)
        to_process = approved_jobs[:batch_size]

        log.info("Processing apply batch: %d jobs (Remaining quota: %d)", len(to_process), remaining_quota)
        results = []

        for idx, job in enumerate(to_process):
            res = await self.apply_to_job(job.job_uid)
            results.append(res)

            # Polite randomized delay between applications
            if idx < len(to_process) - 1:
                delay = random.uniform(3.0, 7.0)
                await asyncio.sleep(delay)

        return results
