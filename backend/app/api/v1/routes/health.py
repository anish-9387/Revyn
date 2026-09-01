"""Liveness and readiness."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import SessionDep
from app.core.config import settings
from app.integrations.llm import get_reasoner
from app.integrations.razorpay import get_gateway
from app.ml.predictor import model_metadata
from app.models.event import RevenueEvent
from app.workers.scheduler import scheduler

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "environment": settings.env}


@router.get("/health/ready")
async def ready(session: SessionDep) -> dict:
    seeded = (await session.execute(select(RevenueEvent.id).limit(1))).first() is not None
    return {
        "status": "ok",
        "database": "connected",
        "seeded": seeded,
        "gateway": get_gateway().name,
        "reasoning_provider": get_reasoner().name,
        "model": model_metadata(),
        "scheduler": scheduler.status(),
    }
