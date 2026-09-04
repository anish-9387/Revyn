"""Synthetic merchant dataset.

Produces a realistic Indian D2C/SaaS/B2B mix: resolved history for model fitting and a
set of live at-risk events for the orchestrator to work on. A route degradation episode
is injected into the recent window so the systemic detector has something to find.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.core.clock import utcnow
from app.core.constants import (
    ActionType,
    Cohort,
    CommunicationPreference,
    CustomerSegment,
    EventKind,
    EventStatus,
    FailureCode,
    MandateRail,
    MandateStatus,
    PaymentMethod,
    RootCause,
)
from app.core.money import rupees_to_paise
from app.data.catalog import ALLOWED_ACTIONS, FAILURE_CAUSE_PRIORS, FAILURE_LABELS, ISSUERS
from app.data.outcome import OutcomeInputs, recovery_probability
from app.engines.features import IST_OFFSET_HOURS
from app.models.customer import Customer
from app.models.event import RevenueEvent

HISTORY_DAYS = 60
LIVE_WINDOW_HOURS = 8
CONTROL_SHARE_HISTORY = 0.22
CONTROL_SHARE_LIVE = 0.15
DEGRADED_ROUTE = "route-upi-alpha"

SEGMENT_WEIGHTS: dict[CustomerSegment, float] = {
    CustomerSegment.VIP: 0.04,
    CustomerSegment.HIGH: 0.14,
    CustomerSegment.MEDIUM: 0.37,
    CustomerSegment.LOW: 0.31,
    CustomerSegment.NEW: 0.14,
}

# Order value band per segment, in rupees.
SEGMENT_AOV: dict[CustomerSegment, tuple[int, int]] = {
    CustomerSegment.VIP: (18_000, 90_000),
    CustomerSegment.HIGH: (7_000, 32_000),
    CustomerSegment.MEDIUM: (2_200, 11_000),
    CustomerSegment.LOW: (450, 3_200),
    CustomerSegment.NEW: (900, 6_500),
}

KIND_WEIGHTS: dict[EventKind, float] = {
    EventKind.PAYMENT_FAILURE: 0.44,
    EventKind.CART_ABANDONMENT: 0.27,
    EventKind.SUBSCRIPTION_FAILURE: 0.17,
    EventKind.OVERDUE_INVOICE: 0.12,
}

PAYMENT_FAILURE_CODES: dict[FailureCode, float] = {
    FailureCode.INSUFFICIENT_FUNDS: 0.18,
    FailureCode.ISSUER_DECLINED: 0.16,
    FailureCode.AUTHENTICATION_FAILED: 0.12,
    FailureCode.GATEWAY_TIMEOUT: 0.10,
    FailureCode.OTP_TIMEOUT: 0.07,
    FailureCode.CARD_EXPIRED: 0.06,
    FailureCode.INVALID_VPA: 0.05,
    FailureCode.PSP_UNAVAILABLE: 0.04,
    FailureCode.ISSUER_UNAVAILABLE: 0.03,
    FailureCode.LIMIT_EXCEEDED: 0.02,
    FailureCode.PAYMENT_CANCELLED: 0.02,
    FailureCode.CONFIGURATION_ERROR: 0.01,
    FailureCode.MANDATE_NOT_FOUND: 0.04,
    FailureCode.MANDATE_REVOKED: 0.04,
    FailureCode.MANDATE_AMOUNT_EXCEEDS: 0.03,
    FailureCode.PDN_NOT_DELIVERED: 0.03,
    FailureCode.AFA_REQUIRED: 0.02,
}

CART_FAILURE_CODES: dict[FailureCode, float] = {
    FailureCode.CHECKOUT_TIMEOUT: 0.55,
    FailureCode.PRICE_HESITATION: 0.30,
    FailureCode.CHECKOUT_ERROR: 0.09,
    FailureCode.METHOD_UNAVAILABLE: 0.06,
}

INVOICE_FAILURE_CODES: dict[FailureCode, float] = {
    FailureCode.INVOICE_UNPAID: 0.82,
    FailureCode.PROMISE_BROKEN: 0.18,
}

# The legacy workflow the merchant ran before Revyn: one fixed action per loss class.
LEGACY_POLICY: dict[EventKind, ActionType] = {
    EventKind.PAYMENT_FAILURE: ActionType.RETRY_PAYMENT,
    EventKind.CART_ABANDONMENT: ActionType.EMAIL,
    EventKind.SUBSCRIPTION_FAILURE: ActionType.RETRY_PAYMENT,
    EventKind.OVERDUE_INVOICE: ActionType.EMAIL,
}


FIRST_NAMES = [
    "Aarav",
    "Ananya",
    "Vihaan",
    "Diya",
    "Ishaan",
    "Meera",
    "Kabir",
    "Aditi",
    "Rohan",
    "Saanvi",
    "Arjun",
    "Priya",
    "Dev",
    "Kavya",
    "Nikhil",
    "Riya",
    "Aryan",
    "Neha",
    "Karan",
    "Isha",
    "Manav",
    "Tara",
    "Yash",
    "Sneha",
    "Rahul",
    "Pooja",
    "Siddharth",
    "Anjali",
]
LAST_NAMES = [
    "Sharma",
    "Iyer",
    "Patel",
    "Reddy",
    "Nair",
    "Gupta",
    "Mehta",
    "Rao",
    "Bose",
    "Kulkarni",
    "Desai",
    "Chatterjee",
    "Menon",
    "Joshi",
    "Kapoor",
    "Malhotra",
    "Verma",
    "Pillai",
    "Shetty",
    "Banerjee",
]


@dataclass(slots=True)
class GeneratedDataset:
    customers: list[Customer] = field(default_factory=list)
    events: list[RevenueEvent] = field(default_factory=list)
    mandates: list = field(default_factory=list)

    @property
    def live_events(self) -> list[RevenueEvent]:
        return [e for e in self.events if not e.is_training]


def _weighted(rng: random.Random, weights: dict) -> object:
    keys = list(weights)
    return rng.choices(keys, weights=[weights[k] for k in keys], k=1)[0]


def _local_hour(moment: datetime) -> float:
    return (moment.hour + moment.minute / 60.0 + IST_OFFSET_HOURS) % 24.0


def _build_customers(rng: random.Random, count: int) -> list[Customer]:
    customers: list[Customer] = []
    for index in range(count):
        segment = _weighted(rng, SEGMENT_WEIGHTS)
        low, high = SEGMENT_AOV[segment]
        aov = rng.randint(low, high)
        payments = max(1, int(rng.gammavariate(2.2, 6.0)))
        if segment is CustomerSegment.NEW:
            payments = rng.randint(1, 3)
        success_rate = min(0.99, max(0.30, rng.betavariate(7.5, 2.2)))
        if segment in (CustomerSegment.VIP, CustomerSegment.HIGH):
            success_rate = min(0.99, success_rate + 0.06)
        customers.append(
            Customer(
                external_ref=f"C{1000 + index}",
                name=f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
                email=f"customer{1000 + index}@example.com",
                phone=f"+9198{rng.randint(10_000_000, 99_999_999)}",
                segment=segment,
                ltv_paise=rupees_to_paise(aov * payments * rng.uniform(0.85, 1.4)),
                average_order_value_paise=rupees_to_paise(aov),
                purchase_frequency=round(rng.uniform(0.4, 6.5), 2),
                preferred_payment_method=_weighted(
                    rng,
                    {
                        PaymentMethod.UPI: 0.48,
                        PaymentMethod.CARD: 0.27,
                        PaymentMethod.NETBANKING: 0.11,
                        PaymentMethod.WALLET: 0.08,
                        PaymentMethod.EMI: 0.04,
                        PaymentMethod.BANK_TRANSFER: 0.02,
                    },
                ),
                communication_preference=_weighted(
                    rng,
                    {
                        CommunicationPreference.WHATSAPP: 0.58,
                        CommunicationPreference.SMS: 0.18,
                        CommunicationPreference.EMAIL: 0.19,
                        CommunicationPreference.VOICE: 0.05,
                    },
                ),
                previous_payment_count=payments,
                previous_success_rate=round(success_rate, 3),
                historical_recovery_rate=round(min(0.85, max(0.05, rng.betavariate(2.4, 5.5))), 3),
                tenure_days=rng.randint(5, 1500),
                opted_out=rng.random() < 0.025,
                lifetime_contacts=rng.randint(0, 4),
            )
        )
    return customers


ROUTE_BY_METHOD: dict[PaymentMethod, tuple[str, ...]] = {
    PaymentMethod.UPI: ("route-upi-alpha", "route-upi-beta"),
    PaymentMethod.CARD: ("route-card-primary", "route-card-secondary"),
    PaymentMethod.NETBANKING: ("route-nb-primary",),
    PaymentMethod.WALLET: ("route-wallet-primary",),
    PaymentMethod.EMI: ("route-card-primary",),
    PaymentMethod.BANK_TRANSFER: ("route-nb-primary",),
}

SUBSCRIPTION_PLANS = (299, 499, 999, 1_999, 4_999, 9_999)

MANDATE_RAILS = (MandateRail.UPI_AUTOPAY, MandateRail.CARD_EMANDATE, MandateRail.NACH)


def _make_mandate(rng: random.Random, customer, now: datetime):
    from app.models.mandate import Mandate

    rail = rng.choice(MANDATE_RAILS)
    status = MandateStatus.ACTIVE if rng.random() < 0.85 else rng.choice([MandateStatus.REVOKED, MandateStatus.PAUSED])
    cap = rng.choice([5_000_00, 10_000_00, 15_000_00, 50_000_00])
    return Mandate(
        customer_id=customer.id,
        external_ref=f"MND{100000 + rng.randint(0, 999999)}",
        rail=rail,
        status=status,
        max_amount_paise=cap,
        sequence_number=rng.randint(1, 3),
        attempts_used=rng.randint(0, 2),
        last_pdn_sent_at=now - timedelta(hours=rng.randint(5, 48)) if rng.random() < 0.7 else None,
        registered_at=now - timedelta(days=rng.randint(10, 400)),
        revoked_at=now - timedelta(days=rng.randint(1, 10)) if status == MandateStatus.REVOKED else None,
    )


def _failure_code(rng: random.Random, kind: EventKind, degraded: bool) -> FailureCode:
    if kind is EventKind.CART_ABANDONMENT:
        return _weighted(rng, CART_FAILURE_CODES)
    if kind is EventKind.OVERDUE_INVOICE:
        return _weighted(rng, INVOICE_FAILURE_CODES)
    if kind is EventKind.SUBSCRIPTION_FAILURE and rng.random() < 0.15:
        return _weighted(
            rng,
            {
                FailureCode.MANDATE_REVOKED: 0.30,
                FailureCode.MANDATE_NOT_FOUND: 0.25,
                FailureCode.MANDATE_AMOUNT_EXCEEDS: 0.20,
                FailureCode.PDN_NOT_DELIVERED: 0.15,
                FailureCode.AFA_REQUIRED: 0.10,
            },
        )
    if degraded:
        return _weighted(
            rng,
            {
                FailureCode.GATEWAY_TIMEOUT: 0.44,
                FailureCode.PSP_UNAVAILABLE: 0.31,
                FailureCode.ISSUER_UNAVAILABLE: 0.17,
                FailureCode.GATEWAY_ERROR: 0.08,
            },
        )
    return _weighted(rng, PAYMENT_FAILURE_CODES)


def _root_cause(rng: random.Random, code: FailureCode, degraded: bool) -> RootCause:
    if degraded and code in {
        FailureCode.GATEWAY_TIMEOUT,
        FailureCode.PSP_UNAVAILABLE,
        FailureCode.ISSUER_UNAVAILABLE,
        FailureCode.GATEWAY_ERROR,
    }:
        return RootCause.ROUTE_DEGRADATION
    priors = FAILURE_CAUSE_PRIORS.get(code)
    if not priors:
        return RootCause.UNKNOWN
    causes = [cause for cause, _ in priors]
    weights = [weight for _, weight in priors]
    residual = max(0.0, 1.0 - sum(weights))
    if residual > 0:
        causes.append(RootCause.UNKNOWN)
        weights.append(residual)
    return rng.choices(causes, weights=weights, k=1)[0]


def _amount_paise(rng: random.Random, customer: Customer, kind: EventKind) -> int:
    aov = customer.average_order_value_paise
    if kind is EventKind.SUBSCRIPTION_FAILURE:
        return rupees_to_paise(rng.choice(SUBSCRIPTION_PLANS))
    if kind is EventKind.OVERDUE_INVOICE:
        return int(aov * rng.uniform(3.0, 14.0))
    return max(rupees_to_paise(99), int(aov * rng.lognormvariate(0.0, 0.42)))


def _legacy_action(rng: random.Random, kind: EventKind) -> ActionType:
    """The pre-Revyn workflow, with the noise a hand-run process actually has."""
    if rng.random() < 0.18:
        allowed = [a for a in ALLOWED_ACTIONS[kind] if a is not ActionType.DO_NOTHING]
        return rng.choice(allowed)
    return LEGACY_POLICY[kind]


def _make_event(
    rng: random.Random,
    *,
    customer: Customer,
    kind: EventKind,
    occurred_at: datetime,
    ref: str,
    degraded_route: str | None,
    is_training: bool,
    control_share: float,
) -> RevenueEvent:
    method = (
        customer.preferred_payment_method
        if rng.random() < 0.72
        else _weighted(rng, dict.fromkeys(PaymentMethod, 1.0))
    )
    if kind is EventKind.OVERDUE_INVOICE:
        method = PaymentMethod.BANK_TRANSFER
    route = rng.choice(ROUTE_BY_METHOD[PaymentMethod(method)])
    degraded = degraded_route is not None and route == degraded_route
    code = _failure_code(rng, kind, degraded)
    cause = _root_cause(rng, code, degraded)
    amount = _amount_paise(rng, customer, kind)

    due_date = None
    if kind is EventKind.OVERDUE_INVOICE:
        due_date = occurred_at - timedelta(days=rng.randint(3, 55))

    event = RevenueEvent(
        external_ref=ref,
        kind=kind,
        status=EventStatus.AT_RISK,
        cohort=Cohort.CONTROL if rng.random() < control_share else Cohort.TREATMENT,
        is_training=is_training,
        customer=customer,
        amount_paise=amount,
        occurred_at=occurred_at,
        due_date=due_date,
        payment_method=method,
        issuer=rng.choice(ISSUERS),
        route=route,
        failure_code=code,
        failure_reason=FAILURE_LABELS.get(code, "Unclassified failure"),
        retry_count=rng.choices([0, 1, 2], weights=[0.68, 0.24, 0.08], k=1)[0]
        if kind in (EventKind.PAYMENT_FAILURE, EventKind.SUBSCRIPTION_FAILURE)
        else 0,
        prior_contacts=rng.choices([0, 1, 2], weights=[0.74, 0.20, 0.06], k=1)[0],
        checkout_duration_seconds=rng.randint(35, 940)
        if kind is EventKind.CART_ABANDONMENT
        else None,
        cart_items=rng.randint(1, 7) if kind is EventKind.CART_ABANDONMENT else None,
        order_ref=f"order_{ref.lower()}",
        payment_ref=f"pay_{ref.lower()}" if kind is not EventKind.CART_ABANDONMENT else None,
        subscription_ref=f"sub_{ref.lower()}" if kind is EventKind.SUBSCRIPTION_FAILURE else None,
        invoice_ref=f"inv_{ref.lower()}" if kind is EventKind.OVERDUE_INVOICE else None,
        root_cause=cause,
        cause_confidence=0.0,
        diagnosis={"degradation_active": degraded, "degradation_ratio": 3.4 if degraded else 1.0},
    )
    return event


def _outcome_inputs(event: RevenueEvent, customer: Customer, degraded: bool) -> OutcomeInputs:
    return OutcomeInputs(
        cause=RootCause(event.root_cause),
        segment=CustomerSegment(customer.segment),
        payment_method=PaymentMethod(event.payment_method),
        amount_paise=event.amount_paise,
        average_order_value_paise=customer.average_order_value_paise,
        previous_success_rate=customer.previous_success_rate,
        historical_recovery_rate=customer.historical_recovery_rate,
        retry_count=event.retry_count,
        prior_contacts=event.prior_contacts,
        local_hour=_local_hour(event.occurred_at),
        degraded=degraded,
    )


def _resolve_history(rng: random.Random, event: RevenueEvent) -> None:
    """Apply the pre-Revyn workflow and roll the observed outcome."""
    from app.data.catalog import intervention

    customer = event.customer
    degraded = bool(event.diagnosis.get("degradation_active"))
    action = (
        ActionType.DO_NOTHING
        if event.cohort == Cohort.CONTROL
        else _legacy_action(rng, EventKind(event.kind))
    )
    spec = intervention(action)
    probability = recovery_probability(_outcome_inputs(event, customer, degraded), action)
    recovered = rng.random() < probability

    event.applied_action = action
    event.contacts_used = 1 if spec.consumes_contact else 0
    event.recovery_cost_paise = spec.cost_paise
    event.resolved_at = event.occurred_at + timedelta(hours=rng.uniform(0.5, 30.0))
    if recovered:
        discount = int(event.amount_paise * spec.discount_pct / 100.0)
        event.status = EventStatus.RECOVERED
        event.recovered_amount_paise = event.amount_paise - discount
        event.recovery_cost_paise += discount
    else:
        event.status = EventStatus.LOST
        event.recovered_amount_paise = 0


#: Money at risk per loss class in the live window, in rupees. Events are generated
#: until each target is met, so the dashboard opens on a realistic revenue-at-risk mix.
LIVE_TARGETS: dict[EventKind, int] = {
    EventKind.PAYMENT_FAILURE: 3_10_000,
    EventKind.CART_ABANDONMENT: 1_90_000,
    EventKind.SUBSCRIPTION_FAILURE: 1_50_000,
    EventKind.OVERDUE_INVOICE: 1_90_000,
}

BUCKET_MINUTES = 15
HEALTH_DAYS = 7
ROUTE_TRAFFIC_SHARE: dict[str, float] = {
    "route-upi-alpha": 0.30,
    "route-upi-beta": 0.18,
    "route-card-primary": 0.22,
    "route-card-secondary": 0.11,
    "route-nb-primary": 0.12,
    "route-wallet-primary": 0.07,
}
ROUTE_METHOD: dict[str, PaymentMethod] = {
    "route-upi-alpha": PaymentMethod.UPI,
    "route-upi-beta": PaymentMethod.UPI,
    "route-card-primary": PaymentMethod.CARD,
    "route-card-secondary": PaymentMethod.CARD,
    "route-nb-primary": PaymentMethod.NETBANKING,
    "route-wallet-primary": PaymentMethod.WALLET,
}


def _diurnal(hour: float) -> float:
    """Traffic shape across an Indian retail day: quiet at dawn, peaking mid-evening."""
    return 0.35 + 0.9 * max(0.0, math.sin(math.pi * (hour - 5.0) / 17.0)) ** 1.4


def build_route_health(
    rng: random.Random, now: datetime, degradation_start: datetime, degradation_end: datetime
) -> list[dict]:
    buckets: list[dict] = []
    total_buckets = HEALTH_DAYS * 24 * 60 // BUCKET_MINUTES
    for step in range(total_buckets):
        start = now - timedelta(minutes=BUCKET_MINUTES * (total_buckets - step))
        load = _diurnal(_local_hour(start))
        for route, share in ROUTE_TRAFFIC_SHARE.items():
            attempts = max(1, int(rng.gauss(240 * share * load, 8 * share * load + 2)))
            rate = rng.uniform(0.075, 0.125)
            if route == DEGRADED_ROUTE and degradation_start <= start < degradation_end:
                # Ramp the failure rate across the incident so the detector sees a trend.
                progress = (start - degradation_start) / (degradation_end - degradation_start)
                rate = 0.09 + 0.30 * min(1.0, progress * 1.6)
            failures = min(attempts, max(0, int(rng.gauss(attempts * rate, attempts * 0.02))))
            buckets.append(
                {
                    "bucket_start": start,
                    "route": route,
                    "method": str(ROUTE_METHOD[route]),
                    "attempts": attempts,
                    "failures": failures,
                    "failed_amount_paise": failures * rng.randint(120_000, 480_000) // 100,
                }
            )
    return buckets


def generate(
    *,
    seed: int,
    customer_count: int,
    history_count: int,
    now: datetime | None = None,
    live_scale: float = 1.0,
) -> tuple[GeneratedDataset, list[dict], tuple[datetime, datetime]]:
    """Build customers, resolved history, live at-risk events and route health buckets."""
    rng = random.Random(seed)
    now = now or utcnow()
    dataset = GeneratedDataset(customers=_build_customers(rng, customer_count))
    # Mandates are created after customer IDs are assigned (in seeding), not here.
    degradation_end = now - timedelta(minutes=12)
    degradation_start = degradation_end - timedelta(minutes=105)

    for index in range(history_count):
        customer = rng.choice(dataset.customers)
        kind = _weighted(rng, KIND_WEIGHTS)
        occurred_at = now - timedelta(
            days=rng.uniform(1.0, HISTORY_DAYS), minutes=rng.uniform(0, 1440)
        )
        # Historical degradation episodes give the model systemic examples to learn from.
        historical_degradation = rng.random() < 0.04
        event = _make_event(
            rng,
            customer=customer,
            kind=kind,
            occurred_at=occurred_at,
            ref=f"TXN{100000 + index}",
            degraded_route=DEGRADED_ROUTE if historical_degradation else None,
            is_training=True,
            control_share=CONTROL_SHARE_HISTORY,
        )
        _resolve_history(rng, event)
        dataset.events.append(event)

    counter = 0
    for kind, target_rupees in LIVE_TARGETS.items():
        target = rupees_to_paise(target_rupees * max(live_scale, 0.01))
        accumulated = 0
        while accumulated < target and counter < 600:
            customer = rng.choice(dataset.customers)
            occurred_at = now - timedelta(minutes=rng.uniform(3, LIVE_WINDOW_HOURS * 60))
            in_incident = degradation_start <= occurred_at < degradation_end
            event = _make_event(
                rng,
                customer=customer,
                kind=kind,
                occurred_at=occurred_at,
                ref=f"EVT{200000 + counter}",
                degraded_route=DEGRADED_ROUTE if in_incident else None,
                is_training=False,
                control_share=CONTROL_SHARE_LIVE,
            )
            dataset.events.append(event)
            accumulated += event.amount_paise
            counter += 1

    buckets = build_route_health(rng, now, degradation_start, degradation_end)
    return dataset, buckets, (degradation_start, degradation_end)
