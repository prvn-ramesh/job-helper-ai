from __future__ import annotations

"""Workflow 1: Discover and sync new job postings.

Coordinates scrapers, deduplicates jobs, persists them to SQLite,
and mirrors newly discovered jobs to Google Sheets.
"""

import asyncio
import logging
from collections.abc import Sequence

from core.entities.job import JobRecord
from core.entities.profile import CandidateProfile
from core.interfaces.repositories.i_job_repository import IJobRepository
from core.interfaces.scrapers.i_scraper import IScraper
from core.interfaces.trackers.i_tracker import ITracker

log = logging.getLogger(__name__)


class DiscoverWorkflow:
    def __init__(
        self,
        scrapers: Sequence[IScraper],
        job_repo: IJobRepository,
        tracker: ITracker,
    ) -> None:
        self.scrapers = scrapers
        self.job_repo = job_repo
        self.tracker = tracker

    async def execute(self, profile: CandidateProfile | None = None) -> dict[str, int]:
        if profile is None:
            from container.container import container
            profile = container.profile

        log.info("Starting discovery workflow with %d scrapers", len(self.scrapers))
        tasks = [scraper.scrape(profile) for scraper in self.scrapers]
        scraped_lists = await asyncio.gather(*tasks, return_exceptions=True)

        all_jobs: list[JobRecord] = []
        for res in scraped_lists:
            if isinstance(res, list):
                all_jobs.extend(res)
            elif isinstance(res, Exception):
                log.error("Scraper failed with error: %s", res)

        total_scraped = len(all_jobs)
        new_jobs_list: list[JobRecord] = []

        for job in all_jobs:
            try:
                is_new = await self.job_repo.upsert(job)
                if is_new:
                    new_jobs_list.append(job)
            except Exception as e:
                log.error("Failed to process job %s: %s", job.job_uid[:8], e)

        if new_jobs_list:
            try:
                await self.tracker.batch_upsert_jobs(new_jobs_list)
            except Exception as sheet_err:
                log.warning("Failed to batch sync jobs to sheet: %s", sheet_err)

        new_jobs = len(new_jobs_list)
        log.info("Discovery complete: scraped=%d, new=%d", total_scraped, new_jobs)
        return {
            "total_scraped": total_scraped,
            "new_jobs": new_jobs,
        }
