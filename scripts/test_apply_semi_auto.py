"""Live Semi-Auto Application Run on First Approved Job."""

import asyncio

from container.container import container
from core.entities.job import JobStatus


async def main():
    print("=" * 70)
    print("PHASE 4: LIVE SEMI-AUTO ATS APPLIER EXECUTION")
    print("=" * 70)

    # 1. Fetch first approved job
    approved_jobs = await container.job_repo.get_by_status(JobStatus.APPROVED)
    if not approved_jobs:
        print("No approved jobs found in database to apply to.")
        return

    job = approved_jobs[0]
    print(f"Target Job:     {job.title} at {job.company}")
    print(f"Platform:       {job.platform}")
    print(f"URL:            {job.apply_url}")
    print(f"Application Mode: {container.settings.application_mode}")
    print(f"Resume Path:    {container.profile.resume_pdf_path}")
    print("-" * 70)

    # 2. Run Apply Workflow
    print("Executing application workflow...")
    result = await container.apply_workflow.apply_to_job(job.job_uid)

    print("-" * 70)
    print("APPLICATION RESULT:")
    print(f"  Success:         {result.success}")
    print(f"  Status:          {result.status}")
    print(f"  Screenshot:      {result.screenshot_path}")
    print(f"  Filled Fields:   {len(result.filled_fields)} fields populated")
    for k, v in list(result.filled_fields.items())[:8]:
        print(f"    - {k}: {v}")
    if result.error_message:
        print(f"  Error:           {result.error_message}")
    if result.confirmation_text:
        print(f"  Confirmation:    {result.confirmation_text}")

    # 3. Check Review Gate Queue
    pending = container.review_gate.list_pending_reviews()
    print("-" * 70)
    print(f"Review Gate Queue: {len(pending)} pending review items")
    for r in pending:
        print(f"  Item UID: {r.job_uid[:12]} | Company: {r.company} | Status: {r.status}")
        print(f"  Screenshot: {r.screenshot_path}")

    # Clean up browser
    await container.browser_manager.close()
    print("=" * 70)
    print("Phase 4 live test complete!")


if __name__ == "__main__":
    asyncio.run(main())
