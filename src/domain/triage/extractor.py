from __future__ import annotations

"""Extractors for experience requirements and normalized location/country/city."""

import re

from core.entities.job import WorkMode

# Known Indian cities
_INDIAN_CITIES = {
    "bengaluru": "Bengaluru",
    "bangalore": "Bengaluru",
    "hyderabad": "Hyderabad",
    "pune": "Pune",
    "mumbai": "Mumbai",
    "bombay": "Mumbai",
    "delhi": "Delhi",
    "new delhi": "Delhi",
    "noida": "Noida",
    "gurgaon": "Gurugram",
    "gurugram": "Gurugram",
    "chennai": "Chennai",
    "kolkata": "Kolkata",
    "ahmedabad": "Ahmedabad",
}

# Known Global countries & country indicators
_COUNTRIES = {
    "india": "India",
    "united states": "USA",
    "usa": "USA",
    "us": "USA",
    "uk": "UK",
    "united kingdom": "UK",
    "canada": "Canada",
    "germany": "Germany",
    "france": "France",
    "singapore": "Singapore",
    "australia": "Australia",
    "netherlands": "Netherlands",
    "ireland": "Ireland",
    "switzerland": "Switzerland",
}

_EXP_PATTERNS = [
    # "3-5 years", "3 to 5 years", "3 - 5 yrs"
    re.compile(r"\b(\d{1,2})\s*(?:-|to)\s*(\d{1,2})\s*(?:years?|yrs?)\b", re.IGNORECASE),
    # "minimum 3 years", "at least 4 years", "min 2 years"
    re.compile(r"\b(?:minimum|min\.?|at least)\s*(\d{1,2})\+?\s*(?:years?|yrs?)\b", re.IGNORECASE),
    # "3+ years of experience", "5+ years experience"
    re.compile(
        r"\b(\d{1,2})\+?\s*(?:years?|yrs?)\s*(?:of\s*)?(?:relevant\s*|hands[- ]on\s*)?(?:experience|exp)\b",
        re.IGNORECASE,
    ),
    # "3+ years in/with ML"
    re.compile(r"\b(\d{1,2})\+?\s*(?:years?|yrs?)\s*(?:in|with)\b", re.IGNORECASE),
]


def extract_experience(title: str, description: str) -> tuple[int | None, int | None]:
    """Extract minimum and maximum years of experience required."""
    text = (title + " " + description[:4000]).lower()

    # Pattern 1: Range "3-5 years"
    match = _EXP_PATTERNS[0].search(text)
    if match:
        try:
            val1, val2 = int(match.group(1)), int(match.group(2))
            if val1 <= 20 and val2 <= 25:
                return (min(val1, val2), max(val1, val2))
        except (ValueError, IndexError):
            pass

    # Pattern 2 & 3: Minimum "X+ years experience"
    for pat in _EXP_PATTERNS[1:]:
        match = pat.search(text)
        if match:
            try:
                val = int(match.group(1))
                if 0 <= val <= 20:
                    return (val, None)
            except (ValueError, IndexError):
                pass

    # Seniority fallback based on title
    title_lower = title.lower()
    if re.search(r"\b(intern|internship|trainee)\b", title_lower):
        return (0, 0)
    if re.search(r"\b(junior|jr\.?|entry|associate|graduate|freshers?)\b", title_lower):
        return (0, 2)
    if re.search(r"\b(senior|sr\.?|principal|lead|staff|director|head)\b", title_lower):
        if re.search(r"\b(staff|principal|director|head)\b", title_lower):
            return (7, None)
        return (5, None)

    return (None, None)


def extract_location(location_str: str, description: str = "") -> tuple[str, str, WorkMode]:
    """Extract (city, country, work_mode) from location text."""
    combined = (location_str + " " + description[:500]).lower()

    # Detect WorkMode
    if "remote" in combined or "work from home" in combined or "anywhere" in combined:
        work_mode = WorkMode.REMOTE
    elif "hybrid" in combined:
        work_mode = WorkMode.HYBRID
    elif "onsite" in combined or "on-site" in combined or "in-office" in combined:
        work_mode = WorkMode.ONSITE
    else:
        work_mode = WorkMode.UNKNOWN

    city = ""
    country = ""

    # Check Indian cities first
    for k, v in _INDIAN_CITIES.items():
        if re.search(rf"\b{re.escape(k)}\b", location_str.lower()):
            city = v
            country = "India"
            break

    # If no Indian city, check known countries
    if not country:
        for k, v in _COUNTRIES.items():
            if re.search(rf"\b{re.escape(k)}\b", location_str.lower()):
                country = v
                break

    # If city still empty, extract first token before comma
    if not city and location_str:
        parts = [p.strip() for p in location_str.split(",") if p.strip()]
        if parts:
            first = parts[0]
            if first.lower() not in ("remote", "unknown", "multiple locations"):
                city = first

    # Default country for remote with unknown country
    if not country and work_mode == WorkMode.REMOTE:
        country = "Remote / Global"

    return (city or "Unknown", country or "Unknown", work_mode)
