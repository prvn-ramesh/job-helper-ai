from __future__ import annotations

from abc import ABC, abstractmethod

from core.entities.job import JobRecord
from core.entities.profile import CandidateProfile


class IApplier(ABC):
    """Port for any job application automation."""

    platform: str

    @abstractmethod
    async def fill_application(self, job: JobRecord, profile: CandidateProfile) -> bool:
        """Fill out job application up to review gate."""

    @abstractmethod
    async def submit_application(self, job: JobRecord) -> bool:
        """Submit the reviewed application."""
