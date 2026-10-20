from __future__ import annotations

"""LLM Fallback Answerer using Google Gemini Flash Lite."""

import json
import logging
from pathlib import Path

from core.config import settings
from core.entities.profile import CandidateProfile

log = logging.getLogger(__name__)


class LLMAnswerer:
    def __init__(self, pending_path: str = "data/pending_questions.json") -> None:
        self.pending_path = Path(pending_path)
        self.pending_path.parent.mkdir(parents=True, exist_ok=True)
        self._model = None

    def _get_model(self):
        if self._model is not None:
            return self._model
        if not settings.gemini_api_key:
            return None
        try:
            import google.generativeai as genai

            genai.configure(api_key=settings.gemini_api_key)
            model_name = settings.gemini_primary_model or "gemini-2.0-flash-lite"
            self._model = genai.GenerativeModel(model_name)
            return self._model
        except Exception as e:
            log.warning("Could not initialize Gemini model: %s", e)
            return None

    async def answer(
        self,
        question: str,
        profile: CandidateProfile,
        options: list[str] | None = None,
        job_context: str = "",
    ) -> str | None:
        """Generate answer via Gemini Flash Lite using candidate ground truth."""
        model = self._get_model()
        if not model:
            self._record_pending(question, options, job_context)
            return None

        prompt = f"""You are answering an application screening question on behalf of a job candidate.
Be truthful, concise, and professional. Only state facts from the profile below. Never invent claims.

CANDIDATE GROUND TRUTH:
- Name: {profile.name}
- Title: {profile.current_title}
- Years of Experience: {profile.years_of_experience}
- Location: {profile.location}
- Degree: {profile.degree} from {profile.institution} ({profile.graduation_year})
- Primary Skills: {", ".join(profile.primary_skills)}
- Secondary Skills: {", ".join(profile.secondary_skills)}
- Work Authorization: {profile.work_authorization}
- Needs Visa Sponsorship: {profile.requires_visa_sponsorship}
- Notice Period: {profile.notice_period}
- Headline: {profile.headline}

QUESTION:
{question}
"""
        if options:
            prompt += "\nAVAILABLE OPTIONS (choose the most accurate one):\n" + "\n".join(
                f"- {opt}" for opt in options
            )
            prompt += "\nRespond with ONLY the exact text of the best option."
        else:
            prompt += "\nRespond concisely with ONLY the direct answer (1-2 sentences maximum, or direct number/yes/no)."

        try:
            resp = model.generate_content(prompt)
            answer_text = resp.text.strip() if resp and resp.text else ""
            if not answer_text:
                self._record_pending(question, options, job_context)
                return None
            return answer_text
        except Exception as e:
            log.warning("Gemini LLM answer generation failed: %s", e)
            self._record_pending(question, options, job_context)
            return None

    def _record_pending(
        self,
        question: str,
        options: list[str] | None = None,
        job_context: str = "",
    ) -> None:
        """Log unresolved questions for human review."""
        try:
            records = []
            if self.pending_path.exists():
                records = json.loads(self.pending_path.read_text())
            records.append(
                {
                    "question": question,
                    "options": options,
                    "context": job_context,
                }
            )
            self.pending_path.write_text(json.dumps(records, indent=2))
            log.info("Saved unresolved question to %s", self.pending_path)
        except Exception as e:
            log.warning("Failed to record pending question: %s", e)
