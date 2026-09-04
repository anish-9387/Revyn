"""Recovery Strategy Simulator.

Replays the current open book of revenue at risk through the decision engine under a
proposed policy and reports the difference. Nothing is written and nothing is executed, so a
merchant can compare policies before adopting one.

Two baselines are produced for context: the merchant legacy workflow, which applies one fixed
action per loss class, and the live Revyn policy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ActionType, EventKind, EventStatus, PolicyVerdict
from app.data.catalog import intervention
from app.engines import degradation as degradation_engine
from app.engines import learning
from app.engines.decision import DecisionInputs, decide
from app.engines.features import FeatureContext, build_features
from app.engines.risk import assess
from app.engines.root_cause import investigate
from app.ml.predictor import get_predictor
from app.models.event import RevenueEvent
from app.services.policy import BudgetState, PolicyEngine, PolicySpec

LEGACY_WORKFLOW: dict[EventKind, ActionType] = {
    EventKind.PAYMENT_FAILURE: ActionType.RETRY_PAYMENT,
    EventKind.CART_ABANDONMENT: ActionType.EMAIL,
    EventKind.SUBSCRIPTION_FAILURE: ActionType.RETRY_PAYMENT,
    EventKind.OVERDUE_INVOICE: ActionType.EMAIL,
}


@dataclass(slots=True)
class SimulationResult:
    label: str
    events: int = 0
    revenue_at_risk_paise: int = 0
    expected_recovery_paise: int = 0
    expected_incremental_paise: int = 0
    intervention_cost_paise: int = 0
    discount_cost_paise: int = 0
    customer_contacts: int = 0
    interventions: int = 0
    do_nothing: int = 0
    approvals_required: int = 0
    blocked: int = 0
    npci_wasted: int = 0
    futile_prevented: int = 0
    action_mix: dict[str, int] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "events": self.events,
            "revenue_at_risk_paise": self.revenue_at_risk_paise,
            "expected_recovery_paise": self.expected_recovery_paise,
            "expected_incremental_paise": self.expected_incremental_paise,
            "intervention_cost_paise": self.intervention_cost_paise,
            "discount_cost_paise": self.discount_cost_paise,
            "customer_contacts": self.customer_contacts,
            "interventions": self.interventions,
            "do_nothing": self.do_nothing,
            "approvals_required": self.approvals_required,
            "blocked": self.blocked,
            "npci_wasted": self.npci_wasted,
            "futile_prevented": self.futile_prevented,
            "action_mix": self.action_mix,
            "net_expected_paise": self.expected_incremental_paise
            - self.intervention_cost_paise
            - self.discount_cost_paise,
        }


@dataclass(slots=True)
class ScoredEvent:
    """Everything the simulator needs, computed once and reused for every policy."""

    event: RevenueEvent
    features: dict
    diagnosis: Any
    risk: Any
    degraded: bool
    learned: dict[ActionType, float]


async def load_open_book(session: AsyncSession, *, limit: int = 400) -> list[ScoredEvent]:
    state = await degradation_engine.detect(session)
    stmt = (
        select(RevenueEvent)
        .where(
            RevenueEvent.is_training.is_(False),
            RevenueEvent.status.in_(
                [EventStatus.AT_RISK, EventStatus.IN_RECOVERY, EventStatus.SUPPRESSED]
            ),
        )
        .order_by(RevenueEvent.amount_paise.desc())
        .limit(limit)
    )
    events = (await session.execute(stmt)).unique().scalars().all()

    scored: list[ScoredEvent] = []
    for event in events:
        signal = state.signal_for(event.route, str(event.payment_method))
        diagnosis = investigate(event, event.customer, signal)
        scored.append(
            ScoredEvent(
                event=event,
                features=build_features(
                    event,
                    event.customer,
                    FeatureContext(
                        degradation_active=signal.route_degraded,
                        degradation_ratio=signal.route_ratio,
                        method_failure_rate=signal.method_ratio,
                    ),
                ),
                diagnosis=diagnosis,
                risk=assess(event, event.customer),
                degraded=signal.route_degraded,
                learned=await learning.learned_rates(
                    session,
                    learning.context_key(event.kind, diagnosis.cause, event.customer.segment),
                ),
            )
        )
    return scored


def _record(result: SimulationResult, option, event: RevenueEvent) -> None:
    result.events += 1
    result.revenue_at_risk_paise += event.amount_paise
    key = str(option.action)
    result.action_mix[key] = result.action_mix.get(key, 0) + 1
    # Wasted = RETRY on regulatory futile
    from app.core.constants import RootCause
    from app.data.catalog import cause_profile

    try:
        rc = RootCause(str(event.root_cause))
        layer = cause_profile(rc).layer
        if layer.value == "regulatory" and option.action is ActionType.RETRY_PAYMENT and rc.value != "execution_window_miss":
            if option.verdict is PolicyVerdict.BLOCK:
                result.futile_prevented += 1
            else:
                result.npci_wasted += 1
    except Exception:
        pass
    if option.action is ActionType.DO_NOTHING:
        result.do_nothing += 1
        return
    result.interventions += 1
    result.expected_recovery_paise += option.expected_recovery_paise
    result.expected_incremental_paise += int(option.uplift * event.amount_paise)
    result.intervention_cost_paise += option.intervention_cost_paise
    result.discount_cost_paise += option.discount_cost_paise
    if intervention(option.action).consumes_contact:
        result.customer_contacts += 1
    if option.verdict is PolicyVerdict.REQUIRE_APPROVAL:
        result.approvals_required += 1


def simulate(book: list[ScoredEvent], spec: PolicySpec, label: str) -> SimulationResult:
    """Score the whole open book under one policy."""
    result = SimulationResult(label=label)
    engine = PolicyEngine(spec)
    predictor = get_predictor()

    for scored in book:
        event = scored.event
        # Mandate-aware budget: assume 0 used, pdn missing unless known
        budget = BudgetState(root_cause=event.root_cause, is_first_presentation=True, npci_attempts_used=0)
        gate = engine.gate_for(
            event=event,
            customer=event.customer,
            budget=budget,
            degraded_route=scored.degraded,
        )
        probabilities = predictor.score(scored.features, list(_allowed(EventKind(event.kind))))
        outcome = decide(
            DecisionInputs(
                event=event,
                customer=event.customer,
                diagnosis=scored.diagnosis,
                risk=scored.risk,
                probabilities=probabilities,
                contacts_used=event.prior_contacts,
                customer_contact_budget=spec.max_contacts,
                degraded_route=scored.degraded,
                min_confidence=spec.min_confidence,
                min_expected_value_paise=spec.min_expected_value_paise,
                max_discount_pct=spec.max_discount_pct,
                learned_rates=scored.learned,
                model_version=predictor.version,
            ),
            gate,
        )
        if all(
            not option.allowed
            for option in outcome.options
            if option.action is not ActionType.DO_NOTHING
        ):
            result.blocked += 1
        _record(result, outcome.chosen, event)
    return result


def simulate_legacy(book: list[ScoredEvent], spec: PolicySpec) -> SimulationResult:
    """Fixed one-action-per-loss-class workflow, contacted regardless of economics."""
    result = SimulationResult(label="Legacy fixed workflow")
    predictor = get_predictor()
    for scored in book:
        event = scored.event
        action = LEGACY_WORKFLOW[EventKind(event.kind)]
        probabilities = predictor.score(scored.features, [action])
        outcome = decide(
            DecisionInputs(
                event=event,
                customer=event.customer,
                diagnosis=scored.diagnosis,
                risk=scored.risk,
                probabilities=probabilities,
                contacts_used=event.prior_contacts,
                customer_contact_budget=spec.max_contacts,
                degraded_route=scored.degraded,
                min_confidence=0.0,
                min_expected_value_paise=-(10**12),
                max_discount_pct=spec.max_discount_pct,
                model_version=predictor.version,
            ),
        )
        option = next(o for o in outcome.options if o.action is action)
        _record(result, option, event)
    return result


def _allowed(kind: EventKind):
    from app.data.catalog import ALLOWED_ACTIONS

    return ALLOWED_ACTIONS[kind]


def compare(current: SimulationResult, proposed: SimulationResult) -> dict[str, Any]:
    current_net = current.as_dict()["net_expected_paise"]
    proposed_net = proposed.as_dict()["net_expected_paise"]
    contact_change = (
        (proposed.customer_contacts - current.customer_contacts) / current.customer_contacts
        if current.customer_contacts
        else 0.0
    )
    return {
        "expected_recovery_delta_paise": proposed.expected_recovery_paise
        - current.expected_recovery_paise,
        "net_expected_delta_paise": proposed_net - current_net,
        "incremental_delta_paise": proposed.expected_incremental_paise
        - current.expected_incremental_paise,
        "contact_delta": proposed.customer_contacts - current.customer_contacts,
        "contact_change_pct": round(contact_change * 100, 1),
        "intervention_delta": proposed.interventions - current.interventions,
        "discount_cost_delta_paise": proposed.discount_cost_paise - current.discount_cost_paise,
        "approval_delta": proposed.approvals_required - current.approvals_required,
    }


async def run_what_if(
    session: AsyncSession, *, current: PolicySpec, overrides: dict[str, Any], limit: int = 400
) -> dict[str, Any]:
    book = await load_open_book(session, limit=limit)
    proposed_spec = current.with_overrides(overrides)
    current_result = simulate(book, current, "Current Revyn policy")
    proposed_result = simulate(book, proposed_spec, "Simulated policy")
    legacy_result = simulate_legacy(book, current)
    return {
        "sample_size": len(book),
        "current": current_result.as_dict(),
        "proposed": proposed_result.as_dict(),
        "legacy_baseline": legacy_result.as_dict(),
        "delta": compare(current_result, proposed_result),
        "delta_vs_legacy": compare(legacy_result, proposed_result),
        "current_policy": current.as_dict(),
        "proposed_policy": proposed_spec.as_dict(),
        "changed_fields": {
            field_name: {
                "from": getattr(current, field_name),
                "to": getattr(proposed_spec, field_name),
            }
            for field_name in current.__dataclass_fields__
            if getattr(current, field_name) != getattr(proposed_spec, field_name)
        },
    }
