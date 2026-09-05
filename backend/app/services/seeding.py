"""Synthetic dataset provisioning.

Generates the merchant, fits the recovery model on the resulting history, bootstraps the
playbook and pre-scores the live book so the dashboard opens with real numbers before the
orchestrator has acted on anything.
"""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import RecoveryContext
from app.agents.pipeline import RecoveryPipeline
from app.core.config import settings
from app.core.constants import Actor, AuditEvent
from app.core.logging import get_logger
from app.data import generator
from app.engines import degradation as degradation_engine
from app.engines import learning
from app.ml import train as trainer
from app.models.audit import AuditLog
from app.models.customer import Customer
from app.models.event import RevenueEvent
from app.models.insight import DegradationWindow, RouteHealthBucket, StrategyStat
from app.models.journey import Decision, RecoveryAction, RecoveryJourney
from app.models.ledger import LedgerEntry
from app.models.mandate import Mandate
from app.services import audit
from app.services.policy import BudgetState, load_engine

log = get_logger(__name__)

# Child rows first so foreign keys stay satisfied on databases that enforce them.
RESET_ORDER = (
    LedgerEntry,
    RecoveryAction,
    Decision,
    RecoveryJourney,
    AuditLog,
    StrategyStat,
    DegradationWindow,
    RouteHealthBucket,
    RevenueEvent,
    Mandate,
    Customer,
)


async def reset(session: AsyncSession) -> None:
    for model in RESET_ORDER:
        await session.execute(delete(model))
    await session.flush()


async def seed(
    session: AsyncSession,
    *,
    reset_first: bool = True,
    customers: int | None = None,
    transactions: int | None = None,
    train_model: bool = True,
    live_scale: float = 1.0,
) -> dict:
    from app.core.cache import get_keystore

    if reset_first:
        await reset(session)
        keystore = get_keystore()
        await keystore.close()

    customer_count = customers or settings.synthetic_customers
    history_count = transactions or settings.synthetic_transactions
    dataset, buckets, (degradation_start, degradation_end) = generator.generate(
        seed=settings.seed,
        customer_count=customer_count,
        history_count=history_count,
        live_scale=live_scale,
    )

    session.add_all(dataset.customers)
    await session.flush()
    # Create mandates for ~45% of customers now that IDs exist
    import random as _random
    from datetime import timedelta as _td

    from app.core.constants import MandateRail, MandateStatus
    rng2 = _random.Random(settings.seed + 1)
    now2 = dataset.events[0].occurred_at if dataset.events else None
    # Use current time for mandate timestamps
    from app.core.clock import utcnow as _utcnow

    _now = _utcnow()
    mandates: list[Mandate] = []
    mandat_by_customer: dict[str, Mandate] = {}
    seq = 700000
    for cust in dataset.customers:
        if rng2.random() < 0.45:
            rail = rng2.choice([MandateRail.UPI_AUTOPAY, MandateRail.CARD_EMANDATE, MandateRail.NACH])
            status = MandateStatus.ACTIVE if rng2.random() < 0.85 else rng2.choice([MandateStatus.REVOKED, MandateStatus.PAUSED])
            cap = rng2.choice([5_000_00, 10_000_00, 15_000_00, 50_000_00])
            m = Mandate(
                customer_id=cust.id,
                external_ref=f"MND{seq:07d}",
                rail=rail,
                status=status,
                max_amount_paise=cap,
                sequence_number=rng2.randint(1, 3),
                attempts_used=rng2.randint(0, 2),
                last_pdn_sent_at=_now - _td(hours=rng2.randint(5, 48)) if rng2.random() < 0.7 else None,
                registered_at=_now - _td(days=rng2.randint(10, 400)),
                revoked_at=_now - _td(days=rng2.randint(1, 10)) if status == MandateStatus.REVOKED else None,
            )
            seq += 1
            mandates.append(m)
            mandat_by_customer[cust.id] = m
    if mandates:
        session.add_all(mandates)
        await session.flush()
        # Link subscription/payment events to mandates where applicable
        for ev in dataset.events:
            if ev.kind in ("subscription_failure", "payment_failure") and ev.customer_id in mandat_by_customer:
                if rng2.random() < 0.6:
                    ev.mandate_id = mandat_by_customer[ev.customer_id].id
    session.add_all(dataset.events)
    session.add_all([RouteHealthBucket(**bucket) for bucket in buckets])
    await session.flush()

    training_result = await trainer.train(session) if train_model else {"trained": False}
    contexts = await learning.bootstrap(session)

    state = await degradation_engine.detect(session)
    await degradation_engine.reconcile_windows(session, state)
    prescored = await prescore(session)

    live = dataset.live_events
    summary = {
        "customers": len(dataset.customers),
        "events": len(dataset.events),
        "training_events": len(dataset.events) - len(live),
        "live_events": len(live),
        "route_health_buckets": len(buckets),
        "playbook_contexts": contexts,
        "prescored_events": prescored,
        "revenue_at_risk_paise": sum(event.amount_paise for event in live),
        "degradation_window": {
            "route": generator.DEGRADED_ROUTE,
            "start": degradation_start.isoformat(),
            "end": degradation_end.isoformat(),
            "detected": [health.as_dict() for health in state.active],
        },
        "model": training_result,
    }
    await audit.record(
        session,
        event_type=AuditEvent.EVENT_DETECTED,
        entity_type="dataset",
        entity_id="synthetic",
        summary=f"Seeded {summary['events']} events for {summary['customers']} customers",
        payload={k: v for k, v in summary.items() if k != "model"},
        actor=Actor.SYSTEM,
    )
    log.info("seeding.completed", extra=summary)
    return summary


async def prescore(session: AsyncSession) -> int:
    """Run the planning agents over the live book without opening journeys."""
    pipeline = RecoveryPipeline()
    policy = await load_engine(session)
    state = await degradation_engine.detect(session)
    stmt = select(RevenueEvent).where(RevenueEvent.is_training.is_(False))
    events = (await session.execute(stmt)).unique().scalars().all()

    for event in events:
        ctx = RecoveryContext(
            session=session,
            event=event,
            customer=event.customer,
            policy=policy,
            degradation=state,
            budget=BudgetState(),
            allow_reasoner=False,
        )
        await pipeline.plan(ctx)
    await session.flush()
    return len(events)
