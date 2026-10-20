from domain.triage.profile_loader import load_profile


def test_load_profile():
    profile = load_profile("config/profile.yaml")
    assert profile.name != ""
    assert profile.email != ""
    assert profile.years_of_experience >= 0
    assert len(profile.primary_skills) > 0
    assert isinstance(profile.requires_visa_sponsorship, bool)
