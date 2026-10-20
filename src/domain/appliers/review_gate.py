from __future__ import annotations

"""Human-in-the-Loop Review Gate.

Enforces application approval workflows:
- In semi-auto mode: Fills form, captures verification screenshot, records state in review queue,
  and halts before submission.
- In full-auto mode: Fills form, captures pre-submit screenshot, submits, and records confirmation.
"""

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from core.config import settings
from core.entities.job import JobRecord

log = logging.getLogger(__name__)


@dataclass
class ReviewItem:
    job_uid: str
    company: str
    title: str
    url: str
    platform: str
    screenshot_path: str
    filled_fields: dict[str, Any]
    status: str = "pending"  # "pending" | "approved" | "rejected"
    notes: str = ""


class ReviewGate:
    def __init__(self, review_queue_path: str = "data/pending_reviews.json") -> None:
        self.queue_path = Path(review_queue_path)
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)

    def is_auto_submit_enabled(self) -> bool:
        """Check if autonomous submission is active."""
        return settings.application_mode.lower() == "full-auto"

    def record_pending_review(
        self,
        job: JobRecord,
        platform: str,
        screenshot_path: str,
        filled_fields: dict[str, Any],
        notes: str = "Awaiting candidate review",
    ) -> ReviewItem:
        """Store filled application for human inspection."""
        item = ReviewItem(
            job_uid=job.uid,
            company=job.company,
            title=job.title,
            url=job.url,
            platform=platform,
            screenshot_path=screenshot_path,
            filled_fields=filled_fields,
            status="pending",
            notes=notes,
        )

        reviews = self.list_pending_reviews()
        # Deduplicate by job_uid
        reviews = [r for r in reviews if r.job_uid != job.uid]
        reviews.append(item)
        self._save(reviews)

        log.info("Job '%s' at %s registered in review gate: %s", job.title, job.company, screenshot_path)
        return item

    def list_pending_reviews(self) -> list[ReviewItem]:
        """Load all review items from queue."""
        if not self.queue_path.exists():
            return []
        try:
            data = json.loads(self.queue_path.read_text())
            return [ReviewItem(**d) for d in data]
        except Exception as e:
            log.warning("Could not read review queue: %s", e)
            return []

    def approve(self, job_uid: str) -> bool:
        """Approve a pending review item."""
        reviews = self.list_pending_reviews()
        found = False
        for r in reviews:
            if r.job_uid == job_uid:
                r.status = "approved"
                found = True
        if found:
            self._save(reviews)
            log.info("Approved review item %s for submission", job_uid)
        return found

    def reject(self, job_uid: str, reason: str = "") -> bool:
        """Reject a pending review item."""
        reviews = self.list_pending_reviews()
        found = False
        for r in reviews:
            if r.job_uid == job_uid:
                r.status = "rejected"
                r.notes = reason
                found = True
        if found:
            self._save(reviews)
            log.info("Rejected review item %s: %s", job_uid, reason)
        return found

    def _save(self, items: list[ReviewItem]) -> None:
        self.queue_path.write_text(json.dumps([asdict(i) for i in items], indent=2))
