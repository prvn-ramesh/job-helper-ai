from __future__ import annotations

from abc import ABC, abstractmethod

from core.entities.job import JobRecord
from core.entities.profile import CandidateProfile


class IScraper(ABC):
    """Port for any job discovery scraper."""

    platform: str  # set as class attribute by each implementation

    @abstractmethod
    async def scrape(self, profile: CandidateProfile) -> list[JobRecord]:
        """Scrape and return raw job records (not yet stored)."""
