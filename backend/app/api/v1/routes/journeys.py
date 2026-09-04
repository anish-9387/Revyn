"""Adaptive recovery journeys and the controls a merchant has over them."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from app.api.deps import PaginationDep, SessionDep
from app.core.constants import JourneyState
from app.models.journey import RecoveryJourney
from app.schemas.common import Page
from app.schemas.read import ActionRead, DecisionRead, JourneyDetail, JourneyRead, RiskItem
from app.schemas.write import JourneyActionRequest
from app.services.orchestrator import orchestrator
from app.services.policy import BudgetState, load_engine

router = APIRouter(prefix="/journeys", tags=["journeys"])


@router.get("", response_model=Page[JourneyRead])
async def list_journeys(
    session: SessionDep, page: PaginationDep, state: JourneyState | None = None
) -> Page[JourneyRead]:
    filters = [RecoveryJourney.state == state] if state else []
    total = int(
        (await session.execute(select(func.count(RecoveryJourney.id)).where(*filters))).scalar()
        or 0
    )
    stmt = (
        select(RecoveryJourney)
        .where(*filters)
        .order_by(RecoveryJourney.created_at.desc())
        .limit(page.limit)
        .offset(page.offset)
    )
    journeys = (await session.execute(stmt)).unique().scalars().all()
    return Page(
        items=[_summarise(j) for j in journeys],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/{journey_id}", response_model=JourneyDetail)
async def get_journey(session: SessionDep, journey_id: str) -> JourneyDetail:
    journey = await _require(session, journey_id)
    engine = await load_engine(session)
    budget = engine.friction_budget(
        journey.event,
        BudgetState(
            contacts_used=journey.contacts_used,
            retries_used=journey.retries_used,
            discounts_used=journey.discounts_used,
            voice_used=journey.voice_used,
        ),
    )
    detail = JourneyDetail.model_validate(journey)
    detail.event = RiskItem.model_validate(journey.event)
    detail.actions = [ActionRead.model_validate(action) for action in journey.actions]
    detail.decisions = [DecisionRead.model_validate(d) for d in journey.decisions]
    detail.friction_budget = budget.as_dict()
    return detail


@router.post("/{journey_id}/pause", response_model=JourneyRead)
async def pause(session: SessionDep, journey_id: str, payload: JourneyActionRequest) -> JourneyRead:
    journey = await orchestrator.pause_journey(session, journey_id, actor=payload.actor)
    return _summarise(journey)


@router.post("/{journey_id}/resume", response_model=JourneyRead)
async def resume(
    session: SessionDep, journey_id: str, payload: JourneyActionRequest
) -> JourneyRead:
    journey = await orchestrator.resume_journey(session, journey_id, actor=payload.actor)
    return _summarise(journey)


@router.post("/{journey_id}/stop", response_model=JourneyRead)
async def stop(session: SessionDep, journey_id: str, payload: JourneyActionRequest) -> JourneyRead:
    journey = await orchestrator.close_journey(
        session, journey_id, actor=payload.actor, reason=payload.reason
    )
    return _summarise(journey)


def _summarise(journey: RecoveryJourney) -> JourneyRead:
    """Event and customer travel with the row; both relationships are eagerly loaded."""
    return JourneyRead.model_validate(journey).model_copy(
        update={
            "event_ref": journey.event.external_ref,
            "amount_paise": journey.event.amount_paise,
            "customer_name": journey.event.customer.name,
        }
    )


async def _require(session, journey_id: str) -> RecoveryJourney:
    journey = (
        (await session.execute(select(RecoveryJourney).where(RecoveryJourney.id == journey_id)))
        .unique()
        .scalar_one_or_none()
    )
    if journey is None:
        raise HTTPException(status_code=404, detail="Journey not found")
    return journey
