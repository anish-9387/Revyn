"""Agent 7 - Verifier. Confirms with the gateway whether money actually arrived.

Nothing is booked on the strength of a dispatched message. A pending action is only resolved
once the gateway is asked, which is also where a promise to pay is captured from a voice
transcript.
"""

from __future__ import annotations

import time
from datetime import date, timedelta

from app.agents.base import RecoveryContext
from app.core.clock import as_utc, utcnow
from app.core.constants import (
    ActionStatus,
    ActionType,
    Actor,
    AgentName,
    AuditEvent,
    EventStatus,
    GatewayStatus,
)
from app.core.logging import get_logger
from app.core.money import format_inr
from app.data.catalog import intervention
from app.integrations.llm import get_reasoner
from app.integrations.razorpay import build_request, get_gateway
from app.models.journey import RecoveryAction
from app.services import audit, ledger

log = get_logger(__name__)


class Verifier:
    name = AgentName.VERIFIER

    async def run(self, ctx: RecoveryContext, action: RecoveryAction) -> GatewayStatus:
        started = time.perf_counter()
        if action.status == ActionStatus.SUCCEEDED:
            status = GatewayStatus.SUCCEEDED
        elif action.status == ActionStatus.FAILED:
            status = GatewayStatus.FAILED
        else:
            status = await self._poll(ctx, action)

        if status is GatewayStatus.SUCCEEDED:
            await self._book(ctx, action)
        elif status is GatewayStatus.FAILED:
            action.status = ActionStatus.FAILED

        await self._capture_promise(ctx, action)
        ctx.trace.add(
            self.name,
            f"{action.action_type} verified as {status}",
            {"action_id": action.id, "provider_ref": action.provider_ref},
            started,
        )
        return status

    async def _poll(self, ctx: RecoveryContext, action: RecoveryAction) -> GatewayStatus:
        delay_seconds = float(action.result.get("resolve_after_seconds") or 0.0)
        from app.core.clock import scaled

        ready_at = as_utc(action.executed_at or utcnow()) + scaled(timedelta(seconds=delay_seconds))
        if utcnow() < ready_at:
            return GatewayStatus.PENDING

        request = build_request(
            ctx.event,
            ctx.customer,
            ActionType(action.action_type),
            idempotency_key=action.idempotency_key,
            discount_pct=action.discount_pct,
            degraded=ctx.degraded_route,
            provider_ref=action.provider_ref,
        )
        result = await get_gateway().fetch_state(request)
        action.result = {
            **action.result,
            "verification": {"status": str(result.status), "message": result.message},
        }
        return result.status

    async def _book(self, ctx: RecoveryContext, action: RecoveryAction) -> None:
        spec = intervention(ActionType(action.action_type))
        discount_paise = int(ctx.event.amount_paise * action.discount_pct / 100.0)
        gross = ctx.event.amount_paise - discount_paise
        cost = spec.cost_paise + discount_paise

        action.status = ActionStatus.SUCCEEDED
        ctx.event.status = EventStatus.RECOVERED
        ctx.event.resolved_at = utcnow()
        ctx.event.applied_action = ActionType(action.action_type)
        ctx.event.recovered_amount_paise = gross
        ctx.event.recovery_cost_paise += cost

        if ctx.journey is not None:
            ctx.journey.recovered_amount_paise = gross
            ctx.journey.cost_paise += cost

        await ledger.book_recovery(
            ctx.session,
            event=ctx.event,
            journey=ctx.journey,
            action=ActionType(action.action_type),
            gross_paise=gross,
            cost_paise=cost,
            model_organic_probability=ctx.event.organic_probability,
        )
        await audit.record(
            ctx.session,
            event_type=AuditEvent.OUTCOME_VERIFIED,
            entity_type="revenue_event",
            entity_id=ctx.event.id,
            summary=f"{format_inr(gross)} confirmed recovered via {action.action_type}",
            payload={"action": str(action.action_type), "provider_ref": action.provider_ref},
            actor=Actor.AGENT,
            actor_name=str(self.name),
        )

    async def _capture_promise(self, ctx: RecoveryContext, action: RecoveryAction) -> None:
        transcript = (action.result.get("notification") or {}).get("transcript")
        if not transcript or ctx.journey is None or ctx.journey.promise_date is not None:
            return
        promise = await get_reasoner().extract_promise(
            transcript,
            {"today": date.today().isoformat(), "amount_rupees": ctx.event.amount_paise / 100},
        )
        if promise is None or not promise.promised or not promise.promise_date:
            return
        try:
            promised_on = date.fromisoformat(promise.promise_date)
        except ValueError:
            return

        ctx.journey.promise_date = utcnow().replace(
            year=promised_on.year, month=promised_on.month, day=promised_on.day
        )
        ctx.journey.promise_confidence = promise.confidence
        action.result = {**action.result, "promise": promise.model_dump()}
        log.info(
            "verifier.promise_captured",
            extra={"journey_id": ctx.journey.id, "date": promise.promise_date},
        )
