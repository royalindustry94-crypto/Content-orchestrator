"""Single-origin preview server: built SPA plus the API under ``/api``.

Mirrors the routing in ``vercel.json`` — static files win, ``/api/*`` goes to
the API through the same prefix-stripping middleware the Vercel entrypoint
uses, and anything else falls back to ``index.html`` for the SPA router. That
makes a local or tunnelled preview exercise the deployed shape rather than an
approximation of it, which the Vite dev proxy would not.

Not a production server. Run it behind a tunnel for phone testing, or locally:

    PIPELINE_PROVIDER_MODE=simulation RUNTIME_PROFILE=serverless \
    python scripts/serve_preview.py --port 8080

Requires ``apps/web/dist`` to exist (``npm --prefix apps/web run build``).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = (ROOT / "apps" / "web" / "dist").resolve()
sys.path.insert(0, str(ROOT / "apps" / "api"))

from app.main import app as api_app  # noqa: E402  (path setup must precede import)
from app.serverless import PrefixStripMiddleware  # noqa: E402
from starlette.responses import FileResponse, PlainTextResponse  # noqa: E402
from starlette.staticfiles import StaticFiles  # noqa: E402

API_PREFIX = "/api"
_api = PrefixStripMiddleware(api_app, API_PREFIX)
_static = StaticFiles(directory=str(DIST))
_index = DIST / "index.html"


def _static_file_for(path: str) -> Path | None:
    """Resolve a request path to a file inside DIST, or None.

    Containment is checked after resolving so ``..`` segments cannot escape the
    build directory.
    """
    if path in ("", "/"):
        return None
    candidate = (DIST / path.lstrip("/")).resolve()
    if candidate.is_file() and DIST in candidate.parents:
        return candidate
    return None


async def app(scope, receive, send):  # noqa: ANN001, ANN201 — ASGI signature
    if scope["type"] == "lifespan":
        await api_app(scope, receive, send)
        return

    path = scope.get("path", "/")
    if path == API_PREFIX or path.startswith(API_PREFIX + "/"):
        await _api(scope, receive, send)
        return
    if _static_file_for(path) is not None:
        await _static(scope, receive, send)
        return
    if _index.is_file():
        await FileResponse(_index)(scope, receive, send)
        return
    await PlainTextResponse(
        "apps/web/dist is missing; run: npm --prefix apps/web run build",
        status_code=503,
    )(scope, receive, send)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    if not _index.is_file():
        raise SystemExit(f"{DIST} has no index.html; build the web app first")

    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
