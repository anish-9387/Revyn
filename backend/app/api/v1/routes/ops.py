"""Operational endpoints: seeding, manual loop control, model and demo fault injection."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException

from app.api.deps import ApiKeyDep, SessionDep
from app.integrations.llm import get_reasoner
from app.integrations.razorpay.factory import simulator
from app.ml import train as trainer
from app.ml.predictor import model_metadata
from app.schemas.write import PromiseRequest, SeedRequest, TimeoutInjectionRequest
from app.services import seeding
from app.services.orchestrator import orchestrator
from app.workers.scheduler import scheduler

router = APIRouter(prefix="/ops", tags=["ops"])


@router.post("/seed")
async def seed(session: SessionDep, payload: SeedRequest, _auth: ApiKeyDep) -> dict:
    """Regenerate the synthetic merchant, refit the model and pre-score the live book."""
    return await seeding.seed(
        session,
        reset_first=payload.reset,
        customers=payload.customers,
        transactions=payload.transactions,
        train_model=payload.train_model,
    )


@router.post("/scan")
async def scan(session: SessionDep, limit: int = 40, _auth: ApiKeyDep = None) -> dict:  # type: ignore[assignment]
    return (await orchestrator.scan(session, limit=limit)).as_dict()


@router.post("/tick")
async def tick(session: SessionDep, limit: int | None = None, _auth: ApiKeyDep = None) -> dict:  # type: ignore[assignment]
    return (await orchestrator.tick(session, limit=limit)).as_dict()


@router.post("/cycle")
async def cycle(_auth: ApiKeyDep = None) -> dict:  # type: ignore[assignment]
    """One full detect-and-execute pass, the same work the scheduler does."""
    return await scheduler.run_once()


@router.get("/scheduler")
async def scheduler_status() -> dict:
    return scheduler.status()


@router.post("/scheduler/start")
async def scheduler_start(_auth: ApiKeyDep = None) -> dict:  # type: ignore[assignment]
    await scheduler.start()
    return scheduler.status()


@router.post("/scheduler/stop")
async def scheduler_stop(_auth: ApiKeyDep = None) -> dict:  # type: ignore[assignment]
    await scheduler.stop()
    return scheduler.status()


@router.get("/model")
async def model() -> dict:
    return {"metadata": model_metadata(), "artifact_age_hours": trainer.artifact_age_hours()}


@router.post("/model/train")
async def retrain(session: SessionDep, _auth: ApiKeyDep = None) -> dict:  # type: ignore[assignment]
    return await trainer.train(session)


@router.post("/inject-timeout")
async def inject_timeout(payload: TimeoutInjectionRequest, _auth: ApiKeyDep = None) -> dict:  # type: ignore[assignment]
    """Arm the graceful-failure demo on the simulated gateway."""
    sim = simulator()
    if sim is None:
        raise HTTPException(
            status_code=409, detail="Fault injection is only available on the simulated gateway"
        )
    sim.faults.timeouts_remaining = payload.count
    sim.faults.succeed_after_timeout = payload.payment_already_succeeded
    return {
        "timeouts_armed": sim.faults.timeouts_remaining,
        "payment_already_succeeded": sim.faults.succeed_after_timeout,
    }


@router.post("/extract-promise")
async def extract_promise(payload: PromiseRequest) -> dict:
    """Promise-to-pay intelligence over a raw customer utterance."""
    reasoner = get_reasoner()
    result = await reasoner.extract_promise(payload.transcript, {"today": date.today().isoformat()})
    return {
        "provider": reasoner.name,
        "result": result.model_dump() if result else None,
    }
