"""End-to-end loop over a small synthetic dataset."""

from __future__ import annotations

import asyncio

import pytest

from app.core.constants import ActionStatus, Cohort, EventStatus, JourneyState
from app.engines import counterfactual
from app.integrations.razorpay.factory import simulator
from app.services import dashboard, ledger, seeding
from app.services.orchestrator import orchestrator
from app.services.policy import get_active_policy


@pytest.fixture
async def seeded(session):
    await seeding.seed(
        session,
        reset_first=True,
        customers=80,
        transactions=400,
        train_model=False,
        live_scale=0.12,
    )
    await session.commit()
    return session


async def drain(session, cycles: int = 12) -> dict:
    totals = {"executed": 0, "verified": 0, "recovered": 0, "closed": 0, "blocked": 0}
    for _ in range(cycles):
        report = (await orchestrator.tick(session, limit=400)).as_dict()
        await session.commit()
        for key in totals:
            totals[key] += report[key]
        await asyncio.sleep(0)
    return totals


async def test_scan_opens_journeys_and_respects_the_holdout(seeded):
    report = await orchestrator.scan(seeded, limit=200)
    await seeded.commit()
    assert report.scanned > 0
    assert report.journeys_started > 0
    assert report.held_out > 0, "control cohort must never be actioned"

    from sqlalchemy import select

    from app.models.event import RevenueEvent
    from app.models.journey import RecoveryJourney

    control_ids = {
        event_id
        for (event_id,) in (
            await seeded.execute(
                select(RevenueEvent.id).where(
                    RevenueEvent.cohort == Cohort.CONTROL, RevenueEvent.is_training.is_(False)
                )
            )
        ).all()
    }
    journey_event_ids = {
        event_id for (event_id,) in (await seeded.execute(select(RecoveryJourney.event_id))).all()
    }
    assert not (control_ids & journey_event_ids)


async def test_one_customer_is_never_owned_by_two_journeys(seeded):
    await orchestrator.scan(seeded, limit=200)
    await seeded.commit()

    from sqlalchemy import func, select

    from app.models.journey import RecoveryJourney

    stmt = (
        select(RecoveryJourney.customer_id, func.count(RecoveryJourney.id))
        .where(RecoveryJourney.state.not_in([JourneyState.CLOSED]))
        .group_by(RecoveryJourney.customer_id)
        .having(func.count(RecoveryJourney.id) > 1)
    )
    assert (await seeded.execute(stmt)).all() == []


async def test_loop_recovers_money_and_books_it_incrementally(seeded):
    await orchestrator.scan(seeded, limit=200)
    await seeded.commit()
    totals = await drain(seeded)

    assert totals["executed"] > 0
    assert totals["verified"] > 0

    summary = await ledger.totals(seeded)
    if totals["recovered"]:
        assert summary["gross_recovered_paise"] > 0
        assert summary["incremental_net_paise"] < summary["gross_recovered_paise"]
        assert summary["organic_estimate_paise"] > 0

    safety = await dashboard.safety_metrics(seeded)
    assert safety["duplicate_executions"] == 0


async def test_ambiguous_gateway_state_is_verified_not_retried(seeded):
    sim = simulator()
    sim.faults.timeouts_remaining = 3
    sim.faults.succeed_after_timeout = True

    await orchestrator.scan(seeded, limit=40)
    await seeded.commit()
    await drain(seeded, cycles=3)

    from sqlalchemy import select

    from app.models.audit import AuditLog
    from app.models.journey import RecoveryAction

    ambiguous = [
        row
        for row in (await seeded.execute(select(AuditLog))).scalars().all()
        if "ambiguous" in row.summary.lower()
    ]
    assert ambiguous, "an injected timeout should be recorded before anything else happens"

    executed = (
        (
            await seeded.execute(
                select(RecoveryAction).where(RecoveryAction.executed_at.is_not(None))
            )
        )
        .unique()
        .scalars()
        .all()
    )
    keys = [action.idempotency_key for action in executed]
    assert len(keys) == len(set(keys)), "a timeout must never produce a second charge"
    sim.faults.timeouts_remaining = 0


async def test_kill_switch_freezes_the_loop(seeded):
    await orchestrator.scan(seeded, limit=60)
    await seeded.commit()
    await orchestrator.set_kill_switch(seeded, enabled=False, actor="test")
    await seeded.commit()

    report = await orchestrator.tick(seeded, limit=200)
    assert report.executed == 0

    config = await get_active_policy(seeded)
    assert config.automation_enabled is False


async def test_approval_gate_holds_high_value_actions(seeded):
    # Drop the threshold so every gateway action in the sample needs sign-off.
    config = await get_active_policy(seeded)
    config.human_approval_amount_paise = 500_00
    await seeded.commit()

    await orchestrator.scan(seeded, limit=200)
    await seeded.commit()

    from sqlalchemy import select

    from app.models.journey import RecoveryAction

    pending = (
        (
            await seeded.execute(
                select(RecoveryAction).where(
                    RecoveryAction.status == ActionStatus.AWAITING_APPROVAL
                )
            )
        )
        .unique()
        .scalars()
        .all()
    )
    assert pending, "a threshold this low must produce approval requests"

    action = pending[0]
    assert action.blocked_reasons
    approved = await orchestrator.approve_action(seeded, action.id, approver="tester")
    await seeded.commit()
    assert ActionStatus(approved.status) is ActionStatus.APPROVED


async def test_control_cohort_produces_a_measurable_organic_rate(seeded):
    await orchestrator.scan(seeded, limit=200)
    await seeded.commit()
    await drain(seeded, cycles=4)

    rates = await counterfactual.cohort_organic_rates(seeded)
    assert rates.overall[1] > 0
    assert 0.0 <= rates.overall[0] <= 1.0

    comparison = await counterfactual.ab_comparison(seeded)
    assert comparison["control"]["customer_contacts"] == 0
    assert comparison["treatment"]["events"] > 0


async def test_events_never_end_up_both_recovered_and_open(seeded):
    await orchestrator.scan(seeded, limit=200)
    await seeded.commit()
    await drain(seeded, cycles=6)

    from sqlalchemy import select

    from app.models.event import RevenueEvent

    events = (
        (await seeded.execute(select(RevenueEvent).where(RevenueEvent.is_training.is_(False))))
        .unique()
        .scalars()
        .all()
    )
    for event in events:
        if event.status == EventStatus.RECOVERED:
            assert event.recovered_amount_paise > 0
            assert event.resolved_at is not None
        if event.status == EventStatus.AT_RISK:
            assert event.recovered_amount_paise == 0
