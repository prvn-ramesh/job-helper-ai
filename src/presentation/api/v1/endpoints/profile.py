from __future__ import annotations

"""Candidate Profile and Preference Settings Endpoint."""

from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter
from pydantic import BaseModel

from container.container import container
from domain.triage.profile_loader import load_profile

router = APIRouter(prefix="/profile", tags=["profile"])


class ProfileUpdateRequest(BaseModel):
    current_ctc_inr: int | None = None
    expected_ctc_inr: int | None = None
    years_of_experience: int | None = None
    location: str | None = None
    requires_visa_sponsorship: bool | None = None
    notice_period: str | None = None
    resume_strategy: str | None = None  # "uploaded_pdf" | "auto_tailor"


@router.get("")
async def get_profile() -> dict[str, Any]:
    """Retrieve active candidate profile and screening preferences."""
    p = container.profile
    prefs_file = Path("config/profile.yaml")
    raw_yaml = yaml.safe_load(prefs_file.read_text()) if prefs_file.exists() else {}

    return {
        "name": p.name,
        "email": p.email,
        "phone": p.phone,
        "location": p.location,
        "current_title": p.current_title,
        "years_of_experience": p.years_of_experience,
        "degree": p.degree,
        "institution": p.institution,
        "graduation_year": p.graduation_year,
        "primary_skills": p.primary_skills,
        "secondary_skills": p.secondary_skills,
        "work_authorization": p.work_authorization,
        "requires_visa_sponsorship": p.requires_visa_sponsorship,
        "current_ctc_inr": p.current_ctc_inr,
        "expected_ctc_inr": p.expected_ctc_inr,
        "notice_period": p.notice_period,
        "resume_pdf_path": p.resume_pdf_path,
        "resume_strategy": raw_yaml.get("resume_strategy", "uploaded_pdf"),
        "linkedin_url": p.linkedin_url,
        "github_url": p.github_url,
        "portfolio_url": p.portfolio_url,
    }


@router.put("")
async def update_profile(req: ProfileUpdateRequest) -> dict[str, Any]:
    """Update compensation, experience, visa, and resume preferences."""
    profile_path = Path("config/profile.yaml")
    answers_path = Path("config/answers.yaml")

    profile_data = yaml.safe_load(profile_path.read_text()) if profile_path.exists() else {}
    answers_data = yaml.safe_load(answers_path.read_text()) if answers_path.exists() else {}

    if req.current_ctc_inr is not None:
        profile_data["current_ctc_inr"] = req.current_ctc_inr
        answers_data.setdefault("compensation", {})["current_ctc_inr"] = req.current_ctc_inr

    if req.expected_ctc_inr is not None:
        profile_data["expected_ctc_inr"] = req.expected_ctc_inr
        answers_data.setdefault("compensation", {})["expected_ctc_inr"] = req.expected_ctc_inr

    if req.years_of_experience is not None:
        profile_data["years_of_experience"] = req.years_of_experience
        answers_data.setdefault("experience", {})["total_years"] = req.years_of_experience

    if req.location is not None:
        profile_data["location"] = req.location
        answers_data.setdefault("personal", {})["city"] = req.location

    if req.requires_visa_sponsorship is not None:
        profile_data["requires_visa_sponsorship"] = req.requires_visa_sponsorship
        answers_data.setdefault("work_authorization", {})["requires_visa_sponsorship"] = req.requires_visa_sponsorship

    if req.notice_period is not None:
        profile_data["notice_period"] = req.notice_period
        answers_data.setdefault("compensation", {})["notice_period"] = req.notice_period

    if req.resume_strategy is not None:
        profile_data["resume_strategy"] = req.resume_strategy

    profile_path.write_text(yaml.dump(profile_data, sort_keys=False))
    answers_path.write_text(yaml.dump(answers_data, sort_keys=False))

    # Reload profile in container
    container.profile = load_profile(str(profile_path))
    container.dict_answerer.data = answers_data

    return {"status": "updated", "profile": await get_profile()}
