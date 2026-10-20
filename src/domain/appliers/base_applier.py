from __future__ import annotations

"""Base Abstract Applier for ATS Job Applications."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from core.entities.job import JobRecord
from core.entities.profile import CandidateProfile
from domain.appliers.review_gate import ReviewGate
from domain.qa.qa_engine import QAEngine
from infrastructure.browser.browser_manager import BrowserManager


@dataclass
class ApplyResult:
    success: bool
    status: str  # "applied" | "pending_review" | "failed"
    screenshot_path: str
    filled_fields: dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    confirmation_text: str = ""


class BaseApplier(ABC):
    def __init__(
        self,
        browser_manager: BrowserManager,
        qa_engine: QAEngine,
        review_gate: ReviewGate,
    ) -> None:
        self.browser_manager = browser_manager
        self.qa_engine = qa_engine
        self.review_gate = review_gate

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Name of the ATS platform (e.g., 'greenhouse', 'lever', 'ashby')."""
        ...

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Return True if this applier handles the given application URL."""
        ...

    @abstractmethod
    async def apply(
        self,
        job: JobRecord,
        profile: CandidateProfile,
        resume_path: str | None = None,
    ) -> ApplyResult:
        """Execute the application process for the given job."""
        ...
