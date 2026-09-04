"""Latent recovery process used by the synthetic dataset and the gateway simulator.

This is the ground truth Revyn is trying to learn. Keeping it in one place means the
model is evaluated against the same process that generates the demo outcomes, and it is
deliberately richer than any heuristic in the codebase so the fitted model has real
structure to discover.

Nothing outside the synthetic data path may import this module.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.core.constants import ActionType, CustomerSegment, PaymentMethod, RootCause
from app.data.catalog import affinity, cause_profile, intervention

# Merchant-specific quirks. These are what make the learned playbook non-obvious:
# this merchant over-performs on WhatsApp and under-performs on SMS.
CHANNEL_BIAS: dict[ActionType, float] = {
    ActionType.WHATSAPP: 0.42,
    ActionType.SMS: -0.34,
    ActionType.VOICE: 0.16,
    ActionType.EMAIL: -0.08,
    ActionType.PAYMENT_LINK: 0.12,
}

SEGMENT_BIAS: dict[CustomerSegment, float] = {
    CustomerSegment.VIP: 0.55,
    CustomerSegment.HIGH: 0.30,
    CustomerSegment.MEDIUM: 0.0,
    CustomerSegment.LOW: -0.28,
    CustomerSegment.NEW: -0.12,
}

METHOD_BIAS: dict[PaymentMethod, float] = {
    PaymentMethod.UPI: 0.18,
    PaymentMethod.CARD: 0.05,
    PaymentMethod.NETBANKING: -0.10,
    PaymentMethod.WALLET: -0.05,
    PaymentMethod.EMI: -0.20,
    PaymentMethod.BANK_TRANSFER: -0.15,
}


@dataclass(slots=True)
class OutcomeInputs:
    cause: RootCause
    segment: CustomerSegment
    payment_method: PaymentMethod
    amount_paise: int
    average_order_value_paise: int
    previous_success_rate: float
    historical_recovery_rate: float
    retry_count: int
    prior_contacts: int
    local_hour: float
    degraded: bool


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _logit(p: float) -> float:
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def organic_probability(inputs: OutcomeInputs) -> float:
    """Chance the money arrives with no intervention at all."""
    profile = cause_profile(inputs.cause)
    amount_ratio = inputs.amount_paise / max(inputs.average_order_value_paise, 1)
    logit = (
        -2.45
        + 1.45 * math.log(profile.organic_multiplier)
        + 1.15 * inputs.previous_success_rate
        + 0.85 * inputs.historical_recovery_rate
        - 0.30 * inputs.retry_count
        - 0.22 * math.log1p(amount_ratio)
        + 0.55 * SEGMENT_BIAS.get(inputs.segment, 0.0)
    )
    # Regulatory causes almost never self-heal
    if profile.layer.value == "regulatory" and inputs.cause.value not in ("execution_window_miss",):
        logit -= 2.2
    return _sigmoid(logit)


def intervention_lift(inputs: OutcomeInputs, action: ActionType) -> float:
    """Chance the intervention itself converts a customer who would not have paid."""
    if action is ActionType.DO_NOTHING:
        return 0.0
    spec = intervention(action)
    profile = cause_profile(inputs.cause)
    amount_ratio = inputs.amount_paise / max(inputs.average_order_value_paise, 1)
    # Evening contacts convert better than early-morning ones.
    hour_effect = 0.22 * math.sin(math.pi * (inputs.local_hour - 6.0) / 18.0)

    logit = (
        _logit(spec.base_success)
        + 1.20 * math.log(max(affinity(inputs.cause, action), 0.05))
        + 0.60 * inputs.previous_success_rate
        - 0.13 * inputs.prior_contacts
        - 0.18 * math.log1p(amount_ratio)
        + SEGMENT_BIAS.get(inputs.segment, 0.0)
        + METHOD_BIAS.get(inputs.payment_method, 0.0)
        + CHANNEL_BIAS.get(action, 0.0)
        + hour_effect
    )
    if inputs.degraded and action is ActionType.RETRY_PAYMENT:
        logit -= 1.55
    if action is ActionType.RETRY_PAYMENT and not profile.retryable:
        logit -= 1.85
    # Regulatory futility: retry never works
    if profile.layer.value == "regulatory" and action is ActionType.RETRY_PAYMENT and inputs.cause.value != "execution_window_miss":
        logit -= 4.5
    if action is ActionType.REREGISTER_MANDATE and profile.layer.value == "regulatory":
        logit += 0.6
    if action is ActionType.AMEND_MANDATE_CAP and inputs.cause is RootCause.MANDATE_CAP_EXCEEDED:
        logit += 0.8
    if action is ActionType.SEND_PDN and inputs.cause is RootCause.PDN_MISSING:
        logit += 0.9
    if action is ActionType.HUMAN_ESCALATION and inputs.amount_paise < 5_000_00:
        logit -= 0.45
    return _sigmoid(logit)


def recovery_probability(inputs: OutcomeInputs, action: ActionType) -> float:
    """Composed probability. An intervention can never score below doing nothing."""
    organic = organic_probability(inputs)
    return organic + (1.0 - organic) * intervention_lift(inputs, action)
