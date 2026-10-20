from __future__ import annotations

"""Workflow 2: Triage Worker.

Scores jobs, evaluates visa/location/experience eligibility,
and routes jobs to either approved or filtered_out.
"""

import logging
from typing import Any

from core.entities.job import EligibilityVerdict, JobRecord, JobStatus
from core.entities.profile import CandidateProfile
from core.interfaces.repositories.i_job_repository import IJobRepository
from core.interfaces.trackers.i_tracker import ITracker
from domain.triage.eligibility import check_eligibility
from domain.triage.scorer import score_job

log = logging.getLogger(__name__)


class TriageWorkflow:
    def __init__(
        self,
        job_repo: IJobRepository,
        tracker: ITracker,
        filter_rules: dict[str, Any] | None = None,
        min_score_threshold: float = 6.0,
    ) -> None:
        self.job_repo = job_repo
        self.tracker = tracker
        self.filter_rules = filter_rules or {}
        self.min_score_threshold = min_score_threshold

    async def execute(self, profile: CandidateProfile | None = None) -> dict[str, int]:
        if profile is None:
            from container.container import container
            profile = container.profile
        log.info("Starting Triage Workflow...")
        pending_jobs = await self.job_repo.get_by_status(JobStatus.DISCOVERED)
        log.info("Found %d discovered jobs to triage", len(pending_jobs))

        approved_jobs: list[JobRecord] = []
        filtered_jobs: list[JobRecord] = []

        for job in pending_jobs:
            score = score_job(job, profile)
            verdict, reason = check_eligibility(job, profile, self.filter_rules)

            # Check score threshold if eligibility passed
            if verdict == EligibilityVerdict.ELIGIBLE and score < self.min_score_threshold:
                verdict = EligibilityVerdict.SKIP
                reason = f"Relevance score {score} < {self.min_score_threshold}"

            if verdict == EligibilityVerdict.SKIP:
                job.status = JobStatus.FILTERED_OUT
                job.score = score
                job.filter_reason = reason
                job.eligibility = verdict
                filtered_jobs.append(job)
                await self.job_repo.update_status(
                    job.job_uid,
                    JobStatus.FILTERED_OUT,
                    score=score,
                    filter_reason=reason,
                )
            else:
                job.status = JobStatus.APPROVED
                job.score = score
                job.filter_reason = None
                job.eligibility = verdict
                approved_jobs.append(job)
                await self.job_repo.update_status(
                    job.job_uid,
                    JobStatus.APPROVED,
                    score=score,
                )

        # Batch sync to Google Sheets (fast, minimal API calls)
        if approved_jobs or filtered_jobs:
            try:
                await self.tracker.batch_sync_triage(approved_jobs, filtered_jobs)
            except Exception as sheet_err:
                log.warning("Sheet batch sync error: %s", sheet_err)

        approved_count = len(approved_jobs)
        filtered_count = len(filtered_jobs)

        log.info(
            "Triage complete: triaged=%d, approved=%d, filtered_out=%d",
            len(pending_jobs),
            approved_count,
            filtered_count,
        )
        return {
            "total_triaged": len(pending_jobs),
            "approved": approved_count,
            "filtered_out": filtered_count,
        }
