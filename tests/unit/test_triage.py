import pytest

from core.entities.job import EligibilityVerdict, JobRecord, WorkMode
from core.entities.profile import CandidateProfile
from domain.triage.eligibility import check_eligibility
from domain.triage.scorer import score_job


@pytest.fixture
def candidate_profile():
    return CandidateProfile(
        name="Praveen",
        email="praveen@example.com",
        phone="9876543210",
        location="Bengaluru, India",
        years_of_experience=2,
        current_title="AI Engineer",
        degree="B.Tech",
        institution="IIT",
        graduation_year=2022,
        primary_skills=["PyTorch", "LLM", "RAG", "Transformers", "CUDA"],
        secondary_skills=["Docker", "FastAPI", "Python", "Git"],
        requires_visa_sponsorship=False,
    )


@pytest.fixture
def filter_rules():
    return {
        "requires_visa_sponsorship": False,
        "target_countries": ["India"],
        "target_cities": ["Bengaluru", "Bangalore", "Hyderabad"],
        "allow_any_remote": True,
        "candidate_experience_years": 2,
        "max_experience_gap_allowed": 1,
    }


def test_scorer_high_relevance(candidate_profile):
    job = JobRecord(
        job_uid="test1",
        title="Senior Machine Learning Engineer (LLM & Agents)",
        company="AI Corp",
        location="Bengaluru",
        platform="greenhouse",
        apply_url="https://ai.corp/job/1",
        description="We are looking for an ML Engineer with PyTorch, LLM, RAG, and Transformers experience.",
    )
    score = score_job(job, candidate_profile)
    assert score >= 7.0


def test_scorer_low_relevance(candidate_profile):
    job = JobRecord(
        job_uid="test2",
        title="Sales Director",
        company="Retail Corp",
        location="Bengaluru",
        platform="greenhouse",
        apply_url="https://retail.corp/job/2",
        description="Leading B2B sales and supply chain partnerships.",
    )
    score = score_job(job, candidate_profile)
    assert score < 4.0


def test_eligibility_experience_filter(candidate_profile, filter_rules):
    # Candidate has 2 yrs exp. Job requires 5 yrs -> Should be skipped
    job = JobRecord(
        job_uid="test3",
        title="Staff ML Engineer",
        company="Tech Corp",
        location="Bengaluru",
        platform="lever",
        apply_url="https://tech.corp/3",
        min_experience_years=5,
    )
    verdict, reason = check_eligibility(job, candidate_profile, filter_rules)
    assert verdict == EligibilityVerdict.SKIP
    assert "Requires 5+ yrs exp" in reason


def test_eligibility_foreign_onsite_filter(candidate_profile, filter_rules):
    # Onsite job in San Francisco when candidate has no US visa -> Should be skipped
    job = JobRecord(
        job_uid="test4",
        title="AI Engineer",
        company="SF AI Inc",
        location="San Francisco, CA",
        city="San Francisco",
        country="USA",
        work_mode=WorkMode.ONSITE,
        platform="greenhouse",
        apply_url="https://sf.ai/4",
        min_experience_years=2,
    )
    verdict, reason = check_eligibility(job, candidate_profile, filter_rules)
    assert verdict == EligibilityVerdict.SKIP
    assert "no work visa" in reason


def test_eligibility_remote_allowed(candidate_profile, filter_rules):
    # Remote job worldwide -> Should be eligible regardless of country
    job = JobRecord(
        job_uid="test5",
        title="AI Engineer",
        company="Global AI",
        location="Remote",
        city="Remote",
        country="USA",
        work_mode=WorkMode.REMOTE,
        platform="greenhouse",
        apply_url="https://global.ai/5",
        min_experience_years=2,
    )
    verdict, reason = check_eligibility(job, candidate_profile, filter_rules)
    assert verdict == EligibilityVerdict.ELIGIBLE
    assert reason is None


def test_eligibility_india_city_allowed(candidate_profile, filter_rules):
    # Onsite/Hybrid in Bengaluru -> Eligible!
    job = JobRecord(
        job_uid="test6",
        title="AI Engineer",
        company="Bengaluru AI",
        location="Bengaluru, India",
        city="Bengaluru",
        country="India",
        work_mode=WorkMode.HYBRID,
        platform="greenhouse",
        apply_url="https://blr.ai/6",
        min_experience_years=2,
    )
    verdict, reason = check_eligibility(job, candidate_profile, filter_rules)
    assert verdict == EligibilityVerdict.ELIGIBLE
    assert reason is None
