from datetime import UTC, datetime

import pytest

from application.workflows.discover_workflow import DiscoverWorkflow
from core.entities.job import EligibilityVerdict, JobRecord, JobStatus
from core.entities.profile import CandidateProfile
from core.interfaces.repositories.i_job_repository import IJobRepository
from core.interfaces.scrapers.i_scraper import IScraper
from core.interfaces.trackers.i_tracker import ITracker


class DummyScraper(IScraper):
    platform = "dummy"

    async def scrape(self, profile: CandidateProfile) -> list[JobRecord]:
        return [
            JobRecord(
                job_uid="job_1",
                title="ML Engineer",
                company="Company A",
                location="Remote",
                platform="dummy",
                apply_url="https://a.com/1",
                status=JobStatus.DISCOVERED,
                eligibility=EligibilityVerdict.ELIGIBLE,
                discovered_at=datetime.now(UTC),
            )
        ]


class MockJobRepo(IJobRepository):
    def __init__(self):
        self.jobs = {}

    async def upsert(self, job: JobRecord) -> bool:
        if job.job_uid in self.jobs:
            return False
        self.jobs[job.job_uid] = job
        return True

    async def exists(self, job_uid: str) -> bool:
        return job_uid in self.jobs

    async def get_by_status(self, status: JobStatus) -> list[JobRecord]:
        return [j for j in self.jobs.values() if j.status == status]

    async def update_status(self, job_uid: str, status: JobStatus, **kwargs) -> None:
        if job_uid in self.jobs:
            self.jobs[job_uid].status = status

    async def count_applied_today(self) -> int:
        return 0

    async def get_by_uid(self, job_uid: str):
        return self.jobs.get(job_uid)


class MockTracker(ITracker):
    def __init__(self):
        self.upserted = []

    async def upsert_job(self, job: JobRecord) -> None:
        self.upserted.append(job)

    async def update_status(self, job_uid: str, status: JobStatus, **extra) -> None:
        pass


@pytest.mark.asyncio
async def test_discover_workflow():
    repo = MockJobRepo()
    tracker = MockTracker()
    workflow = DiscoverWorkflow(
        scrapers=[DummyScraper()],
        job_repo=repo,
        tracker=tracker,
    )

    profile = CandidateProfile(
        name="Test Candidate",
        email="test@example.com",
        phone="1234567890",
        location="Bengaluru",
        years_of_experience=3,
        current_title="AI Engineer",
        degree="B.Tech",
        institution="IIT",
        graduation_year=2021,
    )

    result = await workflow.execute(profile)
    assert result["total_scraped"] == 1
    assert result["new_jobs"] == 1
    assert len(tracker.upserted) == 1
    assert "job_1" in repo.jobs

    # Second run should report 0 new jobs
    result2 = await workflow.execute(profile)
    assert result2["total_scraped"] == 1
    assert result2["new_jobs"] == 0
    assert len(tracker.upserted) == 1
