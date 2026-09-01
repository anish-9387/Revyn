"""Gateway contract shared by the Razorpay client and the simulator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from app.core.constants import (
    ActionType,
    CustomerSegment,
    EventKind,
    GatewayStatus,
    PaymentMethod,
    RootCause,
)
from app.models.customer import Customer
from app.models.event import RevenueEvent


@dataclass(slots=True)
class ActionRequest:
    """Everything the gateway needs, flattened so no ORM object crosses the boundary."""

    action: ActionType
    kind: EventKind
    reference: str
    idempotency_key: str
    amount_paise: int
    discount_pct: float
    customer_name: str
    customer_email: str
    customer_phone: str
    payment_method: PaymentMethod
    order_ref: str | None = None
    payment_ref: str | None = None
    subscription_ref: str | None = None
    invoice_ref: str | None = None
    provider_ref: str | None = None
    # Latent-process inputs, used only by the simulator.
    root_cause: RootCause = RootCause.UNKNOWN
    segment: CustomerSegment = CustomerSegment.MEDIUM
    average_order_value_paise: int = 1
    previous_success_rate: float = 0.5
    historical_recovery_rate: float = 0.2
    retry_count: int = 0
    prior_contacts: int = 0
    local_hour: float = 12.0
    degraded: bool = False

    @property
    def payable_paise(self) -> int:
        return int(self.amount_paise * (1 - self.discount_pct / 100.0))


@dataclass(slots=True)
class GatewayResult:
    status: GatewayStatus
    provider_ref: str | None = None
    message: str = ""
    #: Seconds until the outcome can be verified. Messaging actions resolve later.
    resolve_after_seconds: float = 0.0
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def settled(self) -> bool:
        return self.status in (GatewayStatus.SUCCEEDED, GatewayStatus.FAILED)


class PaymentGateway(Protocol):
    name: str

    async def execute(self, request: ActionRequest) -> GatewayResult:
        """Perform the action. Raises AmbiguousGatewayStateError when state is unknown."""
        ...

    async def fetch_state(self, request: ActionRequest) -> GatewayResult:
        """Read the authoritative outcome. Always safe to call, never charges anything."""
        ...

    async def close(self) -> None: ...


def build_request(
    event: RevenueEvent,
    customer: Customer,
    action: ActionType,
    *,
    idempotency_key: str,
    discount_pct: float = 0.0,
    degraded: bool = False,
    provider_ref: str | None = None,
) -> ActionRequest:
    from app.core.clock import as_utc
    from app.engines.features import IST_OFFSET_HOURS

    occurred = as_utc(event.occurred_at)
    return ActionRequest(
        action=action,
        kind=EventKind(event.kind),
        reference=event.external_ref,
        idempotency_key=idempotency_key,
        amount_paise=event.amount_paise,
        discount_pct=discount_pct,
        customer_name=customer.name,
        customer_email=customer.email,
        customer_phone=customer.phone,
        payment_method=PaymentMethod(event.payment_method),
        order_ref=event.order_ref,
        payment_ref=event.payment_ref,
        subscription_ref=event.subscription_ref,
        invoice_ref=event.invoice_ref,
        provider_ref=provider_ref,
        root_cause=RootCause(event.root_cause),
        segment=CustomerSegment(customer.segment),
        average_order_value_paise=max(customer.average_order_value_paise, 1),
        previous_success_rate=customer.previous_success_rate,
        historical_recovery_rate=customer.historical_recovery_rate,
        retry_count=event.retry_count,
        prior_contacts=event.prior_contacts,
        local_hour=(occurred.hour + occurred.minute / 60.0 + IST_OFFSET_HOURS) % 24.0,
        degraded=degraded,
    )
