"""Recovery Decision Engine.

Every candidate intervention is priced, and the winner is the one with the highest
risk-adjusted incremental value - not the highest raw recovery probability. Choosing on
uplift rather than gross probability is what lets ``DO_NOTHING`` win honestly: an action
must beat leaving the customer alone by more than it costs in money and friction.

    incremental value = uplift x amount
                      - intervention cost
                      - discount given back
                      - friction priced in rupees
                      - systemic risk penalty
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Protocol

from app.core.constants import ActionType, EventKind, PolicyRule, PolicyVerdict, RootCause
from app.data.catalog import ALLOWED_ACTIONS, METHOD_FALLBACKS, cause_profile, intervention
from app.engines.risk import RiskAssessment
from app.engines.root_cause import Diagnosis
from app.ml.predictor import ActionProbabilities
from app.models.customer import Customer
from app.models.event import RevenueEvent

# Friction is priced against the customer relationship, not the transaction: a full-friction
# touch is charged a floor plus a share of lifetime value. That is what makes Revyn more
# careful with its best customers instead of more aggressive.
FRICTION_FLOOR_PAISE = 1_500
FRICTION_LTV_RATE = 0.0022
# Extra penalty for retrying into a degrading route.
DEGRADATION_PENALTY_PAISE = 2_500


@dataclass(slots=True)
class GateVerdict:
    verdict: PolicyVerdict
    reasons: list[PolicyRule] = field(default_factory=list)

    @property
    def allowed(self) -> bool:
        return self.verdict is not PolicyVerdict.BLOCK


class ActionGate(Protocol):
    """Deterministic policy check. The engine never overrides a BLOCK."""

    def __call__(self, action: ActionType, *, discount_pct: float) -> GateVerdict: ...


def open_gate(action: ActionType, *, discount_pct: float) -> GateVerdict:
    return GateVerdict(verdict=PolicyVerdict.ALLOW)


@dataclass(slots=True)
class ActionOption:
    action: ActionType
    label: str
    probability: float
    uplift: float
    expected_recovery_paise: int
    expected_value_paise: int
    intervention_cost_paise: int
    discount_cost_paise: int
    friction_cost_paise: int
    systemic_penalty_paise: int
    friction_score: float
    discount_pct: float
    verdict: PolicyVerdict
    blocked_reasons: list[str]
    rationale: list[str] = field(default_factory=list)

    @property
    def allowed(self) -> bool:
        return self.verdict is not PolicyVerdict.BLOCK

    def as_dict(self) -> dict:
        payload = asdict(self)
        payload["action"] = str(self.action)
        payload["verdict"] = str(self.verdict)
        payload["probability"] = round(self.probability, 4)
        payload["uplift"] = round(self.uplift, 4)
        payload["friction_score"] = round(self.friction_score, 3)
        return payload


@dataclass(slots=True)
class DecisionOutcome:
    chosen: ActionOption
    options: list[ActionOption]
    organic_probability: float
    rationale: list[str]
    evidence: list[str]
    plan: list[PlanStep]
    model_version: str

    @property
    def acts(self) -> bool:
        return self.chosen.action is not ActionType.DO_NOTHING

    def as_dict(self) -> dict:
        return {
            "chosen": self.chosen.as_dict(),
            "options": [option.as_dict() for option in self.options],
            "organic_probability": round(self.organic_probability, 4),
            "rationale": self.rationale,
            "evidence": self.evidence,
            "plan": [step.as_dict() for step in self.plan],
            "model_version": self.model_version,
        }


@dataclass(slots=True)
class PlanStep:
    action: ActionType
    delay_minutes: float
    reason: str

    def as_dict(self) -> dict:
        return {
            "action": str(self.action),
            "label": intervention(self.action).label,
            "delay_minutes": round(self.delay_minutes, 1),
            "reason": self.reason,
        }


@dataclass(slots=True)
class DecisionInputs:
    event: RevenueEvent
    customer: Customer
    diagnosis: Diagnosis
    risk: RiskAssessment
    probabilities: ActionProbabilities
    contacts_used: int = 0
    customer_contact_budget: int = 3
    degraded_route: bool = False
    min_confidence: float = 0.12
    min_expected_value_paise: int = 5_000
    max_discount_pct: float = 15.0
    #: Posterior recovery rates learned for this merchant, keyed by action.
    learned_rates: dict[ActionType, float] = field(default_factory=dict)
    model_version: str = "heuristic-v1"


def candidate_actions(kind: EventKind) -> tuple[ActionType, ...]:
    return ALLOWED_ACTIONS[kind]


def _friction_cost(inputs: DecisionInputs, friction_score: float) -> int:
    """Rupee cost of the goodwill one touch spends, escalating with contacts already made."""
    relationship_value = FRICTION_FLOOR_PAISE + FRICTION_LTV_RATE * inputs.customer.ltv_paise
    escalation = 1.0 + 0.55 * inputs.contacts_used
    return int(friction_score * relationship_value * escalation)


def _discount_pct(inputs: DecisionInputs, action: ActionType) -> float:
    if action is not ActionType.DISCOUNT:
        return 0.0
    spec = intervention(action)
    # Scale the offer down for cheap carts: the incentive should not exceed the upside.
    scaled = spec.discount_pct if inputs.event.amount_paise >= 1_000_00 else spec.discount_pct * 0.6
    return min(scaled, inputs.max_discount_pct)


def price_option(inputs: DecisionInputs, action: ActionType, gate: ActionGate) -> ActionOption:
    spec = intervention(action)
    amount = inputs.event.amount_paise
    probability = inputs.probabilities.per_action.get(action, inputs.probabilities.organic)
    if action in inputs.learned_rates:
        # Blend the model with what this merchant has actually observed.
        probability = 0.65 * probability + 0.35 * inputs.learned_rates[action]
    uplift = (
        0.0
        if action is ActionType.DO_NOTHING
        else max(probability - inputs.probabilities.organic, 0.0)
    )
    discount_pct = _discount_pct(inputs, action)

    discount_cost = int(amount * discount_pct / 100.0 * probability)
    friction_cost = (
        0 if action is ActionType.DO_NOTHING else _friction_cost(inputs, spec.friction_score)
    )
    systemic_penalty = (
        DEGRADATION_PENALTY_PAISE
        if inputs.degraded_route and action is ActionType.RETRY_PAYMENT
        else 0
    )
    expected_recovery = int(probability * amount)
    expected_value = int(
        uplift * amount - spec.cost_paise - discount_cost - friction_cost - systemic_penalty
    )
    verdict = gate(action, discount_pct=discount_pct)

    return ActionOption(
        action=action,
        label=spec.label,
        probability=probability,
        uplift=uplift,
        expected_recovery_paise=expected_recovery,
        expected_value_paise=0 if action is ActionType.DO_NOTHING else expected_value,
        intervention_cost_paise=spec.cost_paise,
        discount_cost_paise=discount_cost,
        friction_cost_paise=friction_cost,
        systemic_penalty_paise=systemic_penalty,
        friction_score=spec.friction_score,
        discount_pct=discount_pct,
        verdict=verdict.verdict,
        blocked_reasons=[str(reason) for reason in verdict.reasons],
    )


def decide(inputs: DecisionInputs, gate: ActionGate = open_gate) -> DecisionOutcome:
    options = [
        price_option(inputs, action, gate)
        for action in candidate_actions(EventKind(inputs.event.kind))
    ]
    options.sort(key=lambda option: option.expected_value_paise, reverse=True)

    do_nothing = next(o for o in options if o.action is ActionType.DO_NOTHING)
    viable = [
        option
        for option in options
        if option.allowed
        and option.action is not ActionType.DO_NOTHING
        and option.expected_value_paise >= inputs.min_expected_value_paise
        and option.probability >= inputs.min_confidence
    ]
    chosen = viable[0] if viable else do_nothing
    chosen.rationale = _rationale(inputs, chosen, options, bool(viable))
    return DecisionOutcome(
        chosen=chosen,
        options=options,
        organic_probability=inputs.probabilities.organic,
        rationale=chosen.rationale,
        evidence=inputs.diagnosis.evidence,
        plan=build_plan(inputs, chosen, options),
        model_version=inputs.model_version,
    )


def _rationale(
    inputs: DecisionInputs, chosen: ActionOption, options: list[ActionOption], acted: bool
) -> list[str]:
    from app.core.constants import CauseLayer
    from app.core.money import format_inr
    from app.data.catalog import cause_profile

    diagnosis = inputs.diagnosis
    lines = [
        f"Diagnosed as {diagnosis.label.lower()} with {diagnosis.confidence:.0%} confidence",
    ]
    # Regulatory futility line
    try:
        from app.core.constants import RootCause
        rc = RootCause(str(inputs.diagnosis.cause))
        if cause_profile(rc).layer is CauseLayer.REGULATORY and rc is not RootCause.EXECUTION_WINDOW_MISS:
            lines.append("Retry is futile: regulatory state guarantees identical decline - only re-registration or cap amendment can resolve it")
    except Exception:
        pass
    organic = inputs.probabilities.organic
    if not acted:
        best_blocked = next(
            (o for o in options if o.action is not ActionType.DO_NOTHING and not o.allowed), None
        )
        best_priced = next((o for o in options if o.action is not ActionType.DO_NOTHING), None)
        if best_blocked is not None and best_priced is not None and not best_priced.allowed:
            lines.append(
                f"Every intervention is currently gated: {', '.join(best_blocked.blocked_reasons)}"
            )
        elif best_priced is not None:
            lines.append(
                f"Best available action ({best_priced.label}) is worth only "
                f"{format_inr(best_priced.expected_value_paise)} after cost and friction"
            )
        lines.append(
            f"Organic recovery is already {organic:.0%}, so intervening would mostly buy friction"
        )
        return lines

    lines.append(
        f"{chosen.label} lifts recovery from {organic:.0%} to {chosen.probability:.0%} "
        f"(+{chosen.uplift * 100:.0f} points)"
    )
    lines.append(
        f"Incremental value {format_inr(chosen.expected_value_paise)} after "
        f"{format_inr(chosen.intervention_cost_paise + chosen.discount_cost_paise)} cost and "
        f"{format_inr(chosen.friction_cost_paise)} friction"
    )
    if not intervention(chosen.action).consumes_contact:
        lines.append("Silent action, so it spends nothing from the customer contact budget")
    runner_up = next(
        (
            o
            for o in options
            if o.action not in (chosen.action, ActionType.DO_NOTHING) and o.allowed
        ),
        None,
    )
    if runner_up is not None:
        gap = chosen.expected_value_paise - runner_up.expected_value_paise
        lines.append(f"Beats {runner_up.label} by {format_inr(gap)} in risk-adjusted value")
    if chosen.systemic_penalty_paise:
        lines.append("Route is degrading, which is already priced into this choice")
    if inputs.learned_rates.get(chosen.action):
        lines.append(
            f"This merchant recovers {inputs.learned_rates[chosen.action]:.0%} of the time with "
            f"{chosen.label.lower()} in comparable cases"
        )
    return lines


def build_plan(
    inputs: DecisionInputs, chosen: ActionOption, options: list[ActionOption]
) -> list[PlanStep]:
    """Sketch the adaptive journey. Later steps only run if earlier ones do not recover."""
    if chosen.action is ActionType.DO_NOTHING:
        return []

    kind = EventKind(inputs.event.kind)
    profile = cause_profile(RootCause(inputs.event.root_cause))
    first_delay = 0.0
    if chosen.action is ActionType.RETRY_PAYMENT:
        first_delay = 25.0 if profile.transient else 45.0
    steps = [
        PlanStep(
            action=chosen.action,
            delay_minutes=first_delay,
            reason="Highest risk-adjusted value for the diagnosed cause",
        )
    ]

    used_channels = {chosen.action}
    remaining_contacts = max(inputs.customer_contact_budget - inputs.contacts_used, 0)
    for option in options:
        if len(steps) >= 3:
            break
        if option.action in used_channels or option.action is ActionType.DO_NOTHING:
            continue
        if not option.allowed or option.expected_value_paise <= 0:
            continue
        spec = intervention(option.action)
        if spec.consumes_contact:
            if remaining_contacts <= 0:
                continue
            remaining_contacts -= 1
        steps.append(
            PlanStep(
                action=option.action,
                delay_minutes=360.0 if spec.consumes_contact else 60.0,
                reason="Escalation if the previous step does not recover the payment",
            )
        )
        used_channels.add(option.action)

    if kind is EventKind.OVERDUE_INVOICE and ActionType.VOICE in used_channels:
        steps.append(
            PlanStep(
                action=ActionType.PROMISE_FOLLOWUP,
                delay_minutes=1440.0,
                reason="Verify a captured promise to pay on its due date",
            )
        )
    return steps


def alternative_methods(event: RevenueEvent) -> list[str]:
    from app.core.constants import PaymentMethod

    return [str(m) for m in METHOD_FALLBACKS.get(PaymentMethod(event.payment_method), ())][:2]
