from __future__ import annotations

"""Eligibility and visa rules evaluator."""

import re
import unicodedata
from typing import Any

from core.entities.job import EligibilityVerdict, JobRecord, WorkMode
from core.entities.profile import CandidateProfile
from domain.triage.extractor import extract_experience, extract_location


def _normalize(s: str | None) -> str:
    if not s:
        return ""
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("utf-8").lower().strip()

# Explicit disqualifiers in JD text
_CLEARANCE_PATTERNS = [
    re.compile(
        r"\b(?:security clearance|secret clearance|top secret|ts/sci|polygraph)\b", re.IGNORECASE
    ),
    re.compile(
        r"\b(?:u\.?s\.?\s*citizenship required|must be a u\.?s\.?\s*citizen|us citizen only)\b",
        re.IGNORECASE,
    ),
]

_NO_SPONSOR_PATTERNS = [
    re.compile(
        r"\b(?:no visa sponsorship|sponsorship is not available|unable to sponsor|will not sponsor)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:not offering sponsorship|without sponsorship|cannot sponsor)\b", re.IGNORECASE
    ),
]

_FOREIGN_LOCATION_TOKENS = (
    "san francisco",
    "new york",
    "seattle",
    "london",
    "mountain view",
    "sunnyvale",
    "boston",
    "austin",
    "toronto",
    "paris",
    "berlin",
    "tokyo",
    "ca |",
    "ny |",
    "wa |",
    ", ca",
    ", ny",
    ", wa",
    ", uk",
    "united states",
)


def check_eligibility(
    job: JobRecord,
    profile: CandidateProfile,
    filter_rules: dict[str, Any] | None = None,
) -> tuple[EligibilityVerdict, str | None]:
    """Evaluate whether candidate is eligible to apply for this job.

    Returns (EligibilityVerdict, rejection_reason_or_None).
    """
    rules = filter_rules or {}
    text = (job.title + " " + job.description[:5000]).lower()

    # 1. Check strict clearance / US citizenship required
    for pat in _CLEARANCE_PATTERNS:
        if pat.search(text):
            return (EligibilityVerdict.SKIP, "Requires security clearance or US citizenship")

    # Fallback extract location and experience if not populated
    city = job.city
    country = job.country
    mode = job.work_mode
    if not city or not country or country.lower() == "unknown" or mode == WorkMode.UNKNOWN:
        ext_city, ext_country, ext_mode = extract_location(job.location, job.description)
        city = city or ext_city
        country = country or ext_country
        if mode == WorkMode.UNKNOWN:
            mode = ext_mode

    # 2. Check Experience requirement
    candidate_exp = rules.get("candidate_experience_years", profile.years_of_experience)
    max_gap = rules.get("max_experience_gap_allowed", 1)
    min_exp = job.min_experience_years
    if min_exp is None:
        min_exp, _ = extract_experience(job.title, job.description)
    if min_exp is not None and min_exp > (candidate_exp + max_gap):
        return (
            EligibilityVerdict.SKIP,
            f"Requires {min_exp}+ yrs exp (candidate has {candidate_exp} yrs, max gap {max_gap})",
        )

    # 3. Check Location & Visa
    is_remote = mode == WorkMode.REMOTE
    allow_remote = rules.get("allow_any_remote", True)

    if is_remote and allow_remote:
        # Check if job explicitly says "US Only Remote" when candidate is outside US
        us_only = (
            "us only" in text or "united states only" in text or "must reside in the us" in text
        )
        if (
            us_only
            and "india" in profile.location.lower()
            and not profile.requires_visa_sponsorship
        ):
            return (EligibilityVerdict.SKIP, "Remote restricted to US residents only")
        return (EligibilityVerdict.ELIGIBLE, None)

    # For non-remote / onsite / hybrid jobs:
    target_countries = [_normalize(c) for c in rules.get("target_countries", ["india"])]
    target_cities = [
        _normalize(c)
        for c in rules.get("target_cities", ["bengaluru", "bangalore", "hyderabad", "remote"])
    ]

    job_country = _normalize(country)
    job_city = _normalize(city)
    job_loc = _normalize(job.location)

    # Check country match
    country_matched = (
        any(tc in job_country or tc in job_loc for tc in target_countries)
        if (job_country or job_loc)
        else False
    )

    # Check city match
    city_matched = any(tc in job_city or tc in job_loc for tc in target_cities)

    # If foreign location and candidate doesn't have visa
    if not country_matched and job_country and job_country not in ("unknown", "remote / global"):
        return (
            EligibilityVerdict.SKIP,
            f"Onsite/Hybrid in {city or 'Unknown'}, {country} (no work visa for this country)",
        )

    # Check for known foreign cities in location text when country is unknown
    if not country_matched and any(tok in job.location.lower() for tok in _FOREIGN_LOCATION_TOKENS):
        return (
            EligibilityVerdict.SKIP,
            f"Onsite/Hybrid in {city or job.location} (no work visa for this country)",
        )

    # If in candidate country but city not targeted
    if country_matched and not city_matched and job_city not in ("unknown", ""):
        has_wildcard = any(c in ("any", "india", "all") for c in target_cities)
        if target_cities and not has_wildcard:
            return (
                EligibilityVerdict.SKIP,
                f"Location {city} not in preferred cities list",
            )

    # 4. Check explicit visa sponsorship refusal in JD for non-remote
    if not is_remote and not country_matched:
        for pat in _NO_SPONSOR_PATTERNS:
            if pat.search(text):
                return (
                    EligibilityVerdict.SKIP,
                    "Job description explicitly refuses visa sponsorship",
                )

    return (EligibilityVerdict.ELIGIBLE, None)
