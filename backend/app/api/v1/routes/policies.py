"""Merchant policy, friction budget defaults and the recovery kill switch."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import ApiKeyDep, SessionDep
from app.core.constants import Actor, AuditEvent
from app.schemas.read import PolicyRead
from app.schemas.write import KillSwitchRequest, PolicyUpdate
from app.services import audit
from app.services.orchestrator import orchestrator
from app.services.policy import get_active_policy

router = APIRouter(prefix="/policies", tags=["policies"])


@router.get("/active", response_model=PolicyRead)
async def active(session: SessionDep) -> PolicyRead:
    return PolicyRead.model_validate(await get_active_policy(session))


@router.patch("/active", response_model=PolicyRead)
async def update(session: SessionDep, payload: PolicyUpdate, _auth: ApiKeyDep = None) -> PolicyRead:  # type: ignore[assignment]
    config = await get_active_policy(session)
    changes = payload.model_dump(exclude_none=True)
    for field, value in changes.items():
        setattr(config, field, value)
    if changes:
        config.version += 1
    await audit.record(
        session,
        event_type=AuditEvent.POLICY_UPDATED,
        entity_type="policy_config",
        entity_id=config.id,
        summary=f"Policy updated: {', '.join(changes) or 'no change'}",
        payload={"changes": changes, "version": config.version},
        actor=Actor.HUMAN,
    )
    # The server-side updated_at is expired by the flush, so read it back before serialising.
    await session.refresh(config)
    return PolicyRead.model_validate(config)


@router.post("/kill-switch")
async def kill_switch(session: SessionDep, payload: KillSwitchRequest, _auth: ApiKeyDep = None) -> dict:  # type: ignore[assignment]
    """Halts or resumes all recovery automation immediately."""
    return await orchestrator.set_kill_switch(session, enabled=payload.enabled, actor=payload.actor)
