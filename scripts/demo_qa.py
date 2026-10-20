"""Live Phase 3 QA Engine Verification Script."""

import asyncio

from container.container import Container
from domain.qa.anti_hallucination import verify_and_sanitize


async def main():
    print("=" * 60)
    print("PHASE 3 QA ENGINE DEMO")
    print("=" * 60)

    c = Container()
    engine = c.qa_engine
    profile = c.profile

    print(f"Loaded Profile: {profile.name}")
    print(f"Current Role: {profile.current_title} ({profile.years_of_experience} yrs)")
    print(f"Location: {profile.location}")
    print(f"Education: {profile.degree} from {profile.institution} ({profile.graduation_year})")
    print(f"Resume path: {profile.resume_pdf_path}")
    print("-" * 60)

    sample_questions = [
        ("Full Legal Name", None),
        ("Current City of Residence", None),
        ("Are you legally authorized to work in India?", ["Yes", "No"]),
        (
            "Will you now or in the future require visa sponsorship for employment?",
            ["Yes", "No", "Not Applicable"],
        ),
        ("What is your current CTC?", None),
        ("What is your expected salary?", None),
        ("Notice period:", ["Immediate", "15 Days", "30 Days", "60 Days"]),
        ("Total years of professional experience?", ["0-1 years", "1-3 years", "3-5 years", "5+ years"]),
        ("How many years of experience do you have with Python?", None),
        ("How many years of experience do you have with PyTorch / Deep Learning?", None),
        ("How many years of experience with LLMs / RAG?", None),
        ("Highest level of education completed:", ["High School", "Bachelor's", "Master's Degree", "PhD"]),
        ("Please provide your LinkedIn profile URL:", None),
        ("Please provide your GitHub URL:", None),
        ("Are you willing to relocate?", ["Yes", "No"]),
        ("Gender:", ["Male", "Female", "Decline to self-identify"]),
    ]

    print("TESTING DETERMINISTIC SCREENING RESOLUTION:")
    for q, opts in sample_questions:
        res = await engine.answer_question(q, profile, options=opts)
        print(f"  Q: {q}")
        print(f"     -> Answer: '{res.answer}' | Source: {res.source} | Confidence: {res.confidence}")

    print("\nTESTING ANTI-HALLUCINATION GUARD:")
    hallucinated_q = "How many years of ML experience do you have?"
    fake_ans = "I have 8 years of extensive ML engineering experience."
    sanitized, modified = verify_and_sanitize(hallucinated_q, fake_ans, profile)
    print(f"  Q: {hallucinated_q}")
    print(f"  Proposed LLM Answer: '{fake_ans}'")
    print(f"  Sanitized by Guard:  '{sanitized}' (Modified: {modified})")

    hallucinated_visa = "Do you need visa sponsorship?"
    fake_visa = "Yes, I require H1B sponsorship."
    sanitized_v, modified_v = verify_and_sanitize(hallucinated_visa, fake_visa, profile)
    print(f"  Q: {hallucinated_visa}")
    print(f"  Proposed LLM Answer: '{fake_visa}'")
    print(f"  Sanitized by Guard:  '{sanitized_v}' (Modified: {modified_v})")
    print("=" * 60)
    print("Phase 3 QA Engine verification complete!")


if __name__ == "__main__":
    asyncio.run(main())
