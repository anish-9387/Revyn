"""Revenue Risk Radar scoring behaviour."""

from __future__ import annotations

from datetime import timedelta

from app.core.clock import utcnow
from app.core.constants import EventKind, RootCause
from app.engines import risk
from tests.conftest import make_customer, make_event


def test_bigger_amount_scores_higher_risk():
    customer = make_customer()
    small = risk.assess(make_event(customer, amount_paise=500_00), customer)
    large = risk.assess(make_event(customer, amount_paise=90_000_00), customer)
    assert large.risk_score > small.risk_score


def test_payment_failure_urgency_decays_with_age():
    customer = make_customer()
    fresh = make_event(customer)
    stale = make_event(customer, occurred_at=utcnow() - timedelta(hours=18))
    assert risk.urgency(fresh) > risk.urgency(stale)


def test_overdue_invoice_urgency_grows_with_days_past_due():
    customer = make_customer()
    now = utcnow()
    recent = make_event(
        customer,
        kind=EventKind.OVERDUE_INVOICE,
        occurred_at=now,
        due_date=now - timedelta(days=4),
    )
    ancient = make_event(
        customer,
        kind=EventKind.OVERDUE_INVOICE,
        occurred_at=now,
        due_date=now - timedelta(days=50),
    )
    assert risk.urgency(ancient, now=now) > risk.urgency(recent, now=now)


def test_hard_declines_are_more_severe_than_transient_ones():
    customer = make_customer()
    transient = make_event(customer, root_cause=RootCause.TRANSIENT_BANK_DECLINE)
    hard = make_event(customer, root_cause=RootCause.EXPIRED_INSTRUMENT, retry_count=2)
    assert risk.severity(hard) > risk.severity(transient)


def test_priority_saturates_so_one_whale_cannot_own_the_queue():
    customer = make_customer()
    event = make_event(customer, amount_paise=90_000_00)
    assessment = risk.assess(event, customer)
    modest = risk.priority(20_000_00, assessment, customer)
    enormous = risk.priority(50_00_000_00, assessment, customer)
    assert modest < enormous <= 100.0
    assert enormous - modest < 100.0


def test_higher_value_customer_ranks_above_an_identical_case():
    vip = make_customer(segment="vip", ltv_paise=30_00_000_00)
    low = make_customer(segment="low", external_ref="C9002", ltv_paise=20_000_00)
    event_vip = make_event(vip)
    event_low = make_event(low, external_ref="EVT9002")
    assert risk.priority(5_000_00, risk.assess(event_vip, vip), vip) > risk.priority(
        5_000_00, risk.assess(event_low, low), low
    )
