import pytest

from core.entities.profile import CandidateProfile
from domain.qa.anti_hallucination import verify_and_sanitize
from domain.qa.dict_answerer import DictAnswerer
from domain.qa.qa_engine import QAEngine


@pytest.fixture
def candidate_profile():
    return CandidateProfile(
        name="Praveen Ramesh",
        email="praveen14aug01@gmail.com",
        phone="+91 9019397062",
        location="Bengaluru, India",
        years_of_experience=2,
        current_title="Machine Learning Engineer",
        degree="Master of Computer Applications (MCA)",
        institution="Bangalore University",
        graduation_year=2024,
        primary_skills=["Python", "PyTorch", "LLM", "RAG"],
        secondary_skills=["FastAPI", "Docker", "PostgreSQL"],
        requires_visa_sponsorship=False,
        notice_period="Immediate",
        linkedin_url="https://linkedin.com/in/prvn-ramesh",
        github_url="https://github.com/prvn-ramesh",
    )


def test_dict_answerer_notice_period(candidate_profile):
    answerer = DictAnswerer("config/answers.yaml")
    ans = answerer.answer("What is your notice period?", candidate_profile)
    assert ans == "Immediate"

    # With form dropdown options
    options = ["15 Days", "30 Days", "Immediate", "60 Days"]
    opt_ans = answerer.answer("Notice period required:", candidate_profile, options=options)
    assert opt_ans == "Immediate"


def test_dict_answerer_sponsorship(candidate_profile):
    answerer = DictAnswerer("config/answers.yaml")
    ans = answerer.answer(
        "Will you now or in the future require visa sponsorship to work in this country?",
        candidate_profile,
    )
    assert ans == "No"

    # Dropdown options
    options = ["Yes", "No", "Not Applicable"]
    opt_ans = answerer.answer("Require sponsorship?", candidate_profile, options=options)
    assert opt_ans == "No"


def test_dict_answerer_work_auth(candidate_profile):
    answerer = DictAnswerer("config/answers.yaml")
    ans = answerer.answer(
        "Are you legally authorized to work in the country of this role?",
        candidate_profile,
    )
    assert ans == "Yes"


def test_dict_answerer_experience_breakdown(candidate_profile):
    answerer = DictAnswerer("config/answers.yaml")
    py_ans = answerer.answer(
        "How many years of experience do you have with Python?", candidate_profile
    )
    assert py_ans == "2"

    tot_ans = answerer.answer("Total years of professional experience?", candidate_profile)
    assert tot_ans == "2"


def test_dict_answerer_compensation(candidate_profile):
    answerer = DictAnswerer("config/answers.yaml")
    curr_ans = answerer.answer("What is your current CTC?", candidate_profile)
    assert "800000" in str(curr_ans)

    exp_ans = answerer.answer("What is your expected salary?", candidate_profile)
    assert "1500000" in str(exp_ans)


def test_dict_answerer_education_and_links(candidate_profile):
    answerer = DictAnswerer("config/answers.yaml")
    deg_ans = answerer.answer("What is your highest level of education?", candidate_profile)
    assert "Master" in deg_ans

    link_ans = answerer.answer("Please share your LinkedIn profile URL:", candidate_profile)
    assert "linkedin.com/in/prvn-ramesh" in link_ans


def test_anti_hallucination_experience_correction(candidate_profile):
    # Candidate has 2 years exp. An answer claiming 7 years should be corrected!
    sanitized, modified = verify_and_sanitize(
        "How many years of experience do you have?",
        "I have 7 years of deep learning experience",
        candidate_profile,
    )
    assert modified is True
    assert sanitized == "2"


def test_anti_hallucination_sponsorship_correction(candidate_profile):
    # Candidate does NOT require sponsorship. An answer claiming 'Yes' must be corrected to 'No'
    sanitized, modified = verify_and_sanitize(
        "Do you require visa sponsorship?",
        "Yes",
        candidate_profile,
    )
    assert modified is True
    assert sanitized == "No"


@pytest.mark.asyncio
async def test_qa_engine_deterministic_resolution(candidate_profile):
    engine = QAEngine()
    result = await engine.answer_question("What is your notice period?", candidate_profile)
    assert result.source == "dict"
    assert result.answer == "Immediate"
    assert result.confidence == 1.0


def test_dict_answerer_numeric_range_options(candidate_profile):
    answerer = DictAnswerer("config/answers.yaml")
    options = ["Less than 1 year", "1-3 years", "3-5 years", "5+ years"]
    ans = answerer.answer(
        "Years of Python experience?", candidate_profile, options=options
    )
    assert ans == "1-3 years"


def test_dict_answerer_location_and_relocation(candidate_profile):
    answerer = DictAnswerer("config/answers.yaml")
    reloc = answerer.answer("Are you willing to relocate?", candidate_profile)
    assert reloc == "Yes"

    city = answerer.answer("Current city of residence?", candidate_profile)
    assert city == "Bengaluru"


def test_anti_hallucination_notice_period(candidate_profile):
    sanitized, modified = verify_and_sanitize(
        "Notice period required:",
        "90 days",
        candidate_profile,
    )
    assert modified is True
    assert sanitized == "Immediate"

