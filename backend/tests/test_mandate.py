import pytest
from datetime import datetime, timedelta

from app.core.constants import ActionType, PolicyRule, PolicyVerdict, RootCause
from app.engines.mandate import (
    REGULATORY_FUTILE_CAUSES,
    attempts_remaining,
    in_execution_window,
    is_retry_futile,
    pdn_satisfied,
    required_remedy,
)
from app.services.policy import BudgetState, PolicyEngine, PolicySpec
from tests.conftest import make_customer, make_event


@pytest.fixture
def policy_engine():
    return PolicyEngine(
        PolicySpec(
            execution_window_guard=True,
            pdn_lead_hours=24.0,
            npci_max_attempts=4,
        )
    )


@pytest.mark.parametrize("cause", REGULATORY_FUTILE_CAUSES)
def test_retry_blocked_for_regulatory_causes(policy_engine, cause):
    customer = make_customer()
    event = make_event(customer)
    budget = BudgetState(root_cause=cause.value)
    
    now = datetime(2023, 1, 1, 0, 0, 0)
    verdict = policy_engine.evaluate(
        ActionType.RETRY_PAYMENT,
        event=event,
        customer=customer,
        budget=budget,
        now=now,
    )
    
    assert verdict.verdict == PolicyVerdict.BLOCK
    assert PolicyRule.RETRY_FUTILE in verdict.reasons


def test_execution_window_miss_not_blocked_as_futile(policy_engine):
    customer = make_customer()
    event = make_event(customer)
    budget = BudgetState(root_cause=RootCause.EXECUTION_WINDOW_MISS.value)
    now = datetime(2023, 1, 1, 0, 0, 0)
    
    verdict = policy_engine.evaluate(
        ActionType.RETRY_PAYMENT,
        event=event,
        customer=customer,
        budget=budget,
        now=now,
    )
    
    assert PolicyRule.RETRY_FUTILE not in verdict.reasons


def test_npci_budget_limit(policy_engine):
    customer = make_customer()
    event = make_event(customer)
    budget = BudgetState(npci_attempts_used=4)
    now = datetime(2023, 1, 1, 0, 0, 0)
    
    verdict = policy_engine.evaluate(
        ActionType.RETRY_PAYMENT,
        event=event,
        customer=customer,
        budget=budget,
        now=now,
    )
    
    assert verdict.verdict == PolicyVerdict.BLOCK
    assert PolicyRule.NPCI_BUDGET_EXHAUSTED in verdict.reasons


def test_in_execution_window():
    # 10:00 to 13:00 IST is peak. 10:00 IST = 04:30 UTC
    peak_start = datetime(2023, 1, 1, 4, 30, 0)
    peak_mid = datetime(2023, 1, 1, 6, 0, 0)
    peak_end = datetime(2023, 1, 1, 7, 29, 0)
    
    assert not in_execution_window(peak_start)
    assert not in_execution_window(peak_mid)
    assert not in_execution_window(peak_end)
    
    safe_time = datetime(2023, 1, 1, 3, 30, 0)
    assert in_execution_window(safe_time)


def test_pdn_satisfied():
    now = datetime(2023, 1, 2, 12, 0, 0)
    assert not pdn_satisfied(None, now)
    assert not pdn_satisfied(now - timedelta(hours=23), now)
    assert pdn_satisfied(now - timedelta(hours=24), now)
    assert pdn_satisfied(now - timedelta(hours=25), now)


def test_required_remedy():
    assert required_remedy(RootCause.MANDATE_ABSENT) == ActionType.REREGISTER_MANDATE
    assert required_remedy(RootCause.MANDATE_REVOKED) == ActionType.REREGISTER_MANDATE
    assert required_remedy(RootCause.MANDATE_CAP_EXCEEDED) == ActionType.AMEND_MANDATE_CAP
    assert required_remedy(RootCause.PDN_MISSING) == ActionType.SEND_PDN
    assert required_remedy(RootCause.AFA_THRESHOLD_BREACH) == ActionType.REREGISTER_MANDATE
    assert required_remedy(RootCause.EXECUTION_WINDOW_MISS) == ActionType.RETRY_PAYMENT
    assert required_remedy(RootCause.TRANSIENT_BANK_DECLINE) == ActionType.DO_NOTHING


def test_is_retry_futile():
    for cause in REGULATORY_FUTILE_CAUSES:
        assert is_retry_futile(cause)
    
    assert not is_retry_futile(RootCause.EXECUTION_WINDOW_MISS)
    assert not is_retry_futile(RootCause.TRANSIENT_BANK_DECLINE)


def test_attempts_remaining():
    assert attempts_remaining(0) == 4
    assert attempts_remaining(2) == 2
    assert attempts_remaining(4) == 0
    assert attempts_remaining(5) == 0
