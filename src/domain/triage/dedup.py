from __future__ import annotations

"""Cross-source job deduplication using sha256(company|title|location).

Ported from JobAggregator/src/job_aggregator/pipeline/dedup.py with
AI/ML-specific suffix stripping and location normalization.
"""

import hashlib
import re

# Strip legal entity noise from company names
_COMPANY_SUFFIXES = re.compile(
    r"\b(inc|corp|corporation|llc|ltd|pvt|private|limited|technologies|"
    r"technology|tech|labs|lab|ai|solutions|services|systems|group|"
    r"holdings|ventures|partners|global|india|innovations?)\b",
    re.IGNORECASE,
)

# Location alias normalization
_LOCATION_ALIASES: dict[str, str] = {
    "bangalore": "bengaluru",
    "banglore": "bengaluru",
    "blr": "bengaluru",
    "bombay": "mumbai",
    "ncr": "delhi",
    "new delhi": "delhi",
    "wfh": "remote",
    "work from home": "remote",
    "anywhere": "remote",
    "pan india": "india",
}


def _normalize_company(name: str) -> str:
    name = re.sub(r"[^\w\s]", " ", name.lower())
    name = _COMPANY_SUFFIXES.sub("", name)
    return re.sub(r"\s+", " ", name).strip()


def _normalize_location(loc: str) -> str:
    loc = loc.lower().strip()
    # Remove country suffixes like ", india" or ", us"
    loc = re.sub(r",\s*(india|us|usa|uk|remote)$", "", loc).strip()
    return _LOCATION_ALIASES.get(loc, loc)


def _normalize_title(title: str) -> str:
    title = title.lower().strip()
    # Remove seniority prefixes to collapse duplicates
    title = re.sub(r"^(senior|sr\.?|junior|jr\.?|lead|staff|principal|mid|l[0-9])\s+", "", title)
    return title


def compute_job_uid(company: str, title: str, location: str) -> str:
    """Compute cross-source dedup key — sha256(company|title|location)."""
    key = "|".join(
        [
            _normalize_company(company),
            _normalize_title(title),
            _normalize_location(location),
        ]
    )
    return hashlib.sha256(key.encode()).hexdigest()
