from __future__ import annotations

"""FastAPI Main Application and Control Plane Server."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from presentation.api.v1.endpoints.actions import router as actions_router
from presentation.api.v1.endpoints.jobs import router as jobs_router
from presentation.api.v1.endpoints.profile import router as profile_router
from presentation.api.v1.endpoints.reviews import router as reviews_router
from presentation.api.v1.endpoints.stats import router as stats_router

app = FastAPI(
    title="Auto-Job Control Plane",
    version="1.0.0",
    description="Autonomous AI/ML Job Application Engine",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API v1 Router Registration
app.include_router(stats_router, prefix="/api/v1")
app.include_router(jobs_router, prefix="/api/v1")
app.include_router(reviews_router, prefix="/api/v1")
app.include_router(profile_router, prefix="/api/v1")
app.include_router(actions_router, prefix="/api/v1")

# Mount Static Directories
screenshots_dir = Path("data/screenshots")
screenshots_dir.mkdir(parents=True, exist_ok=True)
app.mount("/data/screenshots", StaticFiles(directory=str(screenshots_dir)), name="data_screenshots")
app.mount("/screenshots", StaticFiles(directory=str(screenshots_dir)), name="screenshots")

web_dir = Path("src/presentation/web")
web_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "auto-job-control-plane"}


@app.get("/")
async def serve_dashboard():
    """Serve the single-page application dashboard."""
    index_file = web_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Auto-Job Control Plane API is online. Dashboard loading..."}
