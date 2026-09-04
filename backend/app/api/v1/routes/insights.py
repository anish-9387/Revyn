"""Revenue leakage graph, merchant playbook and systemic degradation."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.deps import SessionDep
from app.engines import degradation as degradation_engine
from app.engines import leakage, learning
from app.models.insight import DegradationWindow
from app.schemas.read import DegradationRead

router = APIRouter(tags=["insights"])


@router.get("/leakage/graph")
async def leakage_graph(session: SessionDep) -> dict:
    """Where revenue is leaking, sliced along every dimension a merchant can act on."""
    return await leakage.build_graph(session)


@router.get("/leakage/insights")
async def leakage_insights(session: SessionDep) -> dict:
    return await leakage.insights(session)


@router.get("/playbook")
async def playbook(session: SessionDep) -> dict:
    """Merchant recovery memory: the best-known action per recovery context."""
    return {
        "entries": await learning.playbook(session),
        "min_trials_for_confidence": learning.MIN_TRIALS_FOR_CONFIDENCE,
    }


@router.get("/degradation", response_model=list[DegradationRead])
async def degradation_windows(session: SessionDep) -> list[DegradationRead]:
    stmt = select(DegradationWindow).order_by(
        DegradationWindow.status, DegradationWindow.detected_at.desc()
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [DegradationRead.model_validate(row) for row in rows]


@router.get("/degradation/live")
async def degradation_live(session: SessionDep) -> dict:
    """Current failure-rate picture per route and per method."""
    state = await degradation_engine.detect(session)
    return {
        "routes": [health.as_dict() for health in state.routes.values()],
        "methods": [health.as_dict() for health in state.methods.values()],
        "active": [health.as_dict() for health in state.active],
        "window_minutes": degradation_engine.RECENT_WINDOW_MINUTES,
        "min_attempts": degradation_engine.MIN_RECENT_ATTEMPTS,
    }


@router.get("/degradation/series")
async def degradation_series(
    session: SessionDep,
    value: str = Query(..., description="Route or payment-method name to chart"),
    scope: Literal["route", "method"] = Query(default="route"),
    hours: int = Query(default=6, ge=1, le=48),
) -> dict:
    """Failure-rate history for one scope, charted against the baseline the detector used."""
    return {
        "scope": scope,
        "value": value,
        "points": await degradation_engine.failure_rate_series(
            session, value, scope=scope, hours=hours
        ),
    }
