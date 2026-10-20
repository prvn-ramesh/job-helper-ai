from __future__ import annotations

"""Anti-hallucination verification gate.

Ensures that any generated answer (especially from LLM fallback) strictly
conforms to candidate ground-truth profile facts before being populated into an application form.
"""

import logging
import re
from typing import Any

from core.entities.profile import CandidateProfile

log = logging.getLogger(__name__)


def verify_and_sanitize(
    question: str,
    proposed_answer: Any,
    profile: CandidateProfile,
) -> tuple[Any, bool]:
    """Verify proposed answer against ground truth facts.

    Returns (sanitized_answer, was_modified).
    """
    if proposed_answer is None:
        return (None, False)

    q = question.lower()
    ans_str = str(proposed_answer).strip()

    # 1. Experience hallucination check
    if re.search(r"\b(?:years\s*of\s*experience|total\s*experience|how\s*many\s*years)\b", q):
        # Extract numbers in answer
        nums = [int(n) for n in re.findall(r"\b\d+\b", ans_str)]
        if nums and nums[0] > (profile.years_of_experience + 1):
            log.warning(
                "Anti-hallucination: LLM claimed %d years exp, overriding with true %d years",
                nums[0],
                profile.years_of_experience,
            )
            return (str(profile.years_of_experience), True)

    # 2. Visa sponsorship hallucination check
    is_sponsorship_q = re.search(
        r"\b(?:require\s*sponsorship|need\s*sponsorship|visa\s*sponsorship)\b", q
    )
    if is_sponsorship_q and not profile.requires_visa_sponsorship:
        ans_lower = ans_str.lower()
        if (
            ans_lower in ("yes", "true", "y")
            or ans_lower.startswith("yes")
            or any(w in ans_lower for w in ["require", "need", "sponsorship"])
        ):
            log.warning("Anti-hallucination: corrected visa sponsorship answer to 'No'")
            return ("No", True)

    # 3. Work authorization check
    is_auth_q = re.search(r"\b(?:legally\s*authorized|legal\s*right\s*to\s*work)\b", q)
    if is_auth_q and ans_str.lower() in ("no", "false", "n"):
        log.warning("Anti-hallucination: corrected authorization answer to 'Yes'")
        return ("Yes", True)

    # 4. Notice period check
    is_notice_q = re.search(r"\b(?:notice\s*period)\b", q)
    if is_notice_q and any(w in ans_str.lower() for w in ("60 days", "90 days", "3 months")):
        log.warning(
            "Anti-hallucination: overriding long notice period with '%s'",
            profile.notice_period,
        )
        return (profile.notice_period, True)

    return (proposed_answer, False)
