import pytest

from core.config import settings
from infrastructure.database.sqlite import init_db


@pytest.fixture(autouse=True)
def test_db_isolation(tmp_path, monkeypatch):
    """Isolate tests to a temporary SQLite database so data/jobs.db is never polluted."""
    test_db = tmp_path / "test_jobs.db"
    monkeypatch.setattr(settings, "sqlite_db_path", str(test_db))
    init_db()
    yield test_db
