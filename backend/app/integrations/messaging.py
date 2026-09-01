"""Notification simulator.

No real customer is ever contacted from a demo, so every channel is simulated here. Voice
calls also return a synthetic customer reply, which is what the promise-to-pay extractor
runs against.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from app.core.constants import ActionType, EventKind

VOICE_REPLIES: tuple[str, ...] = (
    "Sorry about that, I will pay tomorrow morning once the funds clear.",
    "I have already asked our accounts team to release it. Should be done in 3 days.",
    "There is a discrepancy in the invoice, I need someone to call me back.",
    "Yes I can pay Rs 72,000 by Friday, please send a fresh link.",
    "I am travelling this week. I will clear it next Monday for sure.",
    "I did not authorise this renewal, please cancel the subscription.",
)

TEMPLATES: dict[tuple[EventKind, ActionType], str] = {
    (EventKind.PAYMENT_FAILURE, ActionType.WHATSAPP): (
        "Hi {name}, your payment of {amount} did not go through. Complete it here: {link}"
    ),
    (EventKind.CART_ABANDONMENT, ActionType.WHATSAPP): (
        "Hi {name}, your cart worth {amount} is still saved. Finish checkout here: {link}"
    ),
    (EventKind.SUBSCRIPTION_FAILURE, ActionType.WHATSAPP): (
        "Hi {name}, we could not renew your plan ({amount}). Update your payment method: {link}"
    ),
    (EventKind.OVERDUE_INVOICE, ActionType.EMAIL): (
        "Hi {name}, invoice for {amount} is past its due date. Pay securely here: {link}"
    ),
}

DEFAULT_TEMPLATE = "Hi {name}, {amount} is pending on your account. Complete it here: {link}"


@dataclass(slots=True)
class Notification:
    channel: ActionType
    recipient: str
    body: str
    message_ref: str
    transcript: str | None = None


def _pick(options: tuple[str, ...], seed: str) -> str:
    index = int(hashlib.sha256(seed.encode()).hexdigest(), 16) % len(options)
    return options[index]


def render(
    *,
    channel: ActionType,
    kind: EventKind,
    name: str,
    amount_label: str,
    link: str,
    recipient: str,
    reference: str,
) -> Notification:
    template = TEMPLATES.get((kind, channel), DEFAULT_TEMPLATE)
    body = template.format(name=name.split()[0], amount=amount_label, link=link)
    transcript = _pick(VOICE_REPLIES, reference) if channel is ActionType.VOICE else None
    return Notification(
        channel=channel,
        recipient=recipient,
        body=body,
        message_ref=f"{channel}_{hashlib.sha256(reference.encode()).hexdigest()[:12]}",
        transcript=transcript,
    )
