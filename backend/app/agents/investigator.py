"""Agent 2 - Investigator. Determines why the revenue is slipping.

A deterministic Bayesian pass produces the diagnosis. The reasoning provider may then
refine it, but only within the candidate set the deterministic pass produced - a cause it
did not consider can never be introduced here.
"""

from __future__ import annotations

import time

from app.agents.base import RecoveryContext
from app.core.constants import AgentName, RootCause
from app.core.logging import get_logger
from app.engines import root_cause as investigator_engine
from app.integrations.llm import get_reasoner

log = get_logger(__name__)

# The model must clear this bar before its confidence replaces the deterministic estimate.
MIN_LLM_CONFIDENCE = 0.35


class Investigator:
    name = AgentName.INVESTIGATOR

    async def run(self, ctx: RecoveryContext) -> None:
        started = time.perf_counter()
        diagnosis = investigator_engine.investigate(
            ctx.event, ctx.customer, ctx.systemic_signal, now=ctx.now
        )
        refined_by = "deterministic"

        reasoner = get_reasoner()
        narrative = (
            await reasoner.diagnose(self._context(ctx, diagnosis)) if ctx.allow_reasoner else None
        )
        if narrative is not None:
            allowed = {str(candidate.cause) for candidate in diagnosis.candidates}
            if narrative.cause in allowed and narrative.confidence >= MIN_LLM_CONFIDENCE:
                diagnosis.cause = RootCause(narrative.cause)
                diagnosis.confidence = narrative.confidence
                diagnosis.narrative = narrative.explanation
                diagnosis.evidence = [*diagnosis.evidence, *narrative.evidence][:6]
                refined_by = reasoner.name
            else:
                log.info(
                    "investigator.llm_rejected",
                    extra={"proposed": narrative.cause, "confidence": narrative.confidence},
                )

        ctx.diagnosis = diagnosis
        ctx.reasoning_provider = refined_by
        ctx.event.root_cause = diagnosis.cause
        ctx.event.cause_layer = diagnosis.layer
        ctx.event.cause_confidence = diagnosis.confidence
        ctx.event.diagnosis = {
            **diagnosis.as_dict(),
            "degradation_active": ctx.degraded_route,
            "degradation_ratio": ctx.systemic_signal.route_ratio,
            "refined_by": refined_by,
        }

        ctx.trace.add(
            self.name,
            f"{diagnosis.label} at {diagnosis.confidence:.0%} confidence",
            {
                "cause": str(diagnosis.cause),
                "layer": str(diagnosis.layer),
                "refined_by": refined_by,
                "evidence": diagnosis.evidence,
                "candidates": [
                    {"cause": str(c.cause), "probability": round(c.probability, 3)}
                    for c in diagnosis.candidates
                ],
            },
            started,
        )

    @staticmethod
    def _context(ctx: RecoveryContext, diagnosis) -> dict:
        from app.core.money import paise_to_rupees

        return {
            "loss_class": str(ctx.event.kind),
            "amount_rupees": round(paise_to_rupees(ctx.event.amount_paise), 2),
            "payment_method": str(ctx.event.payment_method),
            "issuer": ctx.event.issuer,
            "route": ctx.event.route,
            "failure_code": str(ctx.event.failure_code or "none"),
            "failure_reason": ctx.event.failure_reason,
            "retry_count": ctx.event.retry_count,
            "prior_contacts": ctx.event.prior_contacts,
            "checkout_duration_seconds": ctx.event.checkout_duration_seconds,
            "customer": {
                "segment": str(ctx.customer.segment),
                "previous_payments": ctx.customer.previous_payment_count,
                "previous_success_rate": ctx.customer.previous_success_rate,
                "historical_recovery_rate": ctx.customer.historical_recovery_rate,
                "average_order_value_rupees": round(
                    paise_to_rupees(ctx.customer.average_order_value_paise), 2
                ),
            },
            "systemic": {
                "route_degraded": ctx.systemic_signal.route_degraded,
                "route_failure_ratio": round(ctx.systemic_signal.route_ratio, 2),
                "route_failure_share": round(ctx.systemic_signal.route_failure_share, 3),
                "method_degraded": ctx.systemic_signal.method_degraded,
            },
            "deterministic_evidence": diagnosis.evidence,
            "candidate_causes": [
                {"cause": str(c.cause), "label": c.label, "prior": round(c.probability, 3)}
                for c in diagnosis.candidates
            ],
        }
