"""Recovery What-If Simulator."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import ApiKeyDep, SessionDep
from app.core.constants import Actor, AuditEvent
from app.engines import simulator as simulator_engine
from app.schemas.read import PolicyRead
from app.schemas.write import SimulationRequest
from app.services import audit
from app.services.policy import PolicySpec, get_active_policy

router = APIRouter(prefix="/simulator", tags=["simulator"])


@router.post("/what-if")
async def what_if(session: SessionDep, payload: SimulationRequest) -> dict:
    """Score the open book under a proposed policy without writing anything."""
    config = await get_active_policy(session)
    return await simulator_engine.run_what_if(
        session,
        current=PolicySpec.from_model(config),
        overrides=payload.overrides.model_dump(exclude_none=True),
        limit=payload.sample_limit,
    )


@router.post("/apply", response_model=PolicyRead)
async def apply_simulation(session: SessionDep, payload: SimulationRequest, _auth: ApiKeyDep = None) -> PolicyRead:  # type: ignore[assignment]
    """Promote a simulated policy to the live one."""
    config = await get_active_policy(session)
    changes = payload.overrides.model_dump(exclude_none=True)
    for field, value in changes.items():
        setattr(config, field, value)
    if changes:
        config.version += 1
    await audit.record(
        session,
        event_type=AuditEvent.POLICY_UPDATED,
        entity_type="policy_config",
        entity_id=config.id,
        summary=f"Simulated policy applied: {', '.join(changes) or 'no change'}",
        payload={"changes": changes, "version": config.version, "source": "simulator"},
        actor=Actor.HUMAN,
    )
    await session.refresh(config)
    return PolicyRead.model_validate(config)
