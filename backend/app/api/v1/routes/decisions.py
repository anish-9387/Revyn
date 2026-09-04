"""Recovery Confidence Ledger: every automated decision, fully explained."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from app.api.deps import PaginationDep, SessionDep
from app.core.constants import ActionType, PolicyVerdict
from app.models.event import RevenueEvent
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
        select(Decision, RevenueEvent.external_ref, RevenueEvent.amount_paise)
        .join(RevenueEvent, RevenueEvent.id == Decision.event_id)
        .where(*filters)
        .order_by(Decision.created_at.desc())
        .limit(page.limit)
        .offset(page.offset)
    )
    rows = (await session.execute(stmt)).all()
    return Page(
        items=[
            DecisionRead.model_validate(row).model_copy(
                update={"event_ref": ref, "amount_paise": amount}
            )
            for row, ref, amount in rows
        ],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/{decision_id}")
async def explain_decision(session: SessionDep, decision_id: str) -> dict:
    """Why this action, what else was considered, and what the policy said."""
    row = (
        await session.execute(
            select(Decision, RevenueEvent.external_ref, RevenueEvent.amount_paise)
            .join(RevenueEvent, RevenueEvent.id == Decision.event_id)
            .where(Decision.id == decision_id)
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    decision, event_ref, amount_paise = row
    return {
        "decision": DecisionRead.model_validate(decision)
        .model_copy(update={"event_ref": event_ref, "amount_paise": amount_paise})
        .model_dump(mode="json"),
        "policy_explanations": explain(decision.policy_reasons),
        "considered": sorted(
            decision.alternatives, key=lambda option: option["expected_value_paise"], reverse=True
        ),
    }
