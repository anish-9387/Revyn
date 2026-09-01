"""Agent 1 - Sentinel. Scores revenue at risk and decides what is worth pursuing."""

from __future__ import annotations

import time

from app.agents.base import RecoveryContext
from app.core.constants import AgentName, EventStatus
from app.core.money import format_inr
from app.engines import risk as risk_engine

# Opportunities below this are noise: the cheapest contact costs more than the upside.
DUST_FLOOR_PAISE = 200_00


class Sentinel:
    name = AgentName.SENTINEL

    async def run(self, ctx: RecoveryContext) -> None:
        started = time.perf_counter()
        assessment = risk_engine.assess(ctx.event, ctx.customer, now=ctx.now)
        ctx.risk = assessment
        ctx.event.risk_score = assessment.risk_score
        ctx.event.urgency_score = assessment.urgency

        if ctx.event.status == EventStatus.RECOVERED:
            ctx.worth_pursuing = False
            ctx.skip_reason = "Payment already succeeded"
        elif ctx.event.amount_paise < DUST_FLOOR_PAISE:
            ctx.worth_pursuing = False
            ctx.skip_reason = f"Amount {format_inr(ctx.event.amount_paise)} is below the dust floor"
        elif ctx.customer.opted_out and ctx.event.retry_count >= ctx.policy.spec.max_retries:
            ctx.worth_pursuing = False
            ctx.skip_reason = "Customer opted out and no silent action remains"

        ctx.trace.add(
            self.name,
            f"{format_inr(ctx.event.amount_paise)} at risk, risk {assessment.risk_score:.0f}/100",
            {
                **assessment.as_dict(),
                "worth_pursuing": ctx.worth_pursuing,
                "skip_reason": ctx.skip_reason,
            },
            started,
        )
