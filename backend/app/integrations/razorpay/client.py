"""Razorpay test-mode client.

Test mode cannot authorise a payment on the merchant behalf, so a retry is expressed as a
fresh order plus a hosted payment link and the outcome is read back by polling. That
asymmetry is why the simulator is the default for offline demos.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings
from app.core.constants import ActionType, GatewayStatus
from app.core.errors import AmbiguousGatewayStateError, GatewayError
from app.core.logging import get_logger
from app.integrations.razorpay.base import ActionRequest, GatewayResult

log = get_logger(__name__)

TERMINAL_PAYMENT_STATES = {"captured", "authorized", "refunded"}


class RazorpayClient:
    name = "razorpay"

    def __init__(self, key_id: str, key_secret: str, base_url: str, timeout: float) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            auth=(key_id, key_secret),
            timeout=timeout,
            headers={"Content-Type": "application/json"},
        )

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = await self._client.request(method, path, **kwargs)
        except httpx.TimeoutException as exc:
            raise AmbiguousGatewayStateError(
                "Razorpay request timed out; payment state is unknown", details={"path": path}
            ) from exc
        except httpx.HTTPError as exc:
            raise GatewayError(f"Razorpay transport error: {exc}", details={"path": path}) from exc

        if response.status_code >= 500:
            raise AmbiguousGatewayStateError(
                f"Razorpay returned {response.status_code}; state is unknown",
                details={"path": path, "body": response.text[:400]},
            )
        if response.status_code >= 400:
            raise GatewayError(
                f"Razorpay rejected the request ({response.status_code})",
                details={"path": path, "body": response.text[:400]},
            )
        return response.json()

    async def execute(self, request: ActionRequest) -> GatewayResult:
        if request.action in (
            ActionType.RETRY_PAYMENT,
            ActionType.PAYMENT_LINK,
            ActionType.ALT_PAYMENT_METHOD,
        ):
            return await self._create_payment_link(request)
        # Messaging channels are simulated: no live customer is contacted from a demo.
        return GatewayResult(
            status=GatewayStatus.PENDING,
            provider_ref=f"msg_{request.idempotency_key[:18]}",
            message=f"{request.action} dispatched via notification simulator",
            resolve_after_seconds=45 * 60,
        )

    async def _create_payment_link(self, request: ActionRequest) -> GatewayResult:
        payload = {
            "amount": request.payable_paise,
            "currency": "INR",
            "accept_partial": False,
            "reference_id": f"{request.reference}-{request.idempotency_key[:10]}",
            "description": f"Revyn recovery for {request.reference}",
            "customer": {
                "name": request.customer_name,
                "email": request.customer_email,
                "contact": request.customer_phone,
            },
            "notify": {"sms": False, "email": False},
            "reminder_enable": True,
            "notes": {"revyn_action": str(request.action), "revyn_reference": request.reference},
        }
        body = await self._request(
            "POST",
            "/payment_links",
            json=payload,
            headers={"X-Payment-Link-Idempotency": request.idempotency_key},
        )
        return GatewayResult(
            status=GatewayStatus.PENDING,
            provider_ref=body.get("id"),
            message="Payment link created",
            resolve_after_seconds=30 * 60,
            raw={"short_url": body.get("short_url"), "status": body.get("status")},
        )

    async def fetch_state(self, request: ActionRequest) -> GatewayResult:
        reference = request.provider_ref
        if reference and reference.startswith("plink_"):
            body = await self._request("GET", f"/payment_links/{reference}")
            paid = body.get("status") == "paid" or int(body.get("amount_paid") or 0) > 0
            return GatewayResult(
                status=GatewayStatus.SUCCEEDED if paid else GatewayStatus.PENDING,
                provider_ref=reference,
                message=f"Payment link is {body.get('status')}",
                raw=body,
            )
        if request.order_ref:
            body = await self._request("GET", f"/orders/{request.order_ref}/payments")
            payments = body.get("items") or []
            captured = any(item.get("status") in TERMINAL_PAYMENT_STATES for item in payments)
            return GatewayResult(
                status=GatewayStatus.SUCCEEDED if captured else GatewayStatus.FAILED,
                provider_ref=reference,
                message=f"{len(payments)} payment attempts on order",
                raw=body,
            )
        if request.payment_ref:
            body = await self._request("GET", f"/payments/{request.payment_ref}")
            captured = body.get("status") in TERMINAL_PAYMENT_STATES
            return GatewayResult(
                status=GatewayStatus.SUCCEEDED if captured else GatewayStatus.FAILED,
                provider_ref=request.payment_ref,
                message=f"Payment is {body.get('status')}",
                raw=body,
            )
        return GatewayResult(
            status=GatewayStatus.PENDING, provider_ref=reference, message="Nothing to verify yet"
        )

    async def close(self) -> None:
        await self._client.aclose()


def build_client() -> RazorpayClient:
    if not (settings.razorpay_key_id and settings.razorpay_key_secret):
        raise GatewayError("Razorpay credentials are not configured")
    return RazorpayClient(
        key_id=settings.razorpay_key_id,
        key_secret=settings.razorpay_key_secret,
        base_url=settings.razorpay_base_url,
        timeout=settings.gateway_timeout_seconds,
    )
