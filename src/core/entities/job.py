from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class JobStatus(str, Enum):
    DISCOVERED = "discovered"
    TRIAGED = "triaged"
    APPROVED = "approved"
    FILTERED_OUT = "filtered_out"
    PENDING_REVIEW = "pending_review"
    APPLIED = "applied"
    REJECTED = "rejected"
    SKIPPED = "skipped"
    # Human-updated
    INTERVIEW = "interview"
    OFFER = "offer"


class WorkMode(str, Enum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    UNKNOWN = "unknown"


class EligibilityVerdict(str, Enum):
    ELIGIBLE = "eligible"
    CAUTION = "caution"
    SKIP = "skip"
    UNKNOWN = "unknown"


@dataclass
class JobRecord:
    """Core job entity — platform-agnostic normalized record."""

    job_uid: str  # sha256(company|title|location)
    title: str
    company: str
    location: str
    platform: str  # linkedin / greenhouse / lever / ashby / wellfound / etc.
    apply_url: str
    job_id_external: str = ""  # ID from the source platform

    description: str = ""
    content_hash: str = ""  # sha256(description) for change detection

    work_mode: WorkMode = WorkMode.UNKNOWN
    city: str = ""
    country: str = ""
    min_experience_years: int | None = None
    max_experience_years: int | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str = "INR"

    status: JobStatus = JobStatus.DISCOVERED
    score: float | None = None  # 1–10 fit score set by triage
    filter_reason: str | None = None  # Why filtered_out
    eligibility: EligibilityVerdict = EligibilityVerdict.UNKNOWN

    discovered_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    applied_at: datetime | None = None

    resume_used: str | None = None  # filename or "auto-tailored"
    cover_note: str | None = None
    notes: str = ""

    # Review gate
    screenshot_path: str | None = None
    filled_fields: str | None = None  # JSON snapshot of filled values
