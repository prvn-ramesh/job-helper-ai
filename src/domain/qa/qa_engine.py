from __future__ import annotations

"""Unified Question & Answering Engine.

Combines deterministic dictionary lookup with Gemini Flash Lite fallback
and anti-hallucination verification.
"""

import logging
from dataclasses import dataclass
from typing import Any

from core.entities.profile import CandidateProfile
from domain.qa.anti_hallucination import verify_and_sanitize
from domain.qa.dict_answerer import DictAnswerer
from domain.qa.llm_answerer import LLMAnswerer

log = logging.getLogger(__name__)


@dataclass
class AnswerResult:
    answer: Any
    source: str  # "dict" | "llm" | "unresolved"
    confidence: float
    was_sanitized: bool = False


class QAEngine:
    def __init__(
        self,
        dict_answerer: DictAnswerer | None = None,
        llm_answerer: LLMAnswerer | None = None,
    ) -> None:
        self.dict_answerer = dict_answerer or DictAnswerer()
        self.llm_answerer = llm_answerer or LLMAnswerer()

    async def answer_question(
        self,
        question: str,
        profile: CandidateProfile,
        options: list[str] | None = None,
        job_context: str = "",
    ) -> AnswerResult:
        """Resolve a screening question using 2-tier architecture."""
        # Tier 1: Deterministic dictionary lookup (0ms, 0 tokens)
        dict_ans = self.dict_answerer.answer(question, profile, options)
        if dict_ans is not None:
            sanitized, modified = verify_and_sanitize(question, dict_ans, profile)
            return AnswerResult(
                answer=sanitized,
                source="dict",
                confidence=1.0,
                was_sanitized=modified,
            )

        # Tier 2: LLM Fallback (Gemini Flash Lite)
        llm_ans = await self.llm_answerer.answer(question, profile, options, job_context)
        if llm_ans is not None:
            sanitized, modified = verify_and_sanitize(question, llm_ans, profile)
            return AnswerResult(
                answer=sanitized,
                source="llm",
                confidence=0.85,
                was_sanitized=modified,
            )

        return AnswerResult(
            answer=None,
            source="unresolved",
            confidence=0.0,
            was_sanitized=False,
        )
