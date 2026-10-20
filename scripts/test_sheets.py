#!/usr/bin/env python3
"""Phase 0 validation: verify Google Sheets connection and write a test job row."""

import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add src to pythonpath
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.entities.job import EligibilityVerdict, JobRecord, JobStatus, WorkMode
from domain.triage.dedup import compute_job_uid
from domain.triage.profile_loader import load_profile
from infrastructure.sheets.sheets_tracker import SheetsTracker


async def main() -> None:
    print("1. Loading candidate profile...")
    profile = load_profile("config/profile.yaml")
    print(f"   Candidate: {profile.name} ({profile.current_title})")

    print("\n2. Connecting to Google Sheets...")
    tracker = SheetsTracker()

    test_uid = compute_job_uid("Test Corp", "Senior ML Engineer", "Bengaluru")
    test_job = JobRecord(
        job_uid=test_uid,
        title="Senior ML Engineer",
        company="Test Corp",
        location="Bengaluru",
        platform="test_script",
        apply_url="https://example.com/jobs/ml-engineer-test",
        job_id_external="test-001",
        description="Developing LLM agents and multi-modal models.",
        work_mode=WorkMode.HYBRID,
        status=JobStatus.DISCOVERED,
        score=9.5,
        eligibility=EligibilityVerdict.ELIGIBLE,
        discovered_at=datetime.now(UTC),
        notes="Automated Phase 0 connection verification row",
    )

    print(f"3. Upserting test job (UID: {test_uid[:12]})...")
    await tracker.upsert_job(test_job)
    print("✅ Successfully wrote test job row to Google Sheets!")


if __name__ == "__main__":
    asyncio.run(main())
