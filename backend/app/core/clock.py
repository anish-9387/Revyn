"""Time utilities.

Journeys wait hours between steps in production. For demos the wait is divided by
``settings.clock_speedup`` so a six-hour follow-up becomes a few seconds.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.core.config import settings


def utcnow() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    """Normalise a naive datetime read back from SQLite to an aware UTC value."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def scaled(delay: timedelta) -> timedelta:
    speedup = max(settings.clock_speedup, 1.0)
    return timedelta(seconds=delay.total_seconds() / speedup)


def after(delay: timedelta, *, base: datetime | None = None) -> datetime:
    return (base or utcnow()) + scaled(delay)


def minutes(value: float) -> timedelta:
    return timedelta(minutes=value)


def hours(value: float) -> timedelta:
    return timedelta(hours=value)
