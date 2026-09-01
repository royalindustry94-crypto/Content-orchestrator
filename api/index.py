"""Fail-closed Vercel adapter for the real Content Orchestrator API.

The Founder Studio browser shell must remain reachable even when preview-only
backend configuration is incomplete. Required database/auth values are still
required by the real API; this adapter never substitutes owner credentials,
weakens RLS, or fabricates secrets.
"""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "apps" / "api"

if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

try:
    from app.main import app as real_api
except Exception as exc:  # fail closed while keeping a diagnosable endpoint
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/api/health/live")
    @app.get("/health/live")
    async def degraded_liveness() -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={
                "status": "blocked",
                "reason": "preview_backend_configuration_incomplete",
            },
        )

    @app.get("/{path:path}")
    async def backend_blocked(path: str) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Founder Studio backend is not configured for this preview",
            },
        )
else:
    # File-based `api/index.py` is only `/api`. A rewrite may deliver either
    # `/api/health/live` or a stripped `/health/live`. Serve both shapes.
    from starlette.applications import Starlette
    from starlette.routing import Mount

    app = Starlette(
        routes=[
            Mount("/api", app=real_api),
            Mount("/", app=real_api),
        ]
    )
