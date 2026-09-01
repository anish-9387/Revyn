"""Merchant recovery memory and systemic payment degradation windows."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import ActionType, DegradationSeverity
from app.core.db import Base
from app.models.base import TimestampMixin, id_pk, utc_column


class StrategyStat(Base, TimestampMixin):
    """Beta posterior per (loss class, root cause, segment, action).

    The learner updates it after every verified outcome, which is what turns a generic
    playbook into a merchant-specific one.
    """

    __tablename__ = "strategy_stats"
    __table_args__ = (Index("uq_strategy_context_action", "context_key", "action", unique=True),)

    id: Mapped[str] = id_pk()
    context_key: Mapped[str] = mapped_column(String(96), index=True)
    action: Mapped[ActionType] = mapped_column(String(24))
    trials: Mapped[int] = mapped_column(Integer, default=0)
    successes: Mapped[int] = mapped_column(Integer, default=0)
    # Beta prior, seeded from the catalog so a cold start is still sensible.
    alpha: Mapped[float] = mapped_column(Float, default=1.0)
    beta: Mapped[float] = mapped_column(Float, default=1.0)
    recovered_paise: Mapped[int] = mapped_column(Integer, default=0)
    cost_paise: Mapped[int] = mapped_column(Integer, default=0)

    @property
    def posterior_mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)


class DegradationWindow(Base, TimestampMixin):
    """A detected systemic failure spike on one payment route or method."""

    __tablename__ = "degradation_windows"
    __table_args__ = (Index("ix_degradation_scope_status", "scope_type", "scope_value", "status"),)

    id: Mapped[str] = id_pk()
    scope_type: Mapped[str] = mapped_column(String(20), index=True)
    scope_value: Mapped[str] = mapped_column(String(48), index=True)
    status: Mapped[str] = mapped_column(String(12), default="active", index=True)
    severity: Mapped[DegradationSeverity] = mapped_column(String(12))

    detected_at: Mapped[datetime] = utc_column(index=True)
    resolved_at: Mapped[datetime | None] = utc_column(nullable=True)
    baseline_failure_rate: Mapped[float] = mapped_column(Float, default=0.0)
    observed_failure_rate: Mapped[float] = mapped_column(Float, default=0.0)
    ratio: Mapped[float] = mapped_column(Float, default=1.0)
    affected_events: Mapped[int] = mapped_column(Integer, default=0)
    amount_at_risk_paise: Mapped[int] = mapped_column(Integer, default=0)
    recommendation: Mapped[str] = mapped_column(String(240), default="")
    detail: Mapped[dict[str, Any]] = mapped_column(default=dict)


class RouteHealthBucket(Base):
    """Fifteen-minute gateway attempt aggregates.

    Failure counts alone cannot distinguish a traffic spike from a real outage, so the
    degradation detector needs the attempt denominator these buckets carry.
    """

    __tablename__ = "route_health_buckets"
    __table_args__ = (
        Index("uq_route_bucket", "bucket_start", "route", unique=True),
        Index("ix_route_bucket_method", "method", "bucket_start"),
    )

    id: Mapped[str] = id_pk()
    bucket_start: Mapped[datetime] = utc_column(index=True)
    route: Mapped[str] = mapped_column(String(48), index=True)
    method: Mapped[str] = mapped_column(String(20), index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    failures: Mapped[int] = mapped_column(Integer, default=0)
    failed_amount_paise: Mapped[int] = mapped_column(Integer, default=0)

    @property
    def failure_rate(self) -> float:
        return self.failures / self.attempts if self.attempts else 0.0
