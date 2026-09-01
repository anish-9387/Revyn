"""Revenue Risk Radar: turns a queue of failures into a ranked list of money at risk."""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.core.clock import as_utc, utcnow
from app.core.constants import EventKind, RootCause
from app.core.money import paise_to_rupees
from app.data.catalog import cause_profile
from app.models.customer import Customer
from app.models.event import RevenueEvent

# Amount that saturates the revenue component of the risk score.
AMOUNT_REFERENCE_RUPEES = 50_000.0
# Expected recovery that saturates the priority score.
PRIORITY_REFERENCE_PAISE = 15_000_00


@dataclass(slots=True)
class RiskAssessment:
    risk_score: float
    urgency: float
    severity: float
    amount_component: float
    value_component: float
    priority_score: float
    age_minutes: float

    def as_dict(self) -> dict[str, float]:
        return {
            "risk_score": round(self.risk_score, 1),
            "urgency": round(self.urgency, 3),
            "severity": round(self.severity, 3),
            "priority_score": round(self.priority_score, 1),
            "age_minutes": round(self.age_minutes, 1),
        }


def urgency(event: RevenueEvent, *, now=None) -> float:
    """How much the recovery window is closing, on 0..1."""
    now = now or utcnow()
    age_hours = max((now - as_utc(event.occurred_at)).total_seconds() / 3600.0, 0.0)
    kind = EventKind(event.kind)
    if kind is EventKind.CART_ABANDONMENT:
        return _clamp(1.0 - age_hours / 12.0, 0.10, 1.0)
    if kind is EventKind.OVERDUE_INVOICE:
        days_overdue = 0.0
        if event.due_date is not None:
            days_overdue = max((now - as_utc(event.due_date)).total_seconds() / 86_400.0, 0.0)
        return _clamp(0.25 + days_overdue / 60.0, 0.25, 1.0)
    return _clamp(1.0 - age_hours / 24.0, 0.15, 1.0)


def severity(event: RevenueEvent) -> float:
    """How structurally hard the failure is, on 0..1. Hard declines score highest."""
    profile = cause_profile(RootCause(event.root_cause))
    score = 0.35
    if not profile.transient:
        score += 0.28
    if not profile.retryable:
        score += 0.22
    score += 0.08 * min(event.retry_count, 3)
    return _clamp(score, 0.0, 1.0)


def assess(event: RevenueEvent, customer: Customer, *, now=None) -> RiskAssessment:
    now = now or utcnow()
    amount_component = _clamp(
        math.log1p(paise_to_rupees(event.amount_paise)) / math.log1p(AMOUNT_REFERENCE_RUPEES),
        0.0,
        1.2,
    )
    value_component = _clamp((customer.value_weight - 0.8) / 0.8, 0.0, 1.0)
    event_urgency = urgency(event, now=now)
    event_severity = severity(event)
    risk = 100.0 * (
        0.42 * amount_component
        + 0.20 * value_component
        + 0.20 * event_urgency
        + 0.18 * event_severity
    )
    return RiskAssessment(
        risk_score=_clamp(risk, 0.0, 100.0),
        urgency=event_urgency,
        severity=event_severity,
        amount_component=amount_component,
        value_component=value_component,
        priority_score=0.0,
        age_minutes=(now - as_utc(event.occurred_at)).total_seconds() / 60.0,
    )


def priority(expected_recovery_paise: int, assessment: RiskAssessment, customer: Customer) -> float:
    """Rank by money the merchant can expect to see, weighted by urgency and value.

    The transform saturates so a single very large opportunity cannot monopolise the
    queue ahead of several strong ones.
    """
    weighted = expected_recovery_paise * assessment.urgency * customer.value_weight
    return 100.0 * (1.0 - math.exp(-weighted / PRIORITY_REFERENCE_PAISE))


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
