"""Merchant command centre."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import SessionDep
from app.services import dashboard

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview")
async def overview(session: SessionDep) -> dict:
    """Everything the top of the dashboard needs in one round trip."""
    return await dashboard.overview(session)


@router.get("/activity")
async def activity(session: SessionDep, limit: int = Query(default=25, ge=1, le=100)) -> dict:
    return {"items": await dashboard.recent_activity(session, limit=limit)}


@router.get("/safety")
async def safety(session: SessionDep) -> dict:
    return await dashboard.safety_metrics(session)
