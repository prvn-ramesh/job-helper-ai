from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CandidateProfile:
    """Ground-truth candidate profile — loaded from config/profile.yaml."""

    # Personal
    name: str
    email: str
    phone: str
    location: str

    # Experience
    years_of_experience: int
    current_title: str

    # Education
    degree: str
    institution: str
    graduation_year: int

    # One-line summary for screening
    headline: str = ""

    # Work preferences
    desired_roles: list[str] = field(default_factory=list)  # e.g. ["ML Engineer", "AI Engineer"]
    desired_locations: list[str] = field(default_factory=list)
    remote_preference: str = "hybrid"  # remote / hybrid / onsite / any
    min_salary_inr: int | None = None

    # Skills — used by scorer
    primary_skills: list[str] = field(default_factory=list)  # PyTorch, LLM, RAG, CUDA...
    secondary_skills: list[str] = field(default_factory=list)

    # Work auth
    work_authorization: str = "Indian Citizen"
    requires_visa_sponsorship: bool = False

    # Standard answers for ATS screening
    current_ctc_inr: int | None = None
    expected_ctc_inr: int | None = None
    notice_period: str = "Immediate"

    # Resume
    resume_pdf_path: str | None = None  # Path to existing PDF if not auto-generating

    # LinkedIn profile
    linkedin_url: str = ""
    github_url: str = ""
    portfolio_url: str = ""
