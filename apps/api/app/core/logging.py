"""Structured (JSON) logging configuration.

All services (api, worker) import `configure_logging` so log format is
consistent and machine-parseable in production. Never use bare `print()`
for anything that should be observable in prod.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any


class JsonFormatter(logging.Formatter):
    """Renders each log record as a single JSON line.

    Extra structured fields are passed via `logger.info(msg, extra={...})`
    and are merged into the output rather than dropped, which is the
    default `logging` behavior for anything not in the standard record.
    """

    RESERVED = {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "message",
        "taskName",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created))
            + f".{int(record.msecs):03d}Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        for key, value in record.__dict__.items():
            if key not in self.RESERVED and not key.startswith("_"):
                payload[key] = value

        return json.dumps(payload, default=str)


def configure_logging(service_name: str, level: str = "INFO") -> None:
    """Configure root logging for a service. Call once at process start."""
    root = logging.getLogger()
    root.setLevel(level)

    # Clear any pre-existing handlers (e.g. uvicorn defaults) so we don't
    # get duplicate or inconsistently-formatted log lines.
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)

    logging.getLogger(service_name).info(
        "logging configured", extra={"service": service_name, "level": level}
    )
