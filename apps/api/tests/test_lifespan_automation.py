"""P0-3: scheduler/outbox start on lifespan; shutdown awaits cancelled tasks."""

from __future__ import annotations

import asyncio

import pytest

from app import main as main_mod
from app.main import automation_state


@pytest.mark.asyncio
async def test_lifespan_starts_and_stops_automation_loops():
    previous = main_mod.settings.environment
    main_mod.settings.environment = "development"
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
            # Intervals default to 2s for scheduler/outbox.
            await asyncio.sleep(2.3)
            assert automation_state.scheduler_ticks >= 1
            assert automation_state.outbox_ticks >= 1
        assert automation_state.tasks_running == []
    finally:
        main_mod.settings.environment = previous
