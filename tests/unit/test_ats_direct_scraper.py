from core.entities.job import WorkMode
from domain.scrapers.ats_direct_scraper import _detect_work_mode, _matches_keywords


def test_matches_keywords():
    assert _matches_keywords("Senior Machine Learning Engineer") is True
    assert _matches_keywords("Staff AI Engineer") is True
    assert _matches_keywords("LLM Systems Specialist") is True
    assert _matches_keywords("Accountant") is False
    assert _matches_keywords("Frontend React Developer") is False


def test_detect_work_mode():
    assert _detect_work_mode("Location: Remote (US)") == WorkMode.REMOTE
    assert _detect_work_mode("Hybrid - 3 days in office, Bengaluru") == WorkMode.HYBRID
    assert _detect_work_mode("Onsite, Mountain View, CA") == WorkMode.ONSITE
    assert _detect_work_mode("San Francisco, CA") == WorkMode.UNKNOWN
