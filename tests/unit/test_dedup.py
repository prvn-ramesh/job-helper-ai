from domain.triage.dedup import (
    _normalize_company,
    _normalize_location,
    _normalize_title,
    compute_job_uid,
)


def test_dedup_normalization():
    assert _normalize_company("Google India Pvt Ltd") == "google"
    assert _normalize_company("Anthropic Inc.") == "anthropic"
    assert _normalize_location("Bangalore, India") == "bengaluru"
    assert _normalize_location("Remote") == "remote"
    assert _normalize_title("Senior Machine Learning Engineer") == "machine learning engineer"
    assert _normalize_title("Lead AI Engineer") == "ai engineer"


def test_compute_job_uid_consistency():
    uid1 = compute_job_uid("Google LLC", "Senior AI Engineer", "Bangalore, India")
    uid2 = compute_job_uid("Google", "AI Engineer", "Bengaluru")
    assert uid1 == uid2
    assert len(uid1) == 64
