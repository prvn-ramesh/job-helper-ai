from __future__ import annotations

"""Profile loader — reads config/profile.yaml into a CandidateProfile entity."""

from pathlib import Path

import yaml

from core.entities.profile import CandidateProfile


def load_profile(path: str = "config/profile.yaml") -> CandidateProfile:
    data = yaml.safe_load(Path(path).read_text())
    return CandidateProfile(
        name=data["name"],
        email=data["email"],
        phone=data["phone"],
        location=data["location"],
        years_of_experience=int(data["years_of_experience"]),
        current_title=data["current_title"],
        headline=data.get("headline", ""),
        degree=data["degree"],
        institution=data["institution"],
        graduation_year=int(data["graduation_year"]),
        desired_roles=data.get("desired_roles", []),
        desired_locations=data.get("desired_locations", []),
        remote_preference=data.get("remote_preference", "any"),
        min_salary_inr=data.get("min_salary_inr"),
        primary_skills=data.get("primary_skills", []),
        secondary_skills=data.get("secondary_skills", []),
        work_authorization=data.get("work_authorization", "Indian Citizen"),
        requires_visa_sponsorship=data.get("requires_visa_sponsorship", False),
        current_ctc_inr=data.get("current_ctc_inr"),
        expected_ctc_inr=data.get("expected_ctc_inr"),
        notice_period=data.get("notice_period", "Immediate"),
        resume_pdf_path=data.get("resume_pdf_path"),
        linkedin_url=data.get("linkedin_url", ""),
        github_url=data.get("github_url", ""),
        portfolio_url=data.get("portfolio_url", ""),
    )
