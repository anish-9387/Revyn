"""Human-in-the-loop approval queue for high-risk actions."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import SessionDep
from app.core.constants import ActionStatus
from app.models.journey import Decision, RecoveryAction
from app.schemas.read import ActionRead, ApprovalItem, DecisionRead, RiskItem
from app.schemas.write import ApprovalRequest, RejectionRequest
from app.services.orchestrator import orchestrator
from app.services.policy import explain

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("", response_model=list[ApprovalItem])
async def pending(session: SessionDep) -> list[ApprovalItem]:
    stmt = (
        select(RecoveryAction)
        .where(RecoveryAction.status == ActionStatus.AWAITING_APPROVAL)
        .order_by(RecoveryAction.created_at)
    )
    actions = (await session.execute(stmt)).unique().scalars().all()
    items: list[ApprovalItem] = []
    for action in actions:
        decision = None
        if action.decision_id:
            decision = (
                await session.execute(select(Decision).where(Decision.id == action.decision_id))
            ).scalar_one_or_none()
        items.append(
            ApprovalItem(
                action=ActionRead.model_validate(action),
                journey_id=action.journey_id,
                event=RiskItem.model_validate(action.journey.event),
                reasons=action.blocked_reasons,
                explanations=explain(action.blocked_reasons),
                decision=DecisionRead.model_validate(decision) if decision else None,
            )
        )
    return items


@router.post("/{action_id}/approve", response_model=ActionRead)
async def approve(session: SessionDep, action_id: str, payload: ApprovalRequest) -> ActionRead:
    action = await orchestrator.approve_action(
        session, action_id, approver=payload.approver, note=payload.note
    )
    return ActionRead.model_validate(action)


@router.post("/{action_id}/reject", response_model=ActionRead)
async def reject(session: SessionDep, action_id: str, payload: RejectionRequest) -> ActionRead:
    action = await orchestrator.reject_action(
        session, action_id, approver=payload.approver, reason=payload.reason
    )
    return ActionRead.model_validate(action)
