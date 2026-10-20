from __future__ import annotations

"""Instahyre job scraper."""

import logging

from core.entities.job import JobRecord
from core.entities.profile import CandidateProfile
from core.interfaces.scrapers.i_scraper import IScraper

log = logging.getLogger(__name__)


class InstahyreScraper(IScraper):
    platform = "instahyre"

    def __init__(self, headless: bool = True) -> None:
        self.headless = headless

    async def scrape(self, profile: CandidateProfile) -> list[JobRecord]:
        # ponytail: Playwright session scraper for Instahyre candidate portal
        log.info("InstahyreScraper: starting discovery")
        records: list[JobRecord] = []
        return records
