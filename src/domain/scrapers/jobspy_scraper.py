from __future__ import annotations

"""JobSpy scraper wrapping LinkedIn, Indeed, Glassdoor, and ZipRecruiter."""

import asyncio
import itertools
import logging
import random
import time
from typing import Any

from core.entities.job import EligibilityVerdict, JobRecord, JobStatus, WorkMode
from core.entities.profile import CandidateProfile
from core.interfaces.scrapers.i_scraper import IScraper
from domain.triage.dedup import compute_job_uid
from domain.triage.extractor import extract_experience, extract_location

log = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
]


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
        proxies: list[str] | None = None,
    ) -> None:
        self.sites = sites or ["indeed", "glassdoor", "linkedin"]
        self.search_terms = search_terms or ["Machine Learning Engineer", "AI Engineer"]
        self.locations = locations or ["Bengaluru, India", "Remote"]
        self.results_per_query = results_per_query
        self.hours_old = hours_old
        self.proxies = [p.strip() for p in (proxies or []) if p.strip()]
        self._proxy_cycle = itertools.cycle(self.proxies) if self.proxies else None
        self._ua_cycle = itertools.cycle(USER_AGENTS)

    def _get_next_proxy(self) -> str | None:
        if self._proxy_cycle:
            return next(self._proxy_cycle)
        return None

    def _get_next_ua(self) -> str:
        return next(self._ua_cycle)

    async def scrape(self, profile: CandidateProfile) -> list[JobRecord]:
        return await asyncio.to_thread(self._scrape_sync)

    def _scrape_sync(self) -> list[JobRecord]:
        try:
            from jobspy import scrape_jobs
        except ImportError:
            log.warning("python-jobspy is not installed")
            return []

        all_records: list[JobRecord] = []
        active_sites = list(self.sites)
        linkedin_blocked = False

        for term in self.search_terms:
            for loc in self.locations:
                # If LinkedIn was flagged 429 and no proxies are configured, avoid repeated 429 spam
                current_sites = [s for s in active_sites if not (linkedin_blocked and s == "linkedin")]
                if not current_sites:
                    continue

                proxy = self._get_next_proxy()
                ua = self._get_next_ua()

                try:
                    log.info(
                        "JobSpy scraping: query='%s', loc='%s', sites=%s, proxy=%s",
                        term,
                        loc,
                        current_sites,
                        "configured" if proxy else "direct",
                    )
                    df = scrape_jobs(
                        site_name=current_sites,
                        search_term=term,
                        location=loc,
                        results_wanted=self.results_per_query,
                        hours_old=self.hours_old,
                        country_indeed="India"
                        if "india" in loc.lower() or "bengaluru" in loc.lower()
                        else "USA",
                        proxies=proxy,
                        user_agent=ua,
                    )

                    # Polite randomized delay between queries to prevent burst rate limits
                    time.sleep(random.uniform(1.5, 3.0))

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
                    err_msg = str(e)
                    if (
                        ("429" in err_msg or "blocked" in err_msg.lower())
                        and not self.proxies
                        and "linkedin" in current_sites
                    ):
                        log.warning(
                            "[JobSpy] LinkedIn 429 rate limit encountered without proxy. "
                            "Temporarily cooling down LinkedIn for this run; continuing with %s",
                            [s for s in current_sites if s != "linkedin"],
                        )
                        linkedin_blocked = True
                    log.warning("JobSpy scrape notice for '%s' in '%s': %s", term, loc, e)

        log.info("JobSpy collected %d jobs", len(all_records))
        return all_records
