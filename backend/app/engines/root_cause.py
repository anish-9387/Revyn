"""AI Root-Cause Investigator.

Failure codes are a starting point, not a diagnosis. Candidate causes begin at their
prior weight and are re-weighted by evidence from the transaction, the customer history
and the current systemic picture. The posterior is normalised, so confidence reflects how
much the evidence separates the leading cause from its rivals.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.clock import as_utc, utcnow
from app.core.constants import CauseLayer, EventKind, FailureCode, RootCause
from app.core.money import paise_to_rupees
from app.data.catalog import FAILURE_CAUSE_PRIORS, FAILURE_LABELS, cause_profile
from app.models.customer import Customer
from app.models.event import RevenueEvent

# Evidence weaker than this is not worth showing to a merchant.
MIN_CANDIDATE_WEIGHT = 0.02


@dataclass(slots=True)
class CauseCandidate:
    cause: RootCause
    label: str
    probability: float


@dataclass(slots=True)
class Diagnosis:
    cause: RootCause
    layer: CauseLayer
    label: str
    confidence: float
    narrative: str
    transient: bool
    retryable: bool
    evidence: list[str] = field(default_factory=list)
    candidates: list[CauseCandidate] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "cause": str(self.cause),
            "layer": str(self.layer),
            "label": self.label,
            "confidence": round(self.confidence, 3),
            "narrative": self.narrative,
            "transient": self.transient,
            "retryable": self.retryable,
            "evidence": self.evidence,
            "candidates": [
                {"cause": str(c.cause), "label": c.label, "probability": round(c.probability, 3)}
                for c in self.candidates
            ],
        }


@dataclass(slots=True)
class SystemicSignal:
    """What the degradation detector currently believes about this route and method."""

    route_degraded: bool = False
    route_ratio: float = 1.0
    route_failure_share: float = 0.0
    method_degraded: bool = False
    method_ratio: float = 1.0
    route_name: str = ""


def investigate(
    event: RevenueEvent,
    customer: Customer,
    signal: SystemicSignal | None = None,
    *,
    now=None,
) -> Diagnosis:
    now = now or utcnow()
    signal = signal or SystemicSignal()
    code = FailureCode(event.failure_code) if event.failure_code else None
    weights: dict[RootCause, float] = {}
    for cause, prior in FAILURE_CAUSE_PRIORS.get(code, ()) if code else ():
        weights[cause] = prior
    if not weights:
        weights[RootCause.UNKNOWN] = 1.0

    evidence: list[str] = []
    if code is not None:
        evidence.append(f"Gateway reported {FAILURE_LABELS.get(code, str(code))}")

    _apply_systemic(weights, evidence, signal)
    _apply_transaction(weights, evidence, event, customer)
    _apply_customer(weights, evidence, event, customer)
    _apply_receivable(weights, evidence, event, now)

    total = sum(weights.values()) or 1.0
    ranked = sorted(
        ((cause, weight / total) for cause, weight in weights.items()),
        key=lambda pair: pair[1],
        reverse=True,
    )
    top_cause, confidence = ranked[0]
    profile = cause_profile(top_cause)
    return Diagnosis(
        cause=top_cause,
        layer=profile.layer,
        label=profile.label,
        confidence=confidence,
        narrative=profile.narrative,
        transient=profile.transient,
        retryable=profile.retryable,
        evidence=evidence,
        candidates=[
            CauseCandidate(cause=cause, label=cause_profile(cause).label, probability=prob)
            for cause, prob in ranked
            if prob >= MIN_CANDIDATE_WEIGHT
        ][:4],
    )


def _boost(weights: dict[RootCause, float], cause: RootCause, factor: float) -> None:
    weights[cause] = weights.get(cause, 0.05) * factor


def _apply_systemic(
    weights: dict[RootCause, float], evidence: list[str], signal: SystemicSignal
) -> None:
    if signal.route_degraded:
        _boost(weights, RootCause.ROUTE_DEGRADATION, 1.0 + 2.6 * min(signal.route_ratio / 2.0, 2.0))
        for cause in (RootCause.TRANSIENT_BANK_DECLINE, RootCause.HARD_BANK_DECLINE):
            if cause in weights:
                weights[cause] *= 0.55
        evidence.append(
            f"Failure rate on {signal.route_name or 'this route'} is running "
            f"{signal.route_ratio:.1f}x its 7-day baseline"
        )
        if signal.route_failure_share > 0.4:
            evidence.append(
                f"{signal.route_failure_share:.0%} of current failures share this single route"
            )
    if signal.method_degraded:
        _boost(
            weights, RootCause.METHOD_DEGRADATION, 1.0 + 2.0 * min(signal.method_ratio / 2.0, 2.0)
        )
        evidence.append(f"Method-level failure rate is {signal.method_ratio:.1f}x baseline")


def _apply_transaction(
    weights: dict[RootCause, float], evidence: list[str], event: RevenueEvent, customer: Customer
) -> None:
    if event.retry_count >= 2:
        _boost(weights, RootCause.HARD_BANK_DECLINE, 2.1)
        if RootCause.TRANSIENT_BANK_DECLINE in weights:
            weights[RootCause.TRANSIENT_BANK_DECLINE] *= 0.45
        evidence.append(f"Already failed {event.retry_count + 1} times on the same instrument")

    duration = event.checkout_duration_seconds or 0
    if EventKind(event.kind) is EventKind.CART_ABANDONMENT:
        if duration > 600:
            _boost(weights, RootCause.CHECKOUT_LATENCY, 2.2)
            evidence.append(f"Checkout stayed open {duration // 60} minutes before drop-off")
        elif duration < 75 and (event.cart_items or 0) <= 1:
            _boost(weights, RootCause.DELIBERATE_ABANDONMENT, 1.9)
            evidence.append("Single-item cart abandoned within a minute of checkout")
        ratio = event.amount_paise / max(customer.average_order_value_paise, 1)
        if ratio > 2.0:
            _boost(weights, RootCause.PRICE_SENSITIVITY, 1.7 + min(ratio, 6.0) * 0.12)
            evidence.append(f"Cart is {ratio:.1f}x this customer average order value")

    if event.failure_code == FailureCode.GATEWAY_TIMEOUT:
        evidence.append("Payment state was never confirmed by the gateway")


def _apply_customer(
    weights: dict[RootCause, float], evidence: list[str], event: RevenueEvent, customer: Customer
) -> None:
    if customer.previous_success_rate >= 0.9 and customer.previous_payment_count >= 4:
        for cause in (RootCause.DELIBERATE_ABANDONMENT, RootCause.DISPUTED_INVOICE):
            if cause in weights:
                weights[cause] *= 0.55
        for cause in (RootCause.TRANSIENT_BANK_DECLINE, RootCause.AUTH_FRICTION):
            if cause in weights:
                weights[cause] *= 1.35
        evidence.append(
            f"Customer has paid {customer.previous_payment_count} times with a "
            f"{customer.previous_success_rate:.0%} success rate"
        )
    elif customer.previous_payment_count <= 1:
        _boost(weights, RootCause.WRONG_INSTRUMENT_DETAILS, 1.4)
        evidence.append("First-time payer, so instrument details are unverified")

    if customer.historical_recovery_rate >= 0.45:
        evidence.append(
            f"Historically recovers {customer.historical_recovery_rate:.0%} of failures"
        )


def _apply_receivable(
    weights: dict[RootCause, float], evidence: list[str], event: RevenueEvent, now
) -> None:
    if EventKind(event.kind) is not EventKind.OVERDUE_INVOICE or event.due_date is None:
        return
    days = max((now - as_utc(event.due_date)).total_seconds() / 86_400.0, 0.0)
    evidence.append(f"Invoice is {days:.0f} days past due")
    if days > 30:
        _boost(weights, RootCause.DISPUTED_INVOICE, 2.0)
    elif days > 12:
        _boost(weights, RootCause.APPROVAL_BOTTLENECK, 1.5)
    else:
        _boost(weights, RootCause.BUYER_CASHFLOW, 1.4)
    if event.failure_code == FailureCode.PROMISE_BROKEN:
        _boost(weights, RootCause.BUYER_CASHFLOW, 1.6)
        evidence.append("A previous promise to pay was not honoured")
    if paise_to_rupees(event.amount_paise) > 50_000:
        evidence.append("Invoice value is large enough to sit in an approval chain")
