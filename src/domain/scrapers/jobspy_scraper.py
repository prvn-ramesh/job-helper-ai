from __future__ import annotations

"""JobSpy scraper wrapping LinkedIn, Indeed, Glassdoor, and ZipRecruiter."""

import asyncio
import logging
from typing import Any

from core.entities.job import EligibilityVerdict, JobRecord, JobStatus, WorkMode
from core.entities.profile import CandidateProfile
from core.interfaces.scrapers.i_scraper import IScraper
from domain.triage.dedup import compute_job_uid
from domain.triage.extractor import extract_experience, extract_location

log = logging.getLogger(__name__)


def _to_work_mode(is_remote: Any) -> WorkMode:
    if is_remote is True:
        return WorkMode.REMOTE
    return WorkMode.UNKNOWN


class JobSpyScraper(IScraper):
    platform = "jobspy"

    def __init__(
        self,
        sites: list[str] | None = None,
        search_terms: list[str] | None = None,
        locations: list[str] | None = None,
        results_per_query: int = 15,
        hours_old: int = 72,
    ) -> None:
        self.sites = sites or ["linkedin", "indeed", "glassdoor"]
        self.search_terms = search_terms or ["Machine Learning Engineer", "AI Engineer"]
        self.locations = locations or ["Bengaluru, India", "Remote"]
        self.results_per_query = results_per_query
        self.hours_old = hours_old

    async def scrape(self, profile: CandidateProfile) -> list[JobRecord]:
        return await asyncio.to_thread(self._scrape_sync)

    def _scrape_sync(self) -> list[JobRecord]:
        try:
            from jobspy import scrape_jobs
        except ImportError:
            log.warning("python-jobspy is not installed")
            return []

        all_records: list[JobRecord] = []
        for term in self.search_terms:
            for loc in self.locations:
                try:
                    log.info("JobSpy scraping: query='%s', loc='%s'", term, loc)
                    df = scrape_jobs(
                        site_name=self.sites,
                        search_term=term,
                        location=loc,
                        results_wanted=self.results_per_query,
                        hours_old=self.hours_old,
                        country_indeed="India"
                        if "india" in loc.lower() or "bengaluru" in loc.lower()
                        else "USA",
                    )
                    if df is None or df.empty:
                        continue

                    for _, row in df.iterrows():
                        title = str(row.get("title") or "").strip()
                        company = str(row.get("company") or "").strip()
                        job_loc = str(row.get("location") or loc).strip()
                        apply_url = str(row.get("job_url") or "").strip()
                        if not title or not company or not apply_url:
                            continue

                        platform_name = str(row.get("site") or "jobspy").lower()
                        uid = compute_job_uid(company, title, job_loc)
                        desc = str(row.get("description") or "").strip()

                        city, country, mode = extract_location(job_loc, desc)
                        if _to_work_mode(row.get("is_remote")) == WorkMode.REMOTE:
                            mode = WorkMode.REMOTE
                        min_exp, max_exp = extract_experience(title, desc)

                        all_records.append(
                            JobRecord(
                                job_uid=uid,
                                title=title,
                                company=company,
                                location=job_loc,
                                city=city,
                                country=country,
                                min_experience_years=min_exp,
                                max_experience_years=max_exp,
                                platform=platform_name,
                                apply_url=apply_url,
                                job_id_external=str(row.get("id") or ""),
                                description=desc,
                                work_mode=mode,
                                status=JobStatus.DISCOVERED,
                                eligibility=EligibilityVerdict.UNKNOWN,
                            )
                        )
                except Exception as e:
                    log.warning("JobSpy scrape error for '%s' in '%s': %s", term, loc, e)

        log.info("JobSpy collected %d jobs", len(all_records))
        return all_records
