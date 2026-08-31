"""Vercel entrypoint for the isolated Founder Studio preview."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent
API_ROOT = ROOT / "apps" / "api"
WEB_DIST = ROOT / "apps" / "web" / "dist"

if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.main import app as api_app  # noqa: E402

app = FastAPI(
    title="Content Orchestrator Founder Studio Preview",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# The existing React client calls relative /api/* URLs. Mount the real API at
# that prefix so frontend and backend stay on one preview origin.
app.mount("/api", api_app)

if WEB_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(WEB_DIST), html=True), name="founder-studio")
else:
    @app.get("/")
    async def missing_frontend_build() -> None:
        raise HTTPException(status_code=503, detail="Founder Studio frontend build is missing")
