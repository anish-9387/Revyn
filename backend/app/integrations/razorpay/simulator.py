"""Deterministic Razorpay simulator.

Outcomes are derived from a hash of the provider reference compared against the latent
recovery probability, so ``fetch_state`` returns the same answer every time it is called
and survives a process restart. Faults can be injected to exercise the ambiguous-state
path the executor is required to handle safely.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from app.core.constants import ActionType, GatewayStatus
from app.core.errors import AmbiguousGatewayStateError
from app.core.logging import get_logger
from app.data.outcome import OutcomeInputs, recovery_probability
from app.integrations.razorpay.base import ActionRequest, GatewayResult

log = get_logger(__name__)

# How long a messaging action takes to convert into a payment, in real-world minutes.
RESOLVE_DELAY_MINUTES: dict[ActionType, float] = {
    ActionType.PAYMENT_LINK: 35.0,
    ActionType.ALT_PAYMENT_METHOD: 30.0,
    ActionType.WHATSAPP: 40.0,
    ActionType.SMS: 55.0,
    ActionType.EMAIL: 90.0,
    ActionType.VOICE: 25.0,
    ActionType.DISCOUNT: 45.0,
    ActionType.PROMISE_FOLLOWUP: 120.0,
    ActionType.HUMAN_ESCALATION: 180.0,
    ActionType.REREGISTER_MANDATE: 40.0,
    ActionType.AMEND_MANDATE_CAP: 35.0,
    ActionType.SEND_PDN: 20.0,
    ActionType.SWITCH_RAIL: 30.0,
}


@dataclass
class FaultInjection:
    """Demo controls for the graceful-failure scenario."""

    timeouts_remaining: int = 0
    #: When set, the next timed-out action turns out to have already succeeded.
    succeed_after_timeout: bool = True

    def take_timeout(self) -> bool:
        if self.timeouts_remaining <= 0:
            return False
        self.timeouts_remaining -= 1
        return True


def _uniform(seed: str) -> float:
    digest = hashlib.sha256(seed.encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


class RazorpaySimulator:
    name = "simulator"

    def __init__(self) -> None:
        self.faults = FaultInjection()
        # Idempotency keys whose execution timed out and whose real state is unknown.
        self._unresolved: set[str] = set()

    def _reference(self, request: ActionRequest) -> str:
        prefix = {
            ActionType.RETRY_PAYMENT: "pay",
            ActionType.PAYMENT_LINK: "plink",
            ActionType.ALT_PAYMENT_METHOD: "plink",
        }.get(request.action, "msg")
        return f"{prefix}_{request.idempotency_key[:18]}"

    def _outcome_inputs(self, request: ActionRequest) -> OutcomeInputs:
        return OutcomeInputs(
            cause=request.root_cause,
            segment=request.segment,
            payment_method=request.payment_method,
            amount_paise=request.amount_paise,
            average_order_value_paise=request.average_order_value_paise,
            previous_success_rate=request.previous_success_rate,
            historical_recovery_rate=request.historical_recovery_rate,
            retry_count=request.retry_count,
            prior_contacts=request.prior_contacts,
            local_hour=request.local_hour,
            degraded=request.degraded,
        )

    def _resolves_successfully(self, request: ActionRequest, provider_ref: str) -> bool:
        probability = recovery_probability(self._outcome_inputs(request), request.action)
        return _uniform(f"{provider_ref}:{request.action}") < probability

    async def execute(self, request: ActionRequest) -> GatewayResult:
        provider_ref = self._reference(request)
        if self.faults.take_timeout():
            log.warning(
                "gateway.injected_timeout",
                extra={"reference": request.reference, "action": str(request.action)},
            )
            self._unresolved.add(request.idempotency_key)
            raise AmbiguousGatewayStateError(
                "Gateway did not respond in time; payment state is unknown",
                details={"provider_ref": provider_ref, "action": str(request.action)},
            )

        if request.action is ActionType.RETRY_PAYMENT:
            succeeded = self._resolves_successfully(request, provider_ref)
            return GatewayResult(
                status=GatewayStatus.SUCCEEDED if succeeded else GatewayStatus.FAILED,
                provider_ref=provider_ref,
                message="Captured on retry" if succeeded else "Retry declined by issuer",
                raw={"amount": request.payable_paise, "method": str(request.payment_method)},
            )

        return GatewayResult(
            status=GatewayStatus.PENDING,
            provider_ref=provider_ref,
            message=f"{request.action} dispatched, awaiting customer action",
            resolve_after_seconds=RESOLVE_DELAY_MINUTES.get(request.action, 60.0) * 60.0,
            raw={"amount": request.payable_paise, "channel": str(request.action)},
        )

    async def fetch_state(self, request: ActionRequest) -> GatewayResult:
        provider_ref = request.provider_ref or self._reference(request)
        # An attempt that timed out may still have gone through server-side. This is the
        # branch that makes verify-before-retry the only safe behaviour.
        if request.idempotency_key in self._unresolved:
            self._unresolved.discard(request.idempotency_key)
            if not self.faults.succeed_after_timeout:
                return GatewayResult(
                    status=GatewayStatus.FAILED,
                    provider_ref=provider_ref,
                    message="No payment was created before the timeout",
                    raw={"verified": True},
                )
            return GatewayResult(
                status=GatewayStatus.SUCCEEDED,
                provider_ref=provider_ref,
                message="Payment had already succeeded before the timeout",
                raw={"verified": True},
            )
        succeeded = self._resolves_successfully(request, provider_ref)
        return GatewayResult(
            status=GatewayStatus.SUCCEEDED if succeeded else GatewayStatus.FAILED,
            provider_ref=provider_ref,
            message="Payment captured" if succeeded else "No payment received",
            raw={"verified": True},
        )

    async def close(self) -> None:
        return None
