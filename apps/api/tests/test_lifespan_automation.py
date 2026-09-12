"""P0-3: scheduler/outbox start on lifespan; shutdown awaits cancelled tasks."""

from __future__ import annotations

import asyncio

import pytest

from app import main as main_mod
from app.main import automation_state


@pytest.mark.asyncio
async def test_lifespan_starts_and_stops_automation_loops():
    previous = main_mod.settings.environment
    previous_scheduler_interval = main_mod.settings.scheduler_interval_seconds
    previous_outbox_interval = main_mod.settings.outbox_relay_interval_seconds
    main_mod.settings.environment = "development"
    # Production defaults are intentionally slow (see db/session.py's pool
    # comment on serverless connection pressure) — use fast intervals here
    # so this test only asserts the loops start/tick/stop, not any
    # particular cadence.
    main_mod.settings.scheduler_interval_seconds = 0.2
    main_mod.settings.outbox_relay_interval_seconds = 0.2
    automation_state.tasks_running = []
    automation_state.scheduler_ticks = 0
    automation_state.outbox_ticks = 0
    try:
        async with main_mod.lifespan(main_mod.app):
            assert set(automation_state.tasks_running) == {
                "maintenance",
                "outbox_relay",
                "scheduler",
            }
            # Poll with timeout to avoid timing races under CPU contention.
            deadline = asyncio.get_running_loop().time() + 5.0
            while automation_state.scheduler_ticks < 1 or automation_state.outbox_ticks < 1:
                if asyncio.get_running_loop().time() >= deadline:
                    break
                await asyncio.sleep(0.1)
            assert automation_state.scheduler_ticks >= 1
            assert automation_state.outbox_ticks >= 1
        assert automation_state.tasks_running == []
    finally:
        main_mod.settings.environment = previous
        main_mod.settings.scheduler_interval_seconds = previous_scheduler_interval
        main_mod.settings.outbox_relay_interval_seconds = previous_outbox_interval
