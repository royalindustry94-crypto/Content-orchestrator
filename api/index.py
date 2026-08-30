"""Vercel Function entrypoint for the Content Orchestrator API.

Vercel's file-based Python routing serves this module at ``/api``, and
``vercel.json`` rewrites ``/api/*`` here, so one deployment serves the SPA and
the API from a single origin.

Nothing here relaxes a control. The application object is the audited
``app.main:app`` unchanged; this module only resolves the import path, pins the
runtime profile, and strips the routing prefix. The prefix logic itself lives in
``app.serverless`` so the API test suite covers it.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_API_ROOT = Path(__file__).resolve().parents[1] / "apps" / "api"
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

# Assigned, not defaulted: this module only ever executes inside a Vercel
# Function, where "server" would be false however the dashboard is configured.
# Letting an env var win here would let a deployment advertise background loops
# that physically cannot tick between frozen invocations.
os.environ["RUNTIME_PROFILE"] = "serverless"

from app.main import app as _fastapi_app  # noqa: E402  (path setup must precede import)
from app.serverless import PrefixStripMiddleware  # noqa: E402

app = PrefixStripMiddleware(_fastapi_app, "/api")
