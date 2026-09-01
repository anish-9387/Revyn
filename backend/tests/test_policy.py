"""The deterministic gate is the safety boundary, so its rules are pinned by tests."""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.core.clock import utcnow
from app.core.constants import ActionType, EventStatus, PolicyRule, PolicyVerdict
from app.services.policy import BudgetState, PolicyEngine, PolicySpec
from tests.conftest import make_customer, make_event


@pytest.fixture
def engine() -> PolicyEngine:
    return PolicyEngine(PolicySpec())


def test_do_nothing_is_always_allowed(engine):
    customer = make_customer()
    event = make_event(customer)
    verdict = engine.evaluate(
        ActionType.DO_NOTHING, event=event, customer=customer, budget=BudgetState()
    )
    assert verdict.verdict is PolicyVerdict.ALLOW


def test_kill_switch_blocks_every_intervention():
    engine = PolicyEngine(PolicySpec(automation_enabled=False))
    customer = make_customer()
    event = make_event(customer)
    verdict = engine.evaluate(
        ActionType.RETRY_PAYMENT, event=event, customer=customer, budget=BudgetState()
    )
    assert verdict.verdict is PolicyVerdict.BLOCK
    assert PolicyRule.AUTOMATION_DISABLED in verdict.reasons


def test_contact_budget_counts_contacts_made_before_revyn(engine):
    customer = make_customer()
    event = make_event(customer, prior_contacts=2)
    budget = BudgetState(contacts_used=1)
    verdict = engine.evaluate(ActionType.WHATSAPP, event=event, customer=customer, budget=budget)
    assert verdict.verdict is PolicyVerdict.BLOCK
    assert PolicyRule.CONTACT_BUDGET_EXHAUSTED in verdict.reasons


def test_retry_budget_includes_gateway_retries(engine):
    customer = make_customer()
    event = make_event(customer, retry_count=2)
    verdict = engine.evaluate(
        ActionType.RETRY_PAYMENT, event=event, customer=customer, budget=BudgetState()
    )
    assert verdict.verdict is PolicyVerdict.BLOCK
    assert PolicyRule.RETRY_BUDGET_EXHAUSTED in verdict.reasons


def test_opted_out_customer_blocks_contact_but_not_silent_retry(engine):
    customer = make_customer(opted_out=True)
    event = make_event(customer)
    contact = engine.evaluate(
        ActionType.WHATSAPP, event=event, customer=customer, budget=BudgetState()
    )
    silent = engine.evaluate(
        ActionType.RETRY_PAYMENT, event=event, customer=customer, budget=BudgetState()
    )
    assert contact.verdict is PolicyVerdict.BLOCK
    assert PolicyRule.CUSTOMER_OPTED_OUT in contact.reasons
    assert silent.verdict is PolicyVerdict.ALLOW


def test_degradation_guard_suspends_retries(engine):
    customer = make_customer()
    event = make_event(customer)
    verdict = engine.evaluate(
        ActionType.RETRY_PAYMENT,
        event=event,
        customer=customer,
        budget=BudgetState(),
        degraded_route=True,
    )
    assert verdict.verdict is PolicyVerdict.BLOCK
    assert PolicyRule.DEGRADATION_ACTIVE in verdict.reasons


def test_high_value_gateway_action_requires_approval(engine):
    customer = make_customer()
    event = make_event(customer, amount_paise=75_000_00)
    verdict = engine.evaluate(
        ActionType.RETRY_PAYMENT, event=event, customer=customer, budget=BudgetState()
    )
    assert verdict.verdict is PolicyVerdict.REQUIRE_APPROVAL
    assert PolicyRule.HIGH_VALUE_APPROVAL in verdict.reasons


def test_large_discount_requires_approval(engine):
    customer = make_customer()
    event = make_event(customer)
    verdict = engine.evaluate(
        ActionType.DISCOUNT,
        event=event,
        customer=customer,
        budget=BudgetState(),
        discount_pct=12.0,
    )
    assert verdict.verdict is PolicyVerdict.REQUIRE_APPROVAL
    assert PolicyRule.DISCOUNT_APPROVAL in verdict.reasons


def test_cooldown_blocks_a_second_contact_too_soon(engine):
    customer = make_customer()
    event = make_event(customer)
    budget = BudgetState(last_contact_at=utcnow() - timedelta(minutes=5))
    verdict = engine.evaluate(ActionType.SMS, event=event, customer=customer, budget=budget)
    assert verdict.verdict is PolicyVerdict.BLOCK
    assert PolicyRule.COOLDOWN_ACTIVE in verdict.reasons


def test_recovered_event_cannot_be_actioned_again(engine):
    customer = make_customer()
    event = make_event(customer, status=EventStatus.RECOVERED)
    verdict = engine.evaluate(
        ActionType.PAYMENT_LINK, event=event, customer=customer, budget=BudgetState()
    )
    assert verdict.verdict is PolicyVerdict.BLOCK
    assert PolicyRule.ALREADY_RECOVERED in verdict.reasons


def test_quiet_hours_window_wraps_past_midnight():
    engine = PolicyEngine(
        PolicySpec(quiet_hours_enforced=True, quiet_hours_start=21, quiet_hours_end=8)
    )
    # 18:30 UTC is midnight IST, inside the 21:00-08:00 window.
    assert engine._in_quiet_hours(utcnow().replace(hour=18, minute=30))
    # 08:30 UTC is 14:00 IST, outside it.
    assert not engine._in_quiet_hours(utcnow().replace(hour=8, minute=30))


def test_friction_budget_reports_blocking_dimensions(engine):
    customer = make_customer()
    event = make_event(customer, prior_contacts=3, retry_count=2)
    budget = engine.friction_budget(event, BudgetState())
    assert budget.exhausted is True
    assert set(budget.blocking) == {"contacts", "retries"}


def test_spec_overrides_only_touch_known_fields():
    spec = PolicySpec()
    updated = spec.with_overrides({"max_contacts": 5, "not_a_field": 9, "max_retries": None})
    assert updated.max_contacts == 5
    assert updated.max_retries == spec.max_retries
