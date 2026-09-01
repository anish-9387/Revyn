"""Economics of the decision engine: uplift beats gross probability, and doing nothing wins
whenever intervening cannot pay for itself."""

from __future__ import annotations

import pytest

from app.core.constants import ActionType, EventKind, FailureCode, RootCause
from app.engines.decision import DecisionInputs, decide
from app.engines.risk import assess
from app.engines.root_cause import investigate
from app.ml.predictor import ActionProbabilities, HeuristicPredictor
from app.services.policy import BudgetState, PolicyEngine, PolicySpec
from tests.conftest import make_customer, make_event


def build_inputs(event, customer, **overrides) -> DecisionInputs:
    predictor = HeuristicPredictor()
    from app.data.catalog import ALLOWED_ACTIONS
    from app.engines.features import build_features

    features = build_features(event, customer)
    probabilities = predictor.score(features, list(ALLOWED_ACTIONS[EventKind(event.kind)]))
    defaults = {
        "event": event,
        "customer": customer,
        "diagnosis": investigate(event, customer),
        "risk": assess(event, customer),
        "probabilities": probabilities,
        "model_version": predictor.version,
    }
    return DecisionInputs(**{**defaults, **overrides})


def test_every_intervention_scores_at_least_the_organic_baseline():
    customer = make_customer()
    event = make_event(customer)
    outcome = decide(build_inputs(event, customer))
    for option in outcome.options:
        assert option.probability >= outcome.organic_probability - 1e-9


def test_low_intent_low_value_opportunity_is_left_alone():
    """A small amount, a comparison shopper and two contacts already spent: no action pays."""
    customer = make_customer(
        segment="low",
        average_order_value_paise=600_00,
        previous_success_rate=0.35,
        historical_recovery_rate=0.03,
    )
    event = make_event(
        customer,
        amount_paise=800_00,
        prior_contacts=2,
        root_cause=RootCause.DELIBERATE_ABANDONMENT,
    )
    outcome = decide(build_inputs(event, customer, contacts_used=2))
    assert outcome.chosen.action is ActionType.DO_NOTHING
    assert any("friction" in line or "worth only" in line for line in outcome.rationale)


def test_small_cart_with_real_intent_still_earns_an_offer():
    """The mirror case: the same amount is worth acting on when intent and reach are healthy."""
    customer = make_customer(
        segment="medium", average_order_value_paise=1_200_00, ltv_paise=40_000_00
    )
    event = make_event(
        customer,
        kind=EventKind.CART_ABANDONMENT,
        amount_paise=2_400_00,
        failure_code=FailureCode.PRICE_HESITATION,
        root_cause=RootCause.PRICE_SENSITIVITY,
    )
    outcome = decide(build_inputs(event, customer))
    assert outcome.chosen.action is not ActionType.DO_NOTHING
    assert outcome.chosen.expected_value_paise > 0


def test_transient_decline_prefers_the_silent_retry():
    customer = make_customer()
    event = make_event(customer, amount_paise=6_000_00, root_cause=RootCause.TRANSIENT_BANK_DECLINE)
    outcome = decide(build_inputs(event, customer))
    retry = next(o for o in outcome.options if o.action is ActionType.RETRY_PAYMENT)
    link = next(o for o in outcome.options if o.action is ActionType.PAYMENT_LINK)
    assert retry.expected_value_paise > link.expected_value_paise
    assert retry.friction_cost_paise == 0 or retry.friction_cost_paise < link.friction_cost_paise


def test_expired_card_does_not_prefer_a_retry():
    customer = make_customer()
    event = make_event(
        customer,
        payment_method="card",
        failure_code=FailureCode.CARD_EXPIRED,
        root_cause=RootCause.EXPIRED_INSTRUMENT,
    )
    outcome = decide(build_inputs(event, customer))
    assert outcome.chosen.action is not ActionType.RETRY_PAYMENT


def test_exhausted_budgets_leave_only_the_human_path():
    """Contact and retry budgets spent: automation stops, escalation still needs sign-off."""
    customer = make_customer()
    event = make_event(customer, retry_count=2, prior_contacts=3)
    engine = PolicyEngine(PolicySpec())
    gate = engine.gate_for(event=event, customer=customer, budget=BudgetState())
    outcome = decide(build_inputs(event, customer), gate)
    assert outcome.chosen.action in (ActionType.HUMAN_ESCALATION, ActionType.DO_NOTHING)
    assert all(
        option.allowed for option in outcome.options if option.action is outcome.chosen.action
    )
    blocked = {o.action for o in outcome.options if not o.allowed}
    assert ActionType.RETRY_PAYMENT in blocked and ActionType.WHATSAPP in blocked


def test_kill_switch_forces_do_nothing():
    customer = make_customer()
    event = make_event(customer)
    engine = PolicyEngine(PolicySpec(automation_enabled=False))
    gate = engine.gate_for(event=event, customer=customer, budget=BudgetState())
    outcome = decide(build_inputs(event, customer), gate)
    assert outcome.chosen.action is ActionType.DO_NOTHING


def test_discount_cost_is_charged_against_the_recovery():
    customer = make_customer()
    event = make_event(customer, kind=EventKind.CART_ABANDONMENT, amount_paise=20_000_00)
    outcome = decide(build_inputs(event, customer))
    discount = next(o for o in outcome.options if o.action is ActionType.DISCOUNT)
    assert discount.discount_pct > 0
    assert discount.discount_cost_paise > 0
    assert discount.expected_value_paise < discount.uplift * event.amount_paise


def test_cart_abandonment_cannot_retry_a_payment_that_never_happened():
    customer = make_customer()
    event = make_event(customer, kind=EventKind.CART_ABANDONMENT)
    outcome = decide(build_inputs(event, customer))
    assert ActionType.RETRY_PAYMENT not in {option.action for option in outcome.options}


def test_degraded_route_penalises_the_retry_option():
    customer = make_customer()
    event = make_event(customer)
    healthy = decide(build_inputs(event, customer))
    degraded = decide(build_inputs(event, customer, degraded_route=True))
    healthy_retry = next(o for o in healthy.options if o.action is ActionType.RETRY_PAYMENT)
    degraded_retry = next(o for o in degraded.options if o.action is ActionType.RETRY_PAYMENT)
    assert degraded_retry.expected_value_paise < healthy_retry.expected_value_paise


def test_plan_respects_the_remaining_contact_budget():
    customer = make_customer()
    event = make_event(customer, prior_contacts=2)
    outcome = decide(build_inputs(event, customer, contacts_used=2, customer_contact_budget=3))
    from app.data.catalog import intervention

    contact_steps = [step for step in outcome.plan if intervention(step.action).consumes_contact]
    assert len(contact_steps) <= 1


def test_learned_rates_shift_the_ranking():
    customer = make_customer()
    event = make_event(customer)
    baseline = decide(build_inputs(event, customer))
    boosted = decide(build_inputs(event, customer, learned_rates={ActionType.VOICE: 0.95}))
    baseline_voice = next(o for o in baseline.options if o.action is ActionType.VOICE)
    boosted_voice = next(o for o in boosted.options if o.action is ActionType.VOICE)
    assert boosted_voice.probability > baseline_voice.probability


@pytest.mark.parametrize("kind", list(EventKind))
def test_do_nothing_is_available_for_every_loss_class(kind):
    customer = make_customer()
    event = make_event(customer, kind=kind)
    outcome = decide(build_inputs(event, customer))
    assert ActionType.DO_NOTHING in {option.action for option in outcome.options}
    assert outcome.chosen.expected_value_paise >= 0


def test_uplift_is_zero_when_probabilities_match_the_baseline():
    customer = make_customer()
    event = make_event(customer)
    flat = ActionProbabilities(organic=0.4, per_action={ActionType.RETRY_PAYMENT: 0.4})
    outcome = decide(build_inputs(event, customer, probabilities=flat))
    retry = next(o for o in outcome.options if o.action is ActionType.RETRY_PAYMENT)
    assert retry.uplift == 0.0
    assert retry.expected_value_paise < 0
    assert outcome.chosen.action is ActionType.DO_NOTHING
