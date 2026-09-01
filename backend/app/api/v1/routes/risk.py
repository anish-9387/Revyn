"""Revenue Risk Radar."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from app.api.deps import PaginationDep, SessionDep
from app.core.constants import EventKind, EventStatus, JourneyState, RootCause
from app.models.event import RevenueEvent
from app.models.journey import Decision, RecoveryJourney
from app.schemas.common import Page
from app.schemas.read import DecisionRead, RiskItem

router = APIRouter(prefix="/risk", tags=["risk"])

OPEN_STATUSES = (EventStatus.AT_RISK, EventStatus.IN_RECOVERY, EventStatus.SUPPRESSED)


@router.get("", response_model=Page[RiskItem])
async def list_risk(
    session: SessionDep,
    page: PaginationDep,
    kind: EventKind | None = None,
    status: EventStatus | None = None,
    root_cause: RootCause | None = None,
    min_amount_paise: int = Query(default=0, ge=0),
    order_by: str = Query(default="priority", pattern="^(priority|amount|risk|recent)$"),
) -> Page[RiskItem]:
    """Ranked queue of money at risk, highest business value first."""
    filters = [RevenueEvent.is_training.is_(False)]
    filters.append(
        RevenueEvent.status == status if status else RevenueEvent.status.in_(OPEN_STATUSES)
    )
    if kind:
        filters.append(RevenueEvent.kind == kind)
    if root_cause:
        filters.append(RevenueEvent.root_cause == root_cause)
    if min_amount_paise:
        filters.append(RevenueEvent.amount_paise >= min_amount_paise)

    ordering = {
        "priority": (RevenueEvent.priority_score.desc(), RevenueEvent.amount_paise.desc()),
        "amount": (RevenueEvent.amount_paise.desc(),),
        "risk": (RevenueEvent.risk_score.desc(),),
        "recent": (RevenueEvent.occurred_at.desc(),),
    }[order_by]

    total = int(
        (await session.execute(select(func.count(RevenueEvent.id)).where(*filters))).scalar() or 0
    )
    stmt = (
        select(RevenueEvent)
        .where(*filters)
        .order_by(*ordering)
        .limit(page.limit)
        .offset(page.offset)
    )
    events = (await session.execute(stmt)).unique().scalars().all()
    journeys = await _journeys_for(session, [event.id for event in events])

    items = []
    for event in events:
        item = RiskItem.model_validate(event)
        journey = journeys.get(event.id)
        if journey is not None:
            item.journey_id = journey.id
            item.journey_state = JourneyState(journey.state)
        items.append(item)
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.get("/{event_id}", response_model=RiskItem)
async def get_risk_item(session: SessionDep, event_id: str) -> RiskItem:
    event = (
        (await session.execute(select(RevenueEvent).where(RevenueEvent.id == event_id)))
        .unique()
        .scalar_one_or_none()
    )
    if event is None:
        raise HTTPException(status_code=404, detail="Revenue event not found")
    item = RiskItem.model_validate(event)
    journeys = await _journeys_for(session, [event.id])
    if journey := journeys.get(event.id):
        item.journey_id = journey.id
        item.journey_state = JourneyState(journey.state)
    return item


@router.get("/{event_id}/decisions", response_model=list[DecisionRead])
async def event_decisions(session: SessionDep, event_id: str) -> list[DecisionRead]:
    stmt = (
        select(Decision).where(Decision.event_id == event_id).order_by(Decision.created_at.desc())
    )
    return [
        DecisionRead.model_validate(row) for row in (await session.execute(stmt)).scalars().all()
    ]


async def _journeys_for(session, event_ids: list[str]) -> dict[str, RecoveryJourney]:
    if not event_ids:
        return {}
    stmt = (
        select(RecoveryJourney)
        .where(RecoveryJourney.event_id.in_(event_ids))
        .order_by(RecoveryJourney.created_at.desc())
    )
    result: dict[str, RecoveryJourney] = {}
    for journey in (await session.execute(stmt)).unique().scalars().all():
        result.setdefault(journey.event_id, journey)
    return result
