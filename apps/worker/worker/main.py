"""Worker service entrypoint.

Scope for this milestone: process bootstrap, structured logging, and a
graceful-shutdown-aware run loop only. The background agents (Idea
Scraper, Content Auditor, API Health Monitor) and pipeline-stage job
processing belong to a later milestone: they require the data model and
provider integrations, which do not exist yet, and writing them before
those foundations would mean job logic with nothing real to act on.
They land in the milestone that introduces
the data model and the first real provider integration.
"""

from __future__ import annotations

import asyncio
import logging
import signal

from worker.core.config import get_settings
from worker.core.logging import configure_logging

settings = get_settings()
configure_logging(service_name=settings.service_name, level=settings.log_level)
logger = logging.getLogger(__name__)


async def main() -> None:
    stop_event = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop_event.set)

    logger.info(
        "worker starting",
        extra={"service": settings.service_name, "environment": settings.environment},
    )

    await stop_event.wait()

    logger.info("worker shutting down", extra={"service": settings.service_name})


if __name__ == "__main__":
    asyncio.run(main())
