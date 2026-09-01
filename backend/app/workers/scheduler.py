"""Background recovery loop.

Runs detection and execution on a fixed interval inside the API process, which is enough for a
single-node deployment and keeps the demo dependency-free. The loop only touches the
orchestrator, so moving it to Celery or an external worker means swapping this file alone.
"""

from __future__ import annotations

import asyncio
import contextlib

from app.core.config import settings
from app.core.db import SessionFactory
from app.core.logging import get_logger
from app.services.orchestrator import orchestrator

log = get_logger(__name__)


class RecoveryScheduler:
    def __init__(self, interval_seconds: float | None = None) -> None:
        self.interval = interval_seconds or settings.scheduler_interval_seconds
        self._task: asyncio.Task | None = None
        self.cycles = 0
        self.last_error: str | None = None

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        if self.running:
            return
        self._task = asyncio.create_task(self._loop(), name="revyn-recovery-loop")
        log.info("scheduler.started", extra={"interval_seconds": self.interval})

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None
        log.info("scheduler.stopped", extra={"cycles": self.cycles})

    async def _loop(self) -> None:
        while True:
            try:
                await self.run_once()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # keep the loop alive across transient failures
                self.last_error = str(exc)
                log.exception("scheduler.cycle_failed", extra={"error": str(exc)})
            await asyncio.sleep(self.interval)

    async def run_once(self) -> dict:
        async with SessionFactory() as session:
            scan = await orchestrator.scan(session)
            tick = await orchestrator.tick(session)
            await session.commit()
        self.cycles += 1
        report = {"cycle": self.cycles, "scan": scan.as_dict(), "tick": tick.as_dict()}
        if scan.journeys_started or tick.executed or tick.recovered:
            log.info("scheduler.cycle", extra=report)
        return report

    def status(self) -> dict:
        return {
            "running": self.running,
            "interval_seconds": self.interval,
            "cycles": self.cycles,
            "last_error": self.last_error,
            "clock_speedup": settings.clock_speedup,
        }


scheduler = RecoveryScheduler()
