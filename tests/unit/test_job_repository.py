import uuid
from datetime import UTC, datetime

import pytest

from core.entities.job import EligibilityVerdict, JobRecord, JobStatus
from infrastructure.database.job_repository import SQLiteJobRepository
from infrastructure.database.sqlite import init_db


@pytest.mark.asyncio
async def test_job_repository_upsert_and_fetch():
    init_db()
    repo = SQLiteJobRepository()

    unique_uid = f"test_{uuid.uuid4().hex}"
    job = JobRecord(
        job_uid=unique_uid,
        title="AI Engineer",
        company="Anthropic",
        location="Remote",
        platform="greenhouse",
        apply_url="https://job.test/1",
        status=JobStatus.DISCOVERED,
        eligibility=EligibilityVerdict.ELIGIBLE,
        discovered_at=datetime.now(UTC),
    )

    is_new = await repo.upsert(job)
    assert is_new is True

    # Duplicate upsert should return False
    is_new_dup = await repo.upsert(job)
    assert is_new_dup is False

    fetched = await repo.get_by_uid(unique_uid)
    assert fetched is not None
    assert fetched.title == "AI Engineer"
    assert fetched.company == "Anthropic"

    # Test update_application_result
    await repo.update_application_result(
        job_uid=unique_uid,
        status=JobStatus.APPLIED,
        screenshot_path="/data/screenshots/test.png",
        notes="Applied via Greenhouse",
        applied_at=datetime.now(UTC),
    )
    updated = await repo.get_by_uid(unique_uid)
    assert updated.status == JobStatus.APPLIED
    assert updated.screenshot_path == "/data/screenshots/test.png"
    assert updated.notes == "Applied via Greenhouse"
    assert updated.applied_at is not None
