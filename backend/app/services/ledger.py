"""Incremental Recovery Ledger.

Books every recovery net of the organic estimate and the cost of getting it, so the headline
number a merchant sees is money that would not have arrived on its own.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ActionType, Actor, AuditEvent, Cohort
from app.core.money import format_inr
from app.engines import counterfactual
from app.models.event import RevenueEvent
from app.models.journey import RecoveryJourney
from app.models.ledger import LedgerEntry
from app.services import audit


async def book_recovery(
    session: AsyncSession,
    *,
    event: RevenueEvent,
    journey: RecoveryJourney | None,
    action: ActionType,
    gross_paise: int,
    cost_paise: int,
    model_organic_probability: float,
    cohort_rates: counterfactual.CohortRates | None = None,
) -> LedgerEntry:
    rates = cohort_rates or await counterfactual.cohort_organic_rates(session)
    organic_paise, organic_probability, method = counterfactual.organic_estimate(
        amount_paise=gross_paise,
        model_probability=model_organic_probability,
        cohort=rates,
        kind=event.kind,
    )
    incremental = gross_paise - organic_paise - cost_paise
    entry = LedgerEntry(
        event_id=event.id,
        journey_id=journey.id if journey else None,
        cohort=Cohort(event.cohort),
        action=action,
        gross_recovered_paise=gross_paise,
        organic_estimate_paise=organic_paise,
        cost_paise=cost_paise,
        incremental_net_paise=incremental,
        attribution_method=method,
        organic_probability=organic_probability,
        detail={
            "loss_class": str(event.kind),
            "cohort_sample": rates.rate_for(event.kind)[1],
            "model_organic_probability": round(model_organic_probability, 4),
        },
    )
    session.add(entry)
    await audit.record(
        session,
        event_type=AuditEvent.RECOVERY_BOOKED,
        entity_type="revenue_event",
        entity_id=event.id,
        summary=(
            f"Recovered {format_inr(gross_paise)}, incremental {format_inr(incremental)} "
            f"({method} attribution)"
        ),
        payload={
            "gross_paise": gross_paise,
            "organic_estimate_paise": organic_paise,
            "cost_paise": cost_paise,
            "incremental_net_paise": incremental,
            "attribution_method": str(method),
        },
        actor=Actor.SYSTEM,
    )
    await session.flush()
    return entry


async def totals(session: AsyncSession) -> dict:
    stmt = select(
        func.count(LedgerEntry.id),
        func.coalesce(func.sum(LedgerEntry.gross_recovered_paise), 0),
        func.coalesce(func.sum(LedgerEntry.organic_estimate_paise), 0),
        func.coalesce(func.sum(LedgerEntry.cost_paise), 0),
        func.coalesce(func.sum(LedgerEntry.incremental_net_paise), 0),
    )
    entries, gross, organic, cost, incremental = (await session.execute(stmt)).one()
    # NPCI stats
    npci_spent = 0
    futile = 0
    try:
        from app.models.journey import RecoveryJourney
        npci_spent = int((await session.execute(select(func.coalesce(func.sum(RecoveryJourney.npci_attempts_used), 0)))).scalar() or 0)
        futile = int((await session.execute(select(func.coalesce(func.sum(RecoveryJourney.futile_retries_prevented), 0)))).scalar() or 0)
    except Exception:
        pass
    return {
        "entries": int(entries or 0),
        "gross_recovered_paise": int(gross or 0),
        "organic_estimate_paise": int(organic or 0),
        "cost_paise": int(cost or 0),
        "incremental_net_paise": int(incremental or 0),
        "cost_per_recovery_paise": int(cost / entries) if entries else 0,
        "npci_attempts_spent": npci_spent,
        "futile_retries_prevented": futile,
        "mandates_saved": futile,
    }


async def by_action(session: AsyncSession) -> list[dict]:
    stmt = (
        select(
            LedgerEntry.action,
            func.count(LedgerEntry.id),
            func.coalesce(func.sum(LedgerEntry.gross_recovered_paise), 0),
            func.coalesce(func.sum(LedgerEntry.incremental_net_paise), 0),
            func.coalesce(func.sum(LedgerEntry.cost_paise), 0),
        )
        .group_by(LedgerEntry.action)
        .order_by(func.sum(LedgerEntry.incremental_net_paise).desc())
    )
    return [
        {
            "action": str(action),
            "recoveries": int(count or 0),
            "gross_recovered_paise": int(gross or 0),
            "incremental_net_paise": int(incremental or 0),
            "cost_paise": int(cost or 0),
        }
        for action, count, gross, incremental, cost in (await session.execute(stmt)).all()
    ]


async def recent(session: AsyncSession, limit: int = 40) -> list[LedgerEntry]:
    stmt = select(LedgerEntry).order_by(LedgerEntry.created_at.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())
