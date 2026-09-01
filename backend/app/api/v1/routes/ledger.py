"""Incremental Recovery Ledger and the control-versus-Revyn comparison."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import SessionDep
from app.engines import counterfactual
from app.schemas.read import LedgerEntryRead
from app.services import ledger as ledger_service

router = APIRouter(prefix="/ledger", tags=["ledger"])


@router.get("/summary")
async def summary(session: SessionDep) -> dict:
    totals = await ledger_service.totals(session)
    cohort = await counterfactual.cohort_organic_rates(session)
    return {
        **totals,
        "by_action": await ledger_service.by_action(session),
        "cohort_organic_rates": {
            "by_kind": {
                kind: {"rate": rate, "sample": sample}
                for kind, (rate, sample) in cohort.by_kind.items()
            },
            "overall": {"rate": cohort.overall[0], "sample": cohort.overall[1]},
        },
    }


@router.get("/entries", response_model=list[LedgerEntryRead])
async def entries(
    session: SessionDep, limit: int = Query(default=50, ge=1, le=200)
) -> list[LedgerEntryRead]:
    rows = await ledger_service.recent(session, limit=limit)
    return [LedgerEntryRead.model_validate(row) for row in rows]


@router.get("/ab-test")
async def ab_test(session: SessionDep) -> dict:
    """Control holdout against the Revyn-managed cohort on the same population."""
    return await counterfactual.ab_comparison(session)
