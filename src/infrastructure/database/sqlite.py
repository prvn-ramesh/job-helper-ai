from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from core.config import settings


def _get_connection() -> sqlite3.Connection:
    db_path = settings.db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db():
    """Sync context manager — yields a sqlite3.Connection with WAL mode."""
    conn = _get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create tables from schema.sql if they don't exist and ensure columns."""
    schema_path = Path("scripts/schema.sql")
    with get_db() as conn:
        conn.executescript(schema_path.read_text())
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(jobs)").fetchall()}
        for col_name, col_def in [
            ("city", "TEXT NOT NULL DEFAULT ''"),
            ("country", "TEXT NOT NULL DEFAULT ''"),
            ("min_experience_years", "INTEGER"),
            ("max_experience_years", "INTEGER"),
        ]:
            if col_name not in cols:
                conn.execute(f"ALTER TABLE jobs ADD COLUMN {col_name} {col_def}")
    print(f"✅ DB initialized at {settings.db_path}")


if __name__ == "__main__":
    init_db()
