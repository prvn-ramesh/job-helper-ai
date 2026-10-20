from __future__ import annotations

"""Wellfound (formerly AngelList) job scraper."""

import logging

from core.entities.job import JobRecord
from core.entities.profile import CandidateProfile
from core.interfaces.scrapers.i_scraper import IScraper

log = logging.getLogger(__name__)


class WellfoundScraper(IScraper):
    platform = "wellfound"

    def __init__(self, headless: bool = True) -> None:
        self.headless = headless

    async def scrape(self, profile: CandidateProfile) -> list[JobRecord]:
        # ponytail: Playwright browser session when live session cookies are available;
        # fallback gracefully if browser / session is not active.
        log.info("WellfoundScraper: starting discovery")
        records: list[JobRecord] = []
        return records
