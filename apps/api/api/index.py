"""Vercel Python serverless entrypoint.

Vercel's Python runtime auto-detects an ASGI/WSGI `app` object in any
file under `api/` and serves it directly -- this just re-exports the
real FastAPI app so nothing about `app.main` needs to know it's running
under Vercel.
"""

from app.main import app  # noqa: F401
