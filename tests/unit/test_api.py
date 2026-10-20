from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from presentation.api.main import app


@pytest.mark.asyncio
async def test_api_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_api_stats():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_jobs" in data
        assert "discovered" in data
        assert "approved" in data
        assert "filtered_out" in data
        assert data["daily_limit"] >= 1


@pytest.mark.asyncio
async def test_api_jobs_pagination_and_filter():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # All jobs
        response = await ac.get("/api/v1/jobs?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "jobs" in data
        assert len(data["jobs"]) <= 10

        # Filter approved
        app_resp = await ac.get("/api/v1/jobs?status=approved")
        assert app_resp.status_code == 200
        app_data = app_resp.json()
        for j in app_data["jobs"]:
            assert j["status"] == "approved"


@pytest.mark.asyncio
async def test_api_reviews_pending():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/reviews/pending")
        assert response.status_code == 200
        items = response.json()
        assert isinstance(items, list)


@pytest.mark.asyncio
async def test_api_profile_get_and_update():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Fetch current profile
        get_res = await ac.get("/api/v1/profile")
        assert get_res.status_code == 200
        prof = get_res.json()
        assert prof["name"] == "Praveen Ramesh"
        assert prof["current_ctc_inr"] == 400000
        assert prof["expected_ctc_inr"] == 800000

        # 2. Update CTC and experience
        put_res = await ac.put(
            "/api/v1/profile",
            json={
                "current_ctc_inr": 400000,
                "expected_ctc_inr": 800000,
                "years_of_experience": 2,
                "requires_visa_sponsorship": False,
                "resume_strategy": "uploaded_pdf",
            },
        )
        assert put_res.status_code == 200
        updated = put_res.json()["profile"]
        assert updated["current_ctc_inr"] == 400000
        assert updated["expected_ctc_inr"] == 800000
