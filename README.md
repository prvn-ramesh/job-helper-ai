# Auto-Job Engine

Automated job application system optimized for AI/ML Engineer roles.

## Architecture
- Clean 3-tier architecture (`core`, `domain`, `application`, `infrastructure`, `presentation`).
- 3 asynchronous workers:
  - **Worker 1 (Discover)**: Scrapes ATS direct APIs (Greenhouse/Lever/Ashby) & job boards (LinkedIn/Indeed/Glassdoor), deduplicates, records to SQLite and Google Sheets.
  - **Worker 2 (Triage)**: Scores, filters, marks approved/filtered.
  - **Worker 3 (Apply)**: Pre-fills forms, triggers review gate, submits on approval.

## Quickstart
```bash
# Sync dependencies
uv sync

# Initialize SQLite database
uv run python scripts/init_db.py

# Run discovery workflow
PYTHONPATH=src uv run python -c "from container.container import container; import asyncio; asyncio.run(container.discover_workflow.execute(container.profile))"

# Run tests
uv run pytest
```
