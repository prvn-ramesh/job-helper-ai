from __future__ import annotations

"""Google Sheets tracker — upserts job rows keyed on Job ID column.

Auth flow: installed app (OAuth 2.0). On first run, opens browser for
Google consent. Token is cached at settings.token_path for all future runs.
"""

import logging

import gspread
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from core.config import settings
from core.entities.job import JobRecord, JobStatus
from core.interfaces.trackers.i_tracker import ITracker

log = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Column headers for the main "Jobs" sheet
HEADERS = [
    "Job ID",
    "Discovered At",
    "Company",
    "Role Title",
    "Platform",
    "City",
    "Country",
    "Remote?",
    "Min Exp",
    "Score",
    "Apply URL",
    "Status",
    "Filtered Reason",
    "Applied At",
    "Resume Used",
    "Visa Eligible?",
    "Cover Note",
    "Notes",
]

# Column headers for the "Filtered" trash tab
TRASH_HEADERS = [
    "Job ID",
    "Discovered At",
    "Company",
    "Role Title",
    "Platform",
    "City",
    "Country",
    "Min Exp",
    "Score",
    "Filtered Reason",
    "Apply URL",
]


def _get_credentials() -> Credentials:
    """Load or refresh OAuth2 credentials, running browser flow if needed."""
    token_path = settings.token_path
    creds = None

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(settings.credentials_path), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json())

    return creds


def _ensure_sheet_structure(spreadsheet) -> tuple:
    """Ensure 'Jobs', 'Filtered', 'Stats' worksheets exist with correct headers."""
    existing = {ws.title for ws in spreadsheet.worksheets()}

    def ensure_ws(title: str, headers: list[str]):
        if title not in existing:
            ws = spreadsheet.add_worksheet(title=title, rows=1000, cols=len(headers))
        else:
            ws = spreadsheet.worksheet(title)
        # Keep headers in sync
        ws.update("A1", [headers])
        ws.format("1:1", {"textFormat": {"bold": True}})
        return ws

    jobs_ws = ensure_ws("Jobs", HEADERS)
    trash_ws = ensure_ws("Filtered", TRASH_HEADERS)

    # Stats sheet — just a placeholder
    if "Stats" not in existing:
        spreadsheet.add_worksheet(title="Stats", rows=50, cols=10)

    return jobs_ws, trash_ws


def _job_to_jobs_row(job: JobRecord) -> list:
    work_mode = job.work_mode.value if job.work_mode else "unknown"
    remote_label = "Yes" if work_mode == "remote" else ("Hybrid" if work_mode == "hybrid" else "No")
    min_exp_str = (
        f"{job.min_experience_years}+ yrs"
        if job.min_experience_years is not None
        else "Not specified"
    )
    return [
        job.job_uid[:12],  # Job ID (short)
        job.discovered_at.strftime("%Y-%m-%d %H:%M"),
        job.company,
        job.title,
        job.platform,
        job.city or job.location,
        job.country or "Unknown",
        remote_label,
        min_exp_str,
        str(job.score) if job.score is not None else "",
        job.apply_url,
        job.status.value,
        job.filter_reason or "",
        job.applied_at.strftime("%Y-%m-%d %H:%M") if job.applied_at else "",
        job.resume_used or "",
        job.eligibility.value,
        job.cover_note or "",
        job.notes,
    ]


def _job_to_trash_row(job: JobRecord) -> list:
    min_exp_str = (
        f"{job.min_experience_years}+ yrs"
        if job.min_experience_years is not None
        else "Not specified"
    )
    return [
        job.job_uid[:12],
        job.discovered_at.strftime("%Y-%m-%d %H:%M"),
        job.company,
        job.title,
        job.platform,
        job.city or job.location,
        job.country or "Unknown",
        min_exp_str,
        str(job.score) if job.score is not None else "",
        job.filter_reason or "",
        job.apply_url,
    ]


class SheetsTracker(ITracker):
    """Google Sheets ITracker implementation.

    Lazily connects on first use so the OAuth browser flow only opens
    when actually needed (not at import time).
    """

    def __init__(self) -> None:
        self._client: gspread.Client | None = None
        self._jobs_ws: gspread.Worksheet | None = None
        self._trash_ws: gspread.Worksheet | None = None

    def _connect(self) -> None:
        if self._client is not None:
            return
        creds = _get_credentials()
        self._client = gspread.authorize(creds)
        spreadsheet = self._client.open_by_key(settings.google_sheets_id)
        self._jobs_ws, self._trash_ws = _ensure_sheet_structure(spreadsheet)
        log.info("✅ Connected to Google Sheets: %s", spreadsheet.title)

    def _find_row(self, ws: gspread.Worksheet, job_uid_short: str) -> int | None:
        """Return 1-based row index if job_uid found in column A, else None."""
        col_values = ws.col_values(1)
        for i, val in enumerate(col_values[1:], start=2):  # skip header
            if val == job_uid_short:
                return i
        return None

    async def upsert_job(self, job: JobRecord) -> None:
        self._connect()
        short_uid = job.job_uid[:12]

        if job.status.value == "filtered_out":
            # Goes to Trash tab
            row_idx = self._find_row(self._trash_ws, short_uid)
            row_data = _job_to_trash_row(job)
            if row_idx:
                self._trash_ws.update(f"A{row_idx}", [row_data])
            else:
                self._trash_ws.append_row(row_data, value_input_option="USER_ENTERED")
        else:
            # Goes to main Jobs tab
            row_idx = self._find_row(self._jobs_ws, short_uid)
            row_data = _job_to_jobs_row(job)
            if row_idx:
                self._jobs_ws.update(f"A{row_idx}", [row_data])
            else:
                self._jobs_ws.append_row(row_data, value_input_option="USER_ENTERED")

    async def batch_upsert_jobs(self, jobs: list[JobRecord]) -> None:
        """Batch append all new jobs in a single API call to avoid quota limits."""
        if not jobs:
            return
        self._connect()
        existing_uids = set(self._jobs_ws.col_values(1)[1:])
        trash_existing_uids = set(self._trash_ws.col_values(1)[1:])

        jobs_to_append: list[list] = []
        trash_to_append: list[list] = []

        for job in jobs:
            short_uid = job.job_uid[:12]
            if job.status.value == "filtered_out":
                if short_uid not in trash_existing_uids:
                    trash_to_append.append(_job_to_trash_row(job))
                    trash_existing_uids.add(short_uid)
            else:
                if short_uid not in existing_uids:
                    jobs_to_append.append(_job_to_jobs_row(job))
                    existing_uids.add(short_uid)

        if jobs_to_append:
            self._jobs_ws.append_rows(jobs_to_append, value_input_option="USER_ENTERED")
            log.info("Batch appended %d new jobs to Google Sheets", len(jobs_to_append))

        if trash_to_append:
            self._trash_ws.append_rows(trash_to_append, value_input_option="USER_ENTERED")
            log.info("Batch appended %d filtered jobs to trash tab", len(trash_to_append))

    async def update_status(self, job_uid: str, status: JobStatus, **extra) -> None:
        self._connect()
        short_uid = job_uid[:12]
        row_idx = self._find_row(self._jobs_ws, short_uid)
        if not row_idx:
            log.warning("update_status: job %s not found in sheet", short_uid)
            return

        # Status is column J (index 10, 1-based)
        status_col = HEADERS.index("Status") + 1
        self._jobs_ws.update_cell(row_idx, status_col, status.value)

        # Update Applied At if present
        if extra.get("applied_at"):
            applied_col = HEADERS.index("Applied At") + 1
            self._jobs_ws.update_cell(
                row_idx, applied_col, extra["applied_at"].strftime("%Y-%m-%d %H:%M")
            )
