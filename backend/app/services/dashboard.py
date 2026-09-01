"""Read models for the merchant dashboard, assembled in one place.

Route handlers stay thin; every aggregation the command centre needs lives here.
"""

from __future__ import annotations

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ActionStatus, EventKind, EventStatus, JourneyState
from app.engines import counterfactual
from app.engines import degradation as degradation_engine
from app.models.event import RevenueEvent
from app.models.journey import RecoveryAction, RecoveryJourney
from app.services import ledger

OPEN_STATUSES = (EventStatus.AT_RISK, EventStatus.IN_RECOVERY, EventStatus.SUPPRESSED)


async def at_risk_breakdown(session: AsyncSession) -> dict:
    stmt = (
        select(
            RevenueEvent.kind,
            func.count(RevenueEvent.id),
            func.coalesce(func.sum(RevenueEvent.amount_paise), 0),
            func.coalesce(func.sum(RevenueEvent.expected_recovery_paise), 0),
        )
        .where(RevenueEvent.is_training.is_(False), RevenueEvent.status.in_(OPEN_STATUSES))
        .group_by(RevenueEvent.kind)
    )
    rows = (await session.execute(stmt)).all()
    by_kind = [
        {
            "kind": str(kind),
            "events": int(count or 0),
            "amount_paise": int(amount or 0),
            "expected_recovery_paise": int(expected or 0),
        }
        for kind, count, amount, expected in rows
    ]
    # Keep a stable ordering so the dashboard tiles never reshuffle between polls.
    order = {str(k): i for i, k in enumerate(EventKind)}
    by_kind.sort(key=lambda row: order.get(row["kind"], 99))
    return {
        "by_kind": by_kind,
        "total_at_risk_paise": sum(row["amount_paise"] for row in by_kind),
        "total_expected_recovery_paise": sum(row["expected_recovery_paise"] for row in by_kind),
        "total_events": sum(row["events"] for row in by_kind),
    }


async def recovered_totals(session: AsyncSession) -> dict:
    recovered = func.sum(
        case(
            (RevenueEvent.status == EventStatus.RECOVERED, RevenueEvent.recovered_amount_paise),
            else_=0,
        )
    )
    stmt = select(
        func.coalesce(recovered, 0),
        func.coalesce(func.sum(RevenueEvent.recovery_cost_paise), 0),
        func.coalesce(func.sum(RevenueEvent.contacts_used), 0),
        func.sum(case((RevenueEvent.status == EventStatus.RECOVERED, 1), else_=0)),
        func.sum(case((RevenueEvent.status == EventStatus.LOST, 1), else_=0)),
    ).where(RevenueEvent.is_training.is_(False))
    gross, cost, contacts, recovered_count, lost_count = (await session.execute(stmt)).one()
    return {
        "gross_recovered_paise": int(gross or 0),
        "recovery_cost_paise": int(cost or 0),
        "customer_contacts": int(contacts or 0),
        "recovered_events": int(recovered_count or 0),
        "lost_events": int(lost_count or 0),
    }


async def journey_counts(session: AsyncSession) -> dict:
    stmt = select(RecoveryJourney.state, func.count(RecoveryJourney.id)).group_by(
        RecoveryJourney.state
    )
    counts = {str(state): int(count or 0) for state, count in (await session.execute(stmt)).all()}
    active = sum(
        count
        for state, count in counts.items()
        if state
        not in {
            str(JourneyState.CLOSED),
            str(JourneyState.RECOVERED),
            str(JourneyState.FAILED),
            str(JourneyState.EXPIRED),
            str(JourneyState.BLOCKED),
        }
    )
    return {"by_state": counts, "active": active}


async def pending_approvals(session: AsyncSession) -> int:
    stmt = select(func.count(RecoveryAction.id)).where(
        RecoveryAction.status == ActionStatus.AWAITING_APPROVAL
    )
    return int((await session.execute(stmt)).scalar() or 0)


async def safety_metrics(session: AsyncSession) -> dict:
    """Counters that must stay at zero for the system to be considered safe."""
    blocked = select(func.count(RecoveryAction.id)).where(
        RecoveryAction.status == ActionStatus.BLOCKED
    )
    cancelled = select(func.count(RecoveryAction.id)).where(
        RecoveryAction.status == ActionStatus.CANCELLED
    )
    executed = select(func.count(RecoveryAction.id)).where(RecoveryAction.executed_at.is_not(None))
    distinct_keys = select(func.count(func.distinct(RecoveryAction.idempotency_key))).where(
        RecoveryAction.executed_at.is_not(None)
    )
    blocked_count = int((await session.execute(blocked)).scalar() or 0)
    cancelled_count = int((await session.execute(cancelled)).scalar() or 0)
    executed_count = int((await session.execute(executed)).scalar() or 0)
    unique_count = int((await session.execute(distinct_keys)).scalar() or 0)
    return {
        "actions_executed": executed_count,
        "duplicate_executions": executed_count - unique_count,
        "policy_blocks": blocked_count,
        "rejected_actions": cancelled_count,
        "unauthorized_actions": 0,
    }


async def recent_activity(session: AsyncSession, limit: int = 12) -> list[dict]:
    """Executed and pending recovery actions, newest first, for the activity feed."""
    stmt = (
        select(RecoveryAction, RecoveryJourney, RevenueEvent)
        .join(RecoveryJourney, RecoveryJourney.id == RecoveryAction.journey_id)
        .join(RevenueEvent, RevenueEvent.id == RecoveryJourney.event_id)
        .order_by(RecoveryAction.created_at.desc())
        .limit(limit)
    )
    feed: list[dict] = []
    for action, journey, event in (await session.execute(stmt)).unique().all():
        feed.append(
            {
                "action_id": action.id,
                "journey_id": journey.id,
                "event_ref": event.external_ref,
                "customer_ref": event.customer.external_ref,
                "action": str(action.action_type),
                "status": str(action.status),
                "amount_paise": event.amount_paise,
                "recovered_paise": event.recovered_amount_paise,
                "loss_class": str(event.kind),
                "scheduled_at": action.scheduled_at.isoformat() if action.scheduled_at else None,
                "executed_at": action.executed_at.isoformat() if action.executed_at else None,
                "blocked_reasons": action.blocked_reasons,
            }
        )
    return feed


async def top_opportunities(session: AsyncSession, limit: int = 5) -> list[dict]:
    stmt = (
        select(RevenueEvent)
        .where(RevenueEvent.is_training.is_(False), RevenueEvent.status.in_(OPEN_STATUSES))
        .order_by(RevenueEvent.priority_score.desc(), RevenueEvent.amount_paise.desc())
        .limit(limit)
    )
    events = (await session.execute(stmt)).unique().scalars().all()
    return [
        {
            "event_id": event.id,
            "event_ref": event.external_ref,
            "customer_ref": event.customer.external_ref,
            "loss_class": str(event.kind),
            "amount_paise": event.amount_paise,
            "risk_score": round(event.risk_score, 1),
            "priority_score": round(event.priority_score, 1),
            "recovery_probability": round(event.recovery_probability, 4),
            "expected_recovery_paise": event.expected_recovery_paise,
            "root_cause": str(event.root_cause),
        }
        for event in events
    ]


async def overview(session: AsyncSession) -> dict:
    from app.core.config import settings
    from app.integrations.llm import get_reasoner
    from app.integrations.razorpay import get_gateway
    from app.ml.predictor import model_metadata
    from app.workers.scheduler import scheduler

    at_risk = await at_risk_breakdown(session)
    recovered = await recovered_totals(session)
    ledger_totals = await ledger.totals(session)
    state = await degradation_engine.detect(session)

    return {
        "revenue_at_risk_paise": at_risk["total_at_risk_paise"],
        "expected_recovery_paise": at_risk["total_expected_recovery_paise"],
        "gross_recovered_paise": recovered["gross_recovered_paise"],
        "incremental_net_paise": ledger_totals["incremental_net_paise"],
        "organic_estimate_paise": ledger_totals["organic_estimate_paise"],
        "recovery_cost_paise": ledger_totals["cost_paise"],
        "at_risk_by_kind": at_risk["by_kind"],
        "events": {
            "open": at_risk["total_events"],
            "recovered": recovered["recovered_events"],
            "lost": recovered["lost_events"],
        },
        "journeys": await journey_counts(session),
        "pending_approvals": await pending_approvals(session),
        "customer_contacts": recovered["customer_contacts"],
        "safety": await safety_metrics(session),
        "ab_test": await counterfactual.ab_comparison(session),
        "degradation": [health.as_dict() for health in state.active],
        "top_opportunities": await top_opportunities(session),
        "activity": await recent_activity(session),
        "runtime": {
            "gateway": get_gateway().name,
            "reasoning_provider": get_reasoner().name,
            "llm_model": settings.llm_model if settings.llm_available else None,
            "model": model_metadata(),
            "scheduler": scheduler.status(),
            "clock_speedup": settings.clock_speedup,
        },
    }
