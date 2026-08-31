"""Frontend-only Vercel entrypoint for the isolated Founder Studio preview.

Keep the browser shell independent from backend configuration so a missing
preview secret cannot crash the entire mobile page. The real API lives in
api/index.py and remains fail-closed when its required runtime configuration
is unavailable.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent
WEB_DIST = ROOT / "apps" / "web" / "dist"

app = FastAPI(
    title="Content Orchestrator Founder Studio Preview",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

if WEB_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(WEB_DIST), html=True), name="founder-studio")
else:
    @app.get("/")
    async def missing_frontend_build() -> None:
        raise HTTPException(
            status_code=503,
            detail="Founder Studio frontend build is missing",
        )
