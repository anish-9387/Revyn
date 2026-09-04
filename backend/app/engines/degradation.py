"""Payment Degradation Detector.

Compares the recent failure rate on each route and method against a seven-day baseline.
When a route degrades, the decision engine stops preferring retries: hammering a broken
route adds load and customer friction without adding revenue.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import as_utc, utcnow
from app.core.constants import DegradationSeverity
from app.engines.root_cause import SystemicSignal
from app.models.insight import DegradationWindow, RouteHealthBucket

RECENT_WINDOW_MINUTES = 45
BASELINE_DAYS = 7
MIN_RECENT_ATTEMPTS = 60

SEVERITY_THRESHOLDS: tuple[tuple[float, DegradationSeverity], ...] = (
    (2.6, DegradationSeverity.CRITICAL),
    (1.9, DegradationSeverity.ELEVATED),
    (1.45, DegradationSeverity.WATCH),
)


@dataclass(slots=True)
class ScopeHealth:
    scope_type: str
    scope_value: str
    attempts: int
    failures: int
    observed_rate: float
    baseline_rate: float
    ratio: float
    severity: DegradationSeverity

    @property
    def degraded(self) -> bool:
        return self.severity in (DegradationSeverity.ELEVATED, DegradationSeverity.CRITICAL)

    @property
    def scored(self) -> bool:
        """Below the attempt floor a rate is noise, so severity is withheld rather than raised."""
        return self.attempts >= MIN_RECENT_ATTEMPTS

    def as_dict(self) -> dict:
        return {
            "scope_type": self.scope_type,
            "scope_value": self.scope_value,
            "attempts": self.attempts,
            "failures": self.failures,
            "observed_rate": round(self.observed_rate, 4),
            "baseline_rate": round(self.baseline_rate, 4),
            "ratio": round(self.ratio, 2),
            "severity": str(self.severity),
            "degraded": self.degraded,
            "scored": self.scored,
        }


@dataclass(slots=True)
class DegradationState:
    routes: dict[str, ScopeHealth]
    methods: dict[str, ScopeHealth]

    def signal_for(self, route: str, method: str) -> SystemicSignal:
        route_health = self.routes.get(route)
        method_health = self.methods.get(method)
        total_recent_failures = sum(h.failures for h in self.routes.values()) or 1
        return SystemicSignal(
            route_degraded=bool(route_health and route_health.degraded),
            route_ratio=route_health.ratio if route_health else 1.0,
            route_failure_share=(route_health.failures / total_recent_failures)
            if route_health
            else 0.0,
            method_degraded=bool(method_health and method_health.degraded),
            method_ratio=method_health.ratio if method_health else 1.0,
            route_name=route,
        )

    @property
    def active(self) -> list[ScopeHealth]:
        return [h for h in (*self.routes.values(), *self.methods.values()) if h.degraded]


def _severity(ratio: float, observed_rate: float) -> DegradationSeverity:
    if observed_rate < 0.05:
        return DegradationSeverity.NONE
    for threshold, severity in SEVERITY_THRESHOLDS:
        if ratio >= threshold:
            return severity
    return DegradationSeverity.NONE


async def _aggregate(session: AsyncSession, column, now) -> dict[str, ScopeHealth]:
    recent_from = now - timedelta(minutes=RECENT_WINDOW_MINUTES)
    baseline_from = now - timedelta(days=BASELINE_DAYS)

    recent_stmt = (
        select(
            column,
            func.sum(RouteHealthBucket.attempts),
            func.sum(RouteHealthBucket.failures),
        )
        .where(RouteHealthBucket.bucket_start >= recent_from)
        .group_by(column)
    )
    baseline_stmt = (
        select(
            column,
            func.sum(RouteHealthBucket.attempts),
            func.sum(RouteHealthBucket.failures),
        )
        .where(
            RouteHealthBucket.bucket_start >= baseline_from,
            RouteHealthBucket.bucket_start < recent_from,
        )
        .group_by(column)
    )

    baseline = {
        str(scope): (failures or 0) / attempts if attempts else 0.0
        for scope, attempts, failures in (await session.execute(baseline_stmt)).all()
    }
    health: dict[str, ScopeHealth] = {}
    scope_type = "route" if column is RouteHealthBucket.route else "method"
    for scope, attempts, failures in (await session.execute(recent_stmt)).all():
        attempts = int(attempts or 0)
        failures = int(failures or 0)
        observed = failures / attempts if attempts else 0.0
        base = baseline.get(str(scope), 0.0) or observed or 1.0
        ratio = observed / base if base else 1.0
        severity = (
            _severity(ratio, observed)
            if attempts >= MIN_RECENT_ATTEMPTS
            else DegradationSeverity.NONE
        )
        health[str(scope)] = ScopeHealth(
            scope_type=scope_type,
            scope_value=str(scope),
            attempts=attempts,
            failures=failures,
            observed_rate=observed,
            baseline_rate=base,
            ratio=ratio,
            severity=severity,
        )
    return health


async def detect(session: AsyncSession, *, now=None) -> DegradationState:
    now = now or utcnow()
    routes = await _aggregate(session, RouteHealthBucket.route, now)
    methods = await _aggregate(session, RouteHealthBucket.method, now)
    return DegradationState(routes=routes, methods=methods)


async def reconcile_windows(
    session: AsyncSession, state: DegradationState, *, now=None
) -> list[str]:
    """Open a window for each newly degraded scope and close the ones that recovered."""
    now = now or utcnow()
    open_windows = {
        (w.scope_type, w.scope_value): w
        for w in (
            (
                await session.execute(
                    select(DegradationWindow).where(DegradationWindow.status == "active")
                )
            )
            .scalars()
            .all()
        )
    }
    changes: list[str] = []
    degraded_keys: set[tuple[str, str]] = set()

    for health in (*state.routes.values(), *state.methods.values()):
        key = (health.scope_type, health.scope_value)
        if not health.degraded:
            continue
        degraded_keys.add(key)
        window = open_windows.get(key)
        if window is None:
            session.add(
                DegradationWindow(
                    scope_type=health.scope_type,
                    scope_value=health.scope_value,
                    status="active",
                    severity=health.severity,
                    detected_at=now,
                    baseline_failure_rate=health.baseline_rate,
                    observed_failure_rate=health.observed_rate,
                    ratio=health.ratio,
                    affected_events=health.failures,
                    recommendation=_recommendation(health),
                    detail=health.as_dict(),
                )
            )
            changes.append(f"opened:{health.scope_type}:{health.scope_value}")
        else:
            window.severity = health.severity
            window.observed_failure_rate = health.observed_rate
            window.baseline_failure_rate = health.baseline_rate
            window.ratio = health.ratio
            window.affected_events = health.failures
            window.recommendation = _recommendation(health)
            window.detail = health.as_dict()

    for key, window in open_windows.items():
        if key not in degraded_keys:
            window.status = "resolved"
            window.resolved_at = now
            changes.append(f"resolved:{key[0]}:{key[1]}")

    await session.flush()
    return changes


def _recommendation(health: ScopeHealth) -> str:
    if health.severity is DegradationSeverity.CRITICAL:
        return (
            f"Suspend retries on {health.scope_value} and steer new attempts to a healthy "
            "route until the failure rate returns to baseline."
        )
    if health.severity is DegradationSeverity.ELEVATED:
        return (
            f"Throttle retries on {health.scope_value} and offer an alternative payment "
            "method on high-value attempts."
        )
    return f"Monitor {health.scope_value}; failure rate is drifting above baseline."


async def active_window_summary(session: AsyncSession) -> list[DegradationWindow]:
    stmt = (
        select(DegradationWindow)
        .where(DegradationWindow.status == "active")
        .order_by(DegradationWindow.ratio.desc())
    )
    return list((await session.execute(stmt)).scalars().all())


async def failure_rate_series(
    session: AsyncSession, value: str, *, scope: str = "route", hours: int = 6
) -> list[dict]:
    """Fifteen-minute failure-rate points for the incident chart, per route or per method.

    A method spans several routes, so buckets are summed per interval rather than read
    row by row: otherwise one interval would emit one partial point per route.
    """
    since = utcnow() - timedelta(hours=hours)
    column = RouteHealthBucket.method if scope == "method" else RouteHealthBucket.route
    stmt = (
        select(
            RouteHealthBucket.bucket_start,
            func.sum(RouteHealthBucket.attempts),
            func.sum(RouteHealthBucket.failures),
        )
        .where(column == value, RouteHealthBucket.bucket_start >= since)
        .group_by(RouteHealthBucket.bucket_start)
        .order_by(RouteHealthBucket.bucket_start)
    )
    points = []
    for bucket_start, attempts, failures in (await session.execute(stmt)).all():
        attempts, failures = int(attempts or 0), int(failures or 0)
        points.append(
            {
                "at": as_utc(bucket_start).isoformat(),
                "attempts": attempts,
                "failures": failures,
                "failure_rate": round(failures / attempts, 4) if attempts else 0.0,
            }
        )
    return points
