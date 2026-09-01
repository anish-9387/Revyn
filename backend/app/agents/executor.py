"""Agent 6 - Executor. Performs an approved action exactly once.

Two invariants hold here: an idempotency key is reserved before the gateway is touched, and
an ambiguous gateway response is never retried, only verified. Together they stop a timeout
from turning into a double charge.
"""

from __future__ import annotations

import time

from app.agents.base import RecoveryContext
from app.core.clock import utcnow
from app.core.constants import (
    ActionStatus,
    ActionType,
    Actor,
    AgentName,
    AuditEvent,
    GatewayStatus,
    PolicyRule,
)
from app.core.errors import AmbiguousGatewayStateError, GatewayError
from app.core.logging import get_logger
from app.core.money import format_inr
from app.integrations import messaging
from app.integrations.razorpay import build_request, get_gateway
from app.models.journey import RecoveryAction
from app.services import audit, idempotency

log = get_logger(__name__)

NOTIFICATION_CHANNELS = frozenset(
    {
        ActionType.WHATSAPP,
        ActionType.SMS,
        ActionType.EMAIL,
        ActionType.VOICE,
        ActionType.DISCOUNT,
        ActionType.PROMISE_FOLLOWUP,
        ActionType.PAYMENT_LINK,
    }
)

STATUS_MAP = {
    GatewayStatus.SUCCEEDED: ActionStatus.SUCCEEDED,
    GatewayStatus.FAILED: ActionStatus.FAILED,
    GatewayStatus.PENDING: ActionStatus.EXECUTING,
    GatewayStatus.AMBIGUOUS: ActionStatus.EXECUTING,
}


class Executor:
    name = AgentName.EXECUTOR

    async def execute(self, ctx: RecoveryContext, action: RecoveryAction) -> GatewayStatus:
        started = time.perf_counter()
        gateway = get_gateway()

        if not await idempotency.reserve(action.idempotency_key, action.id):
            owner = await idempotency.owner_of(action.idempotency_key)
            if owner != action.id:
                action.status = ActionStatus.CANCELLED
                action.blocked_reasons = [str(PolicyRule.DUPLICATE_ACTION)]
                ctx.trace.add(
                    self.name,
                    "Skipped: identical action already reserved",
                    {"owner": owner},
                    started,
                )
                return GatewayStatus.FAILED

        request = build_request(
            ctx.event,
            ctx.customer,
            ActionType(action.action_type),
            idempotency_key=action.idempotency_key,
            discount_pct=action.discount_pct,
            degraded=ctx.degraded_route,
        )
        action.status = ActionStatus.EXECUTING
        action.executed_at = utcnow()

        try:
            result = await gateway.execute(request)
        except AmbiguousGatewayStateError as exc:
            log.warning("executor.ambiguous", extra={"action_id": action.id, "error": exc.message})
            result = await self._verify_instead_of_retry(ctx, action, request, exc)
        except GatewayError as exc:
            action.status = ActionStatus.FAILED
            action.error = exc.message
            ctx.trace.add(self.name, f"Gateway rejected the action: {exc.message}", {}, started)
            return GatewayStatus.FAILED

        notification = self._notify(ctx, action, result)
        action.provider_ref = result.provider_ref
        action.status = STATUS_MAP[result.status]
        action.result = {
            "status": str(result.status),
            "message": result.message,
            "provider_ref": result.provider_ref,
            "resolve_after_seconds": result.resolve_after_seconds,
            "raw": result.raw,
            "notification": notification,
        }

        await audit.record(
            ctx.session,
            event_type=AuditEvent.ACTION_EXECUTED,
            entity_type="recovery_action",
            entity_id=action.id,
            summary=(
                f"{action.action_type} returned {result.status} "
                f"for {format_inr(ctx.event.amount_paise)}"
            ),
            payload={
                "action": str(action.action_type),
                "gateway": gateway.name,
                "provider_ref": result.provider_ref,
                "status": str(result.status),
                "idempotency_key": action.idempotency_key,
            },
            actor=Actor.AGENT,
            actor_name=str(self.name),
        )
        ctx.trace.add(
            self.name,
            f"{action.action_type} executed via {gateway.name}: {result.status}",
            {"provider_ref": result.provider_ref, "message": result.message},
            started,
        )
        return result.status

    async def _verify_instead_of_retry(self, ctx, action, request, exc):
        """Confirm the real state rather than repeating a charge that may have landed."""
        action.result = {"ambiguous": True, "error": exc.message}
        await audit.record(
            ctx.session,
            event_type=AuditEvent.ACTION_EXECUTED,
            entity_type="recovery_action",
            entity_id=action.id,
            summary="Gateway state ambiguous, verifying before any retry",
            payload={"error": exc.message, "action": str(action.action_type)},
            actor=Actor.AGENT,
            actor_name=str(self.name),
        )
        verified = await get_gateway().fetch_state(request)
        ctx.trace.add(
            self.name,
            f"Payment state was uncertain, verification reports {verified.status}",
            {"verified_status": str(verified.status), "message": verified.message},
        )
        return verified

    @staticmethod
    def _notify(ctx: RecoveryContext, action: RecoveryAction, result) -> dict | None:
        channel = ActionType(action.action_type)
        if channel not in NOTIFICATION_CHANNELS:
            return None
        recipient = ctx.customer.email if channel is ActionType.EMAIL else ctx.customer.phone
        note = messaging.render(
            channel=channel,
            kind=ctx.event.kind,
            name=ctx.customer.name,
            amount_label=format_inr(ctx.event.amount_paise),
            link=f"https://rzp.io/l/{(result.provider_ref or action.id)[:12]}",
            recipient=recipient,
            reference=action.idempotency_key,
        )
        return {
            "channel": str(note.channel),
            "recipient": note.recipient,
            "body": note.body,
            "message_ref": note.message_ref,
            "transcript": note.transcript,
        }
