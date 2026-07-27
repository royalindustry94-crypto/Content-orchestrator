"""Assignment priority helpers (WS4).

Effective priority = base priority + age boost, computed at selection time
from the server clock so it cannot go stale and needs no background job.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Integer, cast, func
from sqlalchemy.sql import ColumnElement

from app.core.config import get_settings


def compute_age_boost(
    created_at: datetime,
    *,
    now: datetime | None = None,
    interval_seconds: int | None = None,
    per_interval: int | None = None,
    boost_max: int | None = None,
) -> int:
    settings = get_settings()
    now = now or datetime.now(UTC)
    interval = (
        interval_seconds
        if interval_seconds is not None
        else settings.assignment_age_boost_interval_seconds
    )
    step = (
        per_interval if per_interval is not None else settings.assignment_age_boost_per_interval
    )
    cap = boost_max if boost_max is not None else settings.assignment_age_boost_max
    age = max(0.0, (now - created_at).total_seconds())
    if interval <= 0:
        return 0
    boost = int(age // interval) * step
    return min(boost, cap)


def compute_effective_priority(
    priority: int,
    created_at: datetime,
    *,
    now: datetime | None = None,
) -> int:
    return priority + compute_age_boost(created_at, now=now)


def base_priority_for_tier(priority_tier: int) -> int:
    settings = get_settings()
    return int(priority_tier) * settings.workspace_tier_priority_weight


def effective_priority_expr(
    priority_col: ColumnElement,
    created_at_col: ColumnElement,
    *,
    now: datetime | None = None,
) -> ColumnElement:
    """SQLAlchemy expression for ORDER BY effective priority DESC.

    ``now`` is injectable for clock-controlled tests; production callers
    omit it and the expression uses the bound wall-clock value from the
    claim transaction.
    """
    settings = get_settings()
    now = now or datetime.now(UTC)
    interval = settings.assignment_age_boost_interval_seconds
    step = settings.assignment_age_boost_per_interval
    cap = settings.assignment_age_boost_max
    age = func.greatest(
        0.0,
        func.extract("epoch", cast(now, created_at_col.type) - created_at_col),
    )
    if interval <= 0:
        return priority_col
    boost = func.least(
        cast(cap, Integer),
        cast(func.floor(age / float(interval)) * step, Integer),
    )
    return priority_col + boost
