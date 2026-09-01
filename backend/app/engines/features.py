"""Feature extraction shared by training and inference.

Both paths call :func:`build_features` so the model never sees a feature at serve time
that it did not see while fitting. Only information available at detection time is
used; nothing derived from the outcome enters the vector.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

from app.core.clock import as_utc
from app.core.constants import ActionType, EventKind, PaymentMethod, RootCause
from app.core.money import paise_to_rupees
from app.data.catalog import affinity, cause_profile, intervention
from app.models.customer import Customer
from app.models.event import RevenueEvent

# Indian Standard Time offset, used for the hour-of-day features.
IST_OFFSET_HOURS = 5.5


@dataclass(slots=True)
class FeatureContext:
    """Signals that live outside the event row itself."""

    degradation_active: bool = False
    degradation_ratio: float = 1.0
    method_failure_rate: float = 0.0
    open_journeys_for_customer: int = 0


def _log1p_rupees(paise: int) -> float:
    return math.log1p(max(paise_to_rupees(paise), 0.0))


def _local_hour(moment: datetime) -> float:
    return (as_utc(moment).hour + as_utc(moment).minute / 60.0 + IST_OFFSET_HOURS) % 24.0


def build_features(
    event: RevenueEvent,
    customer: Customer,
    context: FeatureContext | None = None,
) -> dict[str, float | str]:
    ctx = context or FeatureContext()
    hour = _local_hour(event.occurred_at)
    amount = event.amount_paise
    aov = max(customer.average_order_value_paise, 1)
    days_overdue = 0.0
    if event.due_date is not None:
        days_overdue = max(
            (as_utc(event.occurred_at) - as_utc(event.due_date)).total_seconds() / 86_400.0, 0.0
        )

    profile = cause_profile(RootCause(event.root_cause))
    return {
        # Categorical - one-hot encoded by the vectoriser.
        "kind": str(event.kind),
        "payment_method": str(event.payment_method),
        "failure_code": str(event.failure_code or "none"),
        "root_cause": str(event.root_cause),
        "cause_layer": str(profile.layer),
        "segment": str(customer.segment),
        "issuer": event.issuer,
        "route": event.route,
        # Numeric.
        "amount_log": _log1p_rupees(amount),
        "amount_vs_aov": min(amount / aov, 12.0),
        "retry_count": float(event.retry_count),
        "prior_contacts": float(event.prior_contacts),
        "hour_sin": math.sin(2 * math.pi * hour / 24.0),
        "hour_cos": math.cos(2 * math.pi * hour / 24.0),
        "weekend": 1.0 if as_utc(event.occurred_at).weekday() >= 5 else 0.0,
        "prev_success_rate": customer.previous_success_rate,
        "prev_payments_log": math.log1p(customer.previous_payment_count),
        "historical_recovery_rate": customer.historical_recovery_rate,
        "purchase_frequency": customer.purchase_frequency,
        "ltv_log": _log1p_rupees(customer.ltv_paise),
        "tenure_log": math.log1p(customer.tenure_days),
        "value_weight": customer.value_weight,
        "checkout_duration": float(event.checkout_duration_seconds or 0),
        "cart_items": float(event.cart_items or 0),
        "days_overdue": days_overdue,
        "preferred_method": 1.0
        if PaymentMethod(event.payment_method) == PaymentMethod(customer.preferred_payment_method)
        else 0.0,
        "cause_transient": 1.0 if profile.transient else 0.0,
        "cause_retryable": 1.0 if profile.retryable else 0.0,
        "organic_multiplier": profile.organic_multiplier,
        "degradation_active": 1.0 if ctx.degradation_active else 0.0,
        "degradation_ratio": min(ctx.degradation_ratio, 8.0),
        "method_failure_rate": ctx.method_failure_rate,
    }


def with_action(features: dict[str, float | str], action: ActionType) -> dict[str, float | str]:
    """Add the treatment columns. Substituting the action is how counterfactuals are read."""
    spec = intervention(action)
    cause = RootCause(str(features.get("root_cause", RootCause.UNKNOWN)))
    return {
        **features,
        "action": str(action),
        "action_base_success": spec.base_success,
        "action_friction": spec.friction_score,
        "action_affinity": affinity(cause, action),
        "action_is_contact": 1.0 if spec.consumes_contact else 0.0,
        "action_is_gateway": 1.0 if spec.touches_gateway else 0.0,
    }


def kind_default_failure(kind: EventKind) -> str:
    return {
        EventKind.CART_ABANDONMENT: "checkout_timeout",
        EventKind.OVERDUE_INVOICE: "invoice_unpaid",
    }.get(kind, "none")
