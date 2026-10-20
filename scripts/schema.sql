-- Auto-job SQLite schema (WAL mode for concurrent readers)
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS jobs (
    job_uid             TEXT PRIMARY KEY,
    title               TEXT NOT NULL,
    company             TEXT NOT NULL,
    location            TEXT NOT NULL DEFAULT '',
    platform            TEXT NOT NULL,
    apply_url           TEXT NOT NULL,
    job_id_external     TEXT NOT NULL DEFAULT '',

    description         TEXT NOT NULL DEFAULT '',
    content_hash        TEXT NOT NULL DEFAULT '',

    work_mode           TEXT NOT NULL DEFAULT 'unknown',
    city                TEXT NOT NULL DEFAULT '',
    country             TEXT NOT NULL DEFAULT '',
    min_experience_years INTEGER,
    max_experience_years INTEGER,
    salary_min          INTEGER,
    salary_max          INTEGER,
    salary_currency     TEXT NOT NULL DEFAULT 'INR',

    status              TEXT NOT NULL DEFAULT 'discovered',
    score               REAL,
    filter_reason       TEXT,
    eligibility         TEXT NOT NULL DEFAULT 'unknown',

    discovered_at       TEXT NOT NULL,
    applied_at          TEXT,

    resume_used         TEXT,
    cover_note          TEXT,
    notes               TEXT NOT NULL DEFAULT '',
    screenshot_path     TEXT,
    filled_fields       TEXT  -- JSON blob
);

-- Fast lookups by status (Worker 2 and 3 poll this)
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_discovered_at ON jobs(discovered_at);
CREATE INDEX IF NOT EXISTS idx_jobs_platform ON jobs(platform);
