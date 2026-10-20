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
        self._jobs_uid_cache: dict[str, int] | None = None
        self._trash_uid_cache: dict[str, int] | None = None

    def _connect(self) -> None:
        if self._client is not None:
            return
        creds = _get_credentials()
        self._client = gspread.authorize(creds)
        spreadsheet = self._client.open_by_key(settings.google_sheets_id)
        self._jobs_ws, self._trash_ws = _ensure_sheet_structure(spreadsheet)
        log.info("✅ Connected to Google Sheets: %s", spreadsheet.title)

    def _find_row(self, ws: gspread.Worksheet, job_uid_short: str) -> int | None:
        """Return 1-based row index if job_uid found in column A, using cached row map."""
        if ws == self._jobs_ws:
            if self._jobs_uid_cache is None:
                self._jobs_uid_cache = {
                    val: i for i, val in enumerate(ws.col_values(1)[1:], start=2) if val
                }
            return self._jobs_uid_cache.get(job_uid_short)
        if ws == self._trash_ws:
            if self._trash_uid_cache is None:
                self._trash_uid_cache = {
                    val: i for i, val in enumerate(ws.col_values(1)[1:], start=2) if val
                }
            return self._trash_uid_cache.get(job_uid_short)
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
                if self._trash_uid_cache is not None:
                    self._trash_uid_cache[short_uid] = len(self._trash_uid_cache) + 2
        else:
            # Goes to main Jobs tab
            row_idx = self._find_row(self._jobs_ws, short_uid)
            row_data = _job_to_jobs_row(job)
            if row_idx:
                self._jobs_ws.update(f"A{row_idx}", [row_data])
            else:
                self._jobs_ws.append_row(row_data, value_input_option="USER_ENTERED")
                if self._jobs_uid_cache is not None:
                    self._jobs_uid_cache[short_uid] = len(self._jobs_uid_cache) + 2

    async def batch_upsert_jobs(self, jobs: list[JobRecord]) -> None:
        """Batch append all new jobs in a single API call to avoid quota limits."""
        if not jobs:
            return
        self._connect()
        self._jobs_uid_cache = None
        self._trash_uid_cache = None
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

    async def batch_sync_triage(
        self, approved_jobs: list[JobRecord], filtered_jobs: list[JobRecord]
    ) -> None:
        """Batch sync triaged jobs to the respective sheets with minimal API calls."""
        self._connect()
        # 1. Append filtered jobs to trash tab
        trash_existing = set(self._trash_ws.col_values(1)[1:])
        trash_rows = [
            _job_to_trash_row(j) for j in filtered_jobs if j.job_uid[:12] not in trash_existing
        ]
        if trash_rows:
            self._trash_ws.append_rows(trash_rows, value_input_option="USER_ENTERED")
            log.info("Batch appended %d jobs to Filtered tab", len(trash_rows))

        # 2. Batch update Status, Score, and Filtered Reason in main Jobs sheet
        uid_map = {val: i for i, val in enumerate(self._jobs_ws.col_values(1)[1:], start=2) if val}
        status_col = HEADERS.index("Status") + 1
        score_col = HEADERS.index("Score") + 1
        reason_col = HEADERS.index("Filtered Reason") + 1

        cells_to_update = []
        import gspread.cell

        for j in approved_jobs:
            row_idx = uid_map.get(j.job_uid[:12])
            if row_idx:
                cells_to_update.append(gspread.cell.Cell(row_idx, status_col, "approved"))
                if j.score is not None:
                    cells_to_update.append(gspread.cell.Cell(row_idx, score_col, str(j.score)))

        for j in filtered_jobs:
            row_idx = uid_map.get(j.job_uid[:12])
            if row_idx:
                cells_to_update.append(gspread.cell.Cell(row_idx, status_col, "filtered_out"))
                if j.score is not None:
                    cells_to_update.append(gspread.cell.Cell(row_idx, score_col, str(j.score)))
                if j.filter_reason:
                    cells_to_update.append(gspread.cell.Cell(row_idx, reason_col, j.filter_reason))

        if cells_to_update:
            self._jobs_ws.update_cells(cells_to_update)
            log.info("Batch updated %d cells in Jobs tab", len(cells_to_update))

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
