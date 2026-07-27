"""Structured audit logging with request correlation.

`RequestIDMiddleware` assigns a UUID request id to every request, echoes
it back as `X-Request-ID`, and emits one structured line per request with
method/path/status/duration. Endpoint handlers additionally call
`audit(...)` for domain events (worker registered, credential rotated,
...), which reuses the same request id so a request's log lines correlate.

Redaction: the Authorization header, secrets, and secret hashes are never
passed to this module — callers log identifiers (worker_id,
credential_id) only. There is deliberately no generic "log the request
body" hook, so a secret can't leak by accident.
"""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

audit_logger = logging.getLogger("audit")

_SENSITIVE_KEYS = frozenset({"secret", "worker_secret", "secret_hash", "token", "authorization"})


def audit(request: Request | None, event: str, **fields: object) -> None:
    """Emit a structured audit event, correlated to the current request.
    Refuses sensitive keys outright instead of redacting them — passing a
    secret to the audit log is a programming error that should fail tests.
    """
    leaked = _SENSITIVE_KEYS.intersection(k.lower() for k in fields)
    if leaked:
        raise ValueError(f"refusing to audit-log sensitive fields: {sorted(leaked)}")
    request_id = getattr(request.state, "request_id", None) if request is not None else None
    audit_logger.info(
        event,
        extra={"audit_event": event, "request_id": request_id, **fields},
    )


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.monotonic()
        response = await call_next(request)
        duration_ms = round((time.monotonic() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        audit_logger.info(
            "http_request",
            extra={
                "audit_event": "http_request",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response
