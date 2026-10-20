from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from playwright.async_api import async_playwright

from application.workflows.apply_workflow import ApplyWorkflow
from core.entities.job import JobRecord, JobStatus, WorkMode
from core.entities.profile import CandidateProfile
from domain.appliers.ashby_applier import AshbyApplier
from domain.appliers.base_applier import ApplyResult
from domain.appliers.greenhouse_applier import GreenhouseApplier
from domain.appliers.lever_applier import LeverApplier
from domain.appliers.review_gate import ReviewGate
from domain.qa.dict_answerer import DictAnswerer
from domain.qa.qa_engine import QAEngine
from infrastructure.browser.browser_manager import BrowserManager


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
        resume_pdf_path="tests/fixtures/mock_resume.pdf",
    )


@pytest.fixture
def sample_job():
    return JobRecord(
        job_uid="gh_test_12345",
        title="ML Engineer",
        company="Anthropic",
        location="Remote",
        platform="greenhouse",
        apply_url="https://boards.greenhouse.io/anthropic/jobs/12345",
        status=JobStatus.APPROVED,
        score=8.5,
        work_mode=WorkMode.REMOTE,
        discovered_at=datetime.now(UTC),
    )


def test_can_handle_urls():
    bm = MagicMock()
    qa = MagicMock()
    rg = MagicMock()

    gh = GreenhouseApplier(bm, qa, rg)
    assert gh.can_handle("https://boards.greenhouse.io/openai/jobs/123") is True
    assert gh.can_handle("https://job-boards.greenhouse.io/company/jobs/456") is True
    assert gh.can_handle("https://jobs.lever.co/anthropic/789") is False

    lever = LeverApplier(bm, qa, rg)
    assert lever.can_handle("https://jobs.lever.co/anthropic/789") is True
    assert lever.can_handle("https://boards.greenhouse.io/test/123") is False

    ashby = AshbyApplier(bm, qa, rg)
    assert ashby.can_handle("https://jobs.ashbyhq.com/midjourney/abc") is True
    assert ashby.can_handle("https://jobs.lever.co/test/123") is False


def test_review_gate(tmp_path, sample_job):
    queue_file = str(tmp_path / "reviews.json")
    gate = ReviewGate(queue_file)

    # Record pending review
    item = gate.record_pending_review(
        job=sample_job,
        platform="greenhouse",
        screenshot_path="/path/to/shot.png",
        filled_fields={"first_name": "Praveen", "email": "praveen14aug01@gmail.com"},
    )
    assert item.status == "pending"

    # List items
    pending = gate.list_pending_reviews()
    assert len(pending) == 1
    assert pending[0].job_uid == sample_job.uid
    assert pending[0].company == "Anthropic"

    # Approve
    assert gate.approve(sample_job.uid) is True
    updated = gate.list_pending_reviews()
    assert updated[0].status == "approved"

    # Reject
    assert gate.reject(sample_job.uid, reason="Wrong compensation") is True
    updated = gate.list_pending_reviews()
    assert updated[0].status == "rejected"
    assert updated[0].notes == "Wrong compensation"


@pytest.mark.asyncio
async def test_greenhouse_form_filling(candidate_profile, tmp_path):
    """Test standard Greenhouse form element filling using headless Playwright."""
    html = """
    <html>
      <body>
        <form id="application_form">
          <input id="first_name" name="job_application[first_name]" type="text" />
          <input id="last_name" name="job_application[last_name]" type="text" />
          <input id="email" name="job_application[email]" type="email" />
          <input id="phone" name="job_application[phone]" type="tel" />
          <input id="job_application_location" name="job_application[location]" type="text" />
          <input id="linkedin" name="job_application[answers][linkedin]" type="text" />
          <input id="github" name="job_application[answers][github]" type="text" />
          <div class="field">
            <label>Notice period:</label>
            <select name="job_application[answers][notice]">
              <option value="">Select an option</option>
              <option value="15 Days">15 Days</option>
              <option value="Immediate">Immediate</option>
              <option value="30 Days">30 Days</option>
            </select>
          </div>
        </form>
      </body>
    </html>
    """

    bm = BrowserManager(headless=True)
    dict_ans = DictAnswerer("config/answers.yaml")
    qa = QAEngine(dict_answerer=dict_ans)
    rg = ReviewGate(str(tmp_path / "gate.json"))
    applier = GreenhouseApplier(bm, qa, rg)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(html)

        filled = {}
        await applier._fill_standard_fields(page, candidate_profile, filled)

        assert await page.input_value("#first_name") == "Praveen"
        assert await page.input_value("#last_name") == "Ramesh"
        assert await page.input_value("#email") == "praveen14aug01@gmail.com"
        assert await page.input_value("#phone") == "+91 9019397062"
        assert await page.input_value("#job_application_location") == "Bengaluru, India"
        assert await page.input_value("#linkedin") == "https://linkedin.com/in/prvn-ramesh"
        assert await page.input_value("#github") == "https://github.com/prvn-ramesh"

        # Custom question
        await applier._answer_custom_questions(page, candidate_profile, filled)
        select_val = await page.input_value("select[name='job_application[answers][notice]']")
        assert select_val == "Immediate"

        await browser.close()
    await bm.close()


@pytest.mark.asyncio
async def test_apply_workflow_dispatch_semi_auto(sample_job, candidate_profile, tmp_path):
    repo = MagicMock()
    repo.get_by_uid = AsyncMock(return_value=sample_job)
    repo.update_application_result = AsyncMock()

    tracker = MagicMock()
    tracker.update_status = AsyncMock()

    review_gate = ReviewGate(str(tmp_path / "review_gate.json"))

    mock_applier = MagicMock()
    mock_applier.platform_name = "greenhouse"
    mock_applier.can_handle = MagicMock(return_value=True)
    mock_applier.apply = AsyncMock(
        return_value=ApplyResult(
            success=True,
            status="pending_review",
            screenshot_path="/data/screenshots/gh_shot.png",
            filled_fields={"first_name": "Praveen"},
            confirmation_text="Awaiting candidate review",
        )
    )

    wf = ApplyWorkflow(
        job_repo=repo,
        tracker=tracker,
        appliers=[mock_applier],
        profile=candidate_profile,
        review_gate=review_gate,
    )

    result = await wf.apply_to_job(sample_job.uid)
    assert result.status == "pending_review"
    assert result.success is True
    repo.update_application_result.assert_awaited_once()
    tracker.update_status.assert_awaited_once()
