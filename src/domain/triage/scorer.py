from __future__ import annotations

"""Job scoring engine — computes fit score (1.0 to 10.0) for AI/ML Engineer roles."""

import re

from core.entities.job import JobRecord
from core.entities.profile import CandidateProfile

_DEFAULT_CORE_SKILLS = [
    "pytorch",
    "tensorflow",
    "llm",
    "rag",
    "transformers",
    "cuda",
    "python",
    "machine learning",
    "deep learning",
    "nlp",
    "computer vision",
    "langchain",
    "llamaindex",
    "fine-tuning",
    "prompt engineering",
    "agentic",
    "vllm",
    "tensorrt",
]


def score_job(job: JobRecord, profile: CandidateProfile) -> float:
    """Score a job record from 1.0 to 10.0 based on candidate profile match."""
    score = 1.0
    text = (job.title + " " + job.description[:5000]).lower()
    title_lower = job.title.lower()

    # 1. Title match (up to 4.0 pts)
    target_roles = profile.desired_roles or [
        "machine learning engineer",
        "ai engineer",
        "ml engineer",
        "llm engineer",
        "research engineer",
    ]
    if any(role.lower() in title_lower for role in target_roles):
        score += 3.0
        # Bonus for specific sub-domain matches (LLM, RAG, Agents, Vision, GenAI)
        if any(
            kw in title_lower for kw in ("llm", "agent", "rag", "genai", "deep learning", "nlp")
        ):
            score += 1.0
    elif any(
        kw in title_lower
        for kw in ("ml", "ai", "machine learning", "deep learning", "data science")
    ):
        score += 2.0

    # 2. Primary skills match (up to 4.0 pts)
    primary_skills = profile.primary_skills or _DEFAULT_CORE_SKILLS
    if primary_skills:
        primary_hits = sum(
            1 for s in primary_skills if re.search(rf"\b{re.escape(s.lower())}\b", text)
        )
        ratio = min(1.0, primary_hits / min(len(primary_skills), 4))
        score += ratio * 4.0

    # 3. Secondary skills match (up to 2.0 pts)
    secondary_skills = profile.secondary_skills or ["docker", "fastapi", "git", "aws", "gcp"]
    if secondary_skills:
        secondary_hits = sum(
            1 for s in secondary_skills if re.search(rf"\b{re.escape(s.lower())}\b", text)
        )
        ratio = min(1.0, secondary_hits / min(len(secondary_skills), 3))
        score += ratio * 2.0

    return round(min(10.0, max(1.0, score)), 1)
