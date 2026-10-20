from __future__ import annotations

"""Direct REST API scraper for Greenhouse, Lever, and Ashby job boards.

Free, public, zero captchas, zero browser overhead.
Queries official public job board endpoints.
"""

import asyncio
import html
import logging
import re

import httpx

from core.entities.job import EligibilityVerdict, JobRecord, JobStatus, WorkMode
from core.entities.profile import CandidateProfile
from core.interfaces.scrapers.i_scraper import IScraper
from domain.triage.dedup import compute_job_uid
from domain.triage.extractor import extract_experience, extract_location

log = logging.getLogger(__name__)

# Core keywords to match in title
TITLE_KEYWORDS = [
    "machine learning",
    "ml",
    "ai",
    "llm",
    "deep learning",
    "nlp",
    "computer vision",
    "artificial intelligence",
    "applied scientist",
    "research engineer",
    "genai",
    "prompt",
]


def _matches_keywords(title: str) -> bool:
    title_lower = title.lower()
    return any(re.search(rf"\b{re.escape(kw)}\b", title_lower) for kw in TITLE_KEYWORDS)


def _detect_work_mode(text: str) -> WorkMode:
    text_lower = text.lower()
    if "remote" in text_lower or "work from home" in text_lower:
        return WorkMode.REMOTE
    if "hybrid" in text_lower:
        return WorkMode.HYBRID
    if "onsite" in text_lower or "on-site" in text_lower or "office" in text_lower:
        return WorkMode.ONSITE
    return WorkMode.UNKNOWN


class ATSDirectScraper(IScraper):
    platform = "ats_direct"

    def __init__(self, ats_companies: dict[str, list[str]]) -> None:
        self.ats_companies = ats_companies

    async def scrape(self, profile: CandidateProfile) -> list[JobRecord]:
        results: list[JobRecord] = []
        limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)
        async with httpx.AsyncClient(timeout=15.0, limits=limits, follow_redirects=True) as client:
            tasks = []
            for company in self.ats_companies.get("greenhouse", []):
                tasks.append(self._scrape_greenhouse(client, company))
            for company in self.ats_companies.get("lever", []):
                tasks.append(self._scrape_lever(client, company))
            for company in self.ats_companies.get("ashby", []):
                tasks.append(self._scrape_ashby(client, company))

            outcomes = await asyncio.gather(*tasks, return_exceptions=True)
            for outcome in outcomes:
                if isinstance(outcome, list):
                    results.extend(outcome)
                elif isinstance(outcome, Exception):
                    log.debug("ATS direct scraping failure: %s", outcome)

        log.info("ATSDirectScraper found %d matching jobs across ATS boards", len(results))
        return results

    async def _scrape_greenhouse(self, client: httpx.AsyncClient, slug: str) -> list[JobRecord]:
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
        try:
            resp = await client.get(url)
            if resp.status_code != 200:
                return []
            data = resp.json()
            jobs = data.get("jobs", [])
            records: list[JobRecord] = []
            for j in jobs:
                title = j.get("title", "")
                if not _matches_keywords(title):
                    continue
                loc = (j.get("location") or {}).get("name", "Unknown")
                raw_content = j.get("content", "")
                desc = html.unescape(re.sub(r"<[^>]+>", " ", raw_content))
                apply_url = j.get("absolute_url", "")
                company = slug.replace("-", " ").title()
                uid = compute_job_uid(company, title, loc)
                city, country, mode = extract_location(loc, desc)
                min_exp, max_exp = extract_experience(title, desc)
                records.append(
                    JobRecord(
                        job_uid=uid,
                        title=title,
                        company=company,
                        location=loc,
                        city=city,
                        country=country,
                        min_experience_years=min_exp,
                        max_experience_years=max_exp,
                        platform="greenhouse",
                        apply_url=apply_url,
                        job_id_external=str(j.get("id", "")),
                        description=desc.strip(),
                        work_mode=mode,
                        status=JobStatus.DISCOVERED,
                        eligibility=EligibilityVerdict.ELIGIBLE,
                    )
                )
            return records
        except Exception as e:
            log.debug("Greenhouse %s error: %s", slug, e)
            return []

    async def _scrape_lever(self, client: httpx.AsyncClient, slug: str) -> list[JobRecord]:
        url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
        try:
            resp = await client.get(url)
            if resp.status_code != 200:
                return []
            jobs = resp.json()
            if not isinstance(jobs, list):
                return []
            records: list[JobRecord] = []
            for j in jobs:
                title = j.get("text", "")
                if not _matches_keywords(title):
                    continue
                cats = j.get("categories") or {}
                loc = cats.get("location", "Unknown")
                desc = j.get("descriptionPlain", "") or ""
                apply_url = j.get("hostedUrl", "")
                company = slug.replace("-", " ").title()
                uid = compute_job_uid(company, title, loc)
                city, country, mode = extract_location(loc, desc)
                min_exp, max_exp = extract_experience(title, desc)
                records.append(
                    JobRecord(
                        job_uid=uid,
                        title=title,
                        company=company,
                        location=loc,
                        city=city,
                        country=country,
                        min_experience_years=min_exp,
                        max_experience_years=max_exp,
                        platform="lever",
                        apply_url=apply_url,
                        job_id_external=str(j.get("id", "")),
                        description=desc.strip(),
                        work_mode=mode,
                        status=JobStatus.DISCOVERED,
                        eligibility=EligibilityVerdict.ELIGIBLE,
                    )
                )
            return records
        except Exception as e:
            log.debug("Lever %s error: %s", slug, e)
            return []

    async def _scrape_ashby(self, client: httpx.AsyncClient, slug: str) -> list[JobRecord]:
        url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
        try:
            resp = await client.get(url)
            if resp.status_code != 200:
                return []
            data = resp.json()
            jobs = data.get("jobPostings", [])
            records: list[JobRecord] = []
            for j in jobs:
                title = j.get("title", "")
                if not _matches_keywords(title):
                    continue
                loc = j.get("locationName", "Unknown")
                desc_html = j.get("descriptionHtml", "")
                desc = html.unescape(re.sub(r"<[^>]+>", " ", desc_html))
                apply_url = j.get("jobPostingUrl", "")
                company = slug.replace("-", " ").title()
                uid = compute_job_uid(company, title, loc)
                city, country, mode = extract_location(loc, desc)
                min_exp, max_exp = extract_experience(title, desc)
                records.append(
                    JobRecord(
                        job_uid=uid,
                        title=title,
                        company=company,
                        location=loc,
                        city=city,
                        country=country,
                        min_experience_years=min_exp,
                        max_experience_years=max_exp,
                        platform="ashby",
                        apply_url=apply_url,
                        job_id_external=str(j.get("id", "")),
                        description=desc.strip(),
                        work_mode=mode,
                        status=JobStatus.DISCOVERED,
                        eligibility=EligibilityVerdict.ELIGIBLE,
                    )
                )
            return records
        except Exception as e:
            log.debug("Ashby %s error: %s", slug, e)
            return []
