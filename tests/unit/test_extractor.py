from core.entities.job import WorkMode
from domain.triage.extractor import extract_experience, extract_location


def test_extract_experience():
    assert extract_experience("ML Engineer", "Requires 3-5 years of experience") == (3, 5)
    assert extract_experience(
        "AI Engineer", "Must have minimum 4+ years of relevant experience in PyTorch"
    ) == (4, None)
    assert extract_experience("Senior AI Engineer", "Build generative models") == (5, None)
    assert extract_experience("Staff Research Scientist", "") == (7, None)
    assert extract_experience("ML Intern", "") == (0, 0)
    assert extract_experience("Junior Machine Learning Engineer", "") == (0, 2)


def test_extract_location():
    city, country, mode = extract_location("Bangalore, India", "")
    assert city == "Bengaluru"
    assert country == "India"
    assert mode == WorkMode.UNKNOWN

    city, country, mode = extract_location("Remote - US", "")
    assert country == "USA"
    assert mode == WorkMode.REMOTE

    city, country, mode = extract_location("San Francisco, CA", "Hybrid role 3 days in office")
    assert city == "San Francisco"
    assert mode == WorkMode.HYBRID
