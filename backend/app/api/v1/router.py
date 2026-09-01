"""API v1 router assembly."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes import (
    approvals,
    audit,
    dashboard,
    decisions,
    health,
    insights,
    journeys,
    ledger,
    ops,
    policies,
    risk,
    simulator,
)

api_router = APIRouter()
for module in (
    health,
    dashboard,
    risk,
    journeys,
    decisions,
    approvals,
    policies,
    simulator,
    ledger,
    insights,
    audit,
    ops,
):
    api_router.include_router(module.router)
