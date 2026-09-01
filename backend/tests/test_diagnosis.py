"""Root-cause investigation and the calibrated predictor."""

from __future__ import annotations

from app.core.constants import ActionType, CauseLayer, EventKind, FailureCode, RootCause
from app.engines.features import build_features
from app.engines.root_cause import SystemicSignal, investigate
from app.ml.predictor import HeuristicPredictor
from tests.conftest import make_customer, make_event

ALL_ACTIONS = [
    ActionType.RETRY_PAYMENT,
    ActionType.PAYMENT_LINK,
    ActionType.WHATSAPP,
    ActionType.VOICE,
    ActionType.DISCOUNT,
]


def test_expired_card_is_diagnosed_as_an_expired_instrument():
    customer = make_customer()
    event = make_event(customer, payment_method="card", failure_code=FailureCode.CARD_EXPIRED)
    diagnosis = investigate(event, customer)
    assert diagnosis.cause is RootCause.EXPIRED_INSTRUMENT
    assert diagnosis.retryable is False


def test_route_degradation_outranks_a_bank_decline_when_the_route_is_sick():
    customer = make_customer()
    event = make_event(customer, failure_code=FailureCode.GATEWAY_TIMEOUT)
    healthy = investigate(event, customer, SystemicSignal())
    degraded = investigate(
        event,
        customer,
        SystemicSignal(
            route_degraded=True,
            route_ratio=4.2,
            route_failure_share=0.62,
            route_name="route-upi-alpha",
        ),
    )

    def probability_of(diagnosis, cause: RootCause) -> float:
        return next((c.probability for c in diagnosis.candidates if c.cause is cause), 0.0)

    assert healthy.cause is RootCause.ROUTE_TIMEOUT
    assert degraded.cause is RootCause.ROUTE_DEGRADATION
    assert degraded.layer is CauseLayer.SYSTEMIC
    assert probability_of(degraded, RootCause.ROUTE_DEGRADATION) > probability_of(
        healthy, RootCause.ROUTE_DEGRADATION
    )
    assert any("4.2x" in line for line in degraded.evidence)
    assert any("62%" in line for line in degraded.evidence)


def test_repeated_failures_shift_a_decline_from_transient_to_hard():
    customer = make_customer()
    once = investigate(make_event(customer, failure_code=FailureCode.ISSUER_DECLINED), customer)
    thrice = investigate(
        make_event(customer, failure_code=FailureCode.ISSUER_DECLINED, retry_count=2), customer
    )
    assert once.cause is RootCause.TRANSIENT_BANK_DECLINE
    assert thrice.cause is RootCause.HARD_BANK_DECLINE


def test_expensive_cart_points_at_price_sensitivity():
    customer = make_customer(average_order_value_paise=2_000_00)
    event = make_event(
        customer,
        kind=EventKind.CART_ABANDONMENT,
        amount_paise=9_000_00,
        failure_code=FailureCode.PRICE_HESITATION,
        checkout_duration_seconds=200,
        cart_items=3,
    )
    diagnosis = investigate(event, customer)
    assert diagnosis.cause is RootCause.PRICE_SENSITIVITY
    assert any("average order value" in line for line in diagnosis.evidence)


def test_candidate_probabilities_form_a_distribution():
    customer = make_customer()
    diagnosis = investigate(make_event(customer), customer)
    assert diagnosis.candidates
    assert 0.0 < diagnosis.confidence <= 1.0
    assert sum(c.probability for c in diagnosis.candidates) <= 1.0 + 1e-9


def test_no_intervention_scores_below_doing_nothing():
    customer = make_customer()
    event = make_event(customer)
    scores = HeuristicPredictor().score(build_features(event, customer), ALL_ACTIONS)
    for action in ALL_ACTIONS:
        assert scores.per_action[action] >= scores.organic
        assert scores.uplift(action) >= 0.0


def test_retrying_a_dead_instrument_is_scored_down():
    customer = make_customer()
    retryable = make_event(customer, root_cause=RootCause.TRANSIENT_BANK_DECLINE)
    dead = make_event(customer, root_cause=RootCause.EXPIRED_INSTRUMENT)
    predictor = HeuristicPredictor()
    good = predictor.score(build_features(retryable, customer), [ActionType.RETRY_PAYMENT])
    bad = predictor.score(build_features(dead, customer), [ActionType.RETRY_PAYMENT])
    assert good.uplift(ActionType.RETRY_PAYMENT) > bad.uplift(ActionType.RETRY_PAYMENT)


def test_degradation_suppresses_the_retry_estimate():
    from app.engines.features import FeatureContext

    customer = make_customer()
    event = make_event(customer)
    predictor = HeuristicPredictor()
    healthy = predictor.score(build_features(event, customer), [ActionType.RETRY_PAYMENT])
    degraded = predictor.score(
        build_features(
            event, customer, FeatureContext(degradation_active=True, degradation_ratio=4.0)
        ),
        [ActionType.RETRY_PAYMENT],
    )
    assert degraded.uplift(ActionType.RETRY_PAYMENT) < healthy.uplift(ActionType.RETRY_PAYMENT)


def test_contact_fatigue_lowers_the_estimate():
    customer = make_customer()
    predictor = HeuristicPredictor()
    fresh = predictor.score(build_features(make_event(customer), customer), [ActionType.WHATSAPP])
    tired = predictor.score(
        build_features(make_event(customer, prior_contacts=3), customer), [ActionType.WHATSAPP]
    )
    assert tired.uplift(ActionType.WHATSAPP) < fresh.uplift(ActionType.WHATSAPP)
