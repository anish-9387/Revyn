"""Gateway selection. The simulator is the default so demos never need credentials."""

from __future__ import annotations

from app.core.config import settings
from app.core.logging import get_logger
from app.integrations.razorpay.base import PaymentGateway
from app.integrations.razorpay.simulator import RazorpaySimulator

log = get_logger(__name__)

_gateway: PaymentGateway | None = None


def get_gateway() -> PaymentGateway:
    global _gateway
    if _gateway is None:
        if settings.gateway == "razorpay":
            from app.integrations.razorpay.client import build_client

            try:
                _gateway = build_client()
                log.info("gateway.razorpay_ready")
            except Exception as exc:
                log.warning("gateway.razorpay_unavailable", extra={"error": str(exc)})
                _gateway = RazorpaySimulator()
        else:
            _gateway = RazorpaySimulator()
    return _gateway


async def reset_gateway() -> None:
    global _gateway
    if _gateway is not None:
        await _gateway.close()
        _gateway = None


def simulator() -> RazorpaySimulator | None:
    gateway = get_gateway()
    return gateway if isinstance(gateway, RazorpaySimulator) else None
