"""Recovery Confidence Ledger: every automated decision, fully explained."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from app.api.deps import PaginationDep, SessionDep
from app.core.constants import ActionType, PolicyVerdict
from app.models.journey import Decision
from app.schemas.common import Page
from app.schemas.read import DecisionRead
from app.services.policy import explain

router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.get("", response_model=Page[DecisionRead])
async def list_decisions(
    session: SessionDep,
    page: PaginationDep,
    action: ActionType | None = None,
    verdict: PolicyVerdict | None = None,
) -> Page[DecisionRead]:
    filters = []
    if action:
        filters.append(Decision.chosen_action == action)
    if verdict:
        filters.append(Decision.policy_verdict == verdict)
    total = int(
        (await session.execute(select(func.count(Decision.id)).where(*filters))).scalar() or 0
    )
    stmt = (
        select(Decision)
        .where(*filters)
        .order_by(Decision.created_at.desc())
        .limit(page.limit)
        .offset(page.offset)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return Page(
        items=[DecisionRead.model_validate(row) for row in rows],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/{decision_id}")
async def explain_decision(session: SessionDep, decision_id: str) -> dict:
    """Why this action, what else was considered, and what the policy said."""
    decision = (
        await session.execute(select(Decision).where(Decision.id == decision_id))
    ).scalar_one_or_none()
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    return {
        "decision": DecisionRead.model_validate(decision).model_dump(mode="json"),
        "policy_explanations": explain(decision.policy_reasons),
        "considered": sorted(
            decision.alternatives, key=lambda option: option["expected_value_paise"], reverse=True
        ),
    }
