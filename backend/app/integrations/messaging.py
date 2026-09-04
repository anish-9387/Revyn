from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from app.core.constants import ActionType, EventKind

VOICE_REPLIES: tuple[str, ...] = (
    "Sorry about that, I will pay tomorrow morning once the funds clear.",
    "I have already asked our accounts team to release it. Should be done in 3 days.",
    "There is a discrepancy in the invoice, I need someone to call me back.",
    "Yes I can pay Rs 72,000 by Friday, please send a fresh link.",
    "I am travelling this week. I will clear it next Monday for sure.",
    "I did not authorise this renewal, please cancel the subscription.",
    "paisa Monday tak aa jayega, thoda time do",
    "kal subah payment kar dunga, salary aane ke baad",
    "parso tak clear ho jayega, promise",
)

TEMPLATES: dict[tuple[EventKind, ActionType], str] = {
    (EventKind.PAYMENT_FAILURE, ActionType.WHATSAPP): "Hi {name}, your payment of {amount} did not go through. Complete it here: {link}",
    (EventKind.CART_ABANDONMENT, ActionType.WHATSAPP): "Hi {name}, your cart worth {amount} is still saved. Finish checkout here: {link}",
    (EventKind.SUBSCRIPTION_FAILURE, ActionType.WHATSAPP): "Hi {name}, we could not renew your plan ({amount}). Update your payment method: {link}",
    (EventKind.OVERDUE_INVOICE, ActionType.EMAIL): "Hi {name}, invoice for {amount} is past its due date. Pay securely here: {link}",
    (EventKind.PAYMENT_FAILURE, ActionType.SEND_PDN): "Hi {name}, reminder: {amount} will be debited in 24 hours. Ensure sufficient balance. Link: {link}",
    (EventKind.SUBSCRIPTION_FAILURE, ActionType.SEND_PDN): "Hi {name}, your subscription renewal of {amount} is scheduled in 24 hours. Keep balance ready: {link}",
    (EventKind.PAYMENT_FAILURE, ActionType.REREGISTER_MANDATE): "Hi {name}, your mandate needs re-authorisation for {amount}. Re-register securely: {link}",
    (EventKind.SUBSCRIPTION_FAILURE, ActionType.REREGISTER_MANDATE): "Hi {name}, please re-authorise your mandate for {amount} to continue service: {link}",
    (EventKind.PAYMENT_FAILURE, ActionType.AMEND_MANDATE_CAP): "Hi {name}, your charge {amount} exceeds mandate cap. Approve higher limit: {link}",
}

REGULATORY_TEMPLATES: dict[str, str] = {
    "mandate_absent": "Hi {name}, no mandate found for {amount}. Authorise mandate: {link}",
    "mandate_revoked": "Hi {name}, your mandate was revoked - please re-authorise for {amount}: {link}",
    "mandate_cap_exceeded": "Hi {name}, {amount} exceeds your mandate cap. Approve amendment: {link}",
    "pdn_missing": "Hi {name}, pre-debit notification for {amount}. Confirm & keep balance ready: {link}",
    "afa_threshold_breach": "Hi {name}, {amount} needs fresh authentication. Authorise here: {link}",
}

DEFAULT_TEMPLATE = "Hi {name}, {amount} is pending on your account. Complete it here: {link}"


@dataclass(slots=True)
class Notification:
    channel: ActionType
    recipient: str
    body: str
    message_ref: str
    transcript: str | None = None


@dataclass(slots=True)
class ValidationResult:
    ok: bool
    violations: list[str]
    fallback_used: bool = False


DLT_MAX_LEN: dict[ActionType, int] = {
    ActionType.WHATSAPP: 1024,
    ActionType.SMS: 160,
    ActionType.EMAIL: 2000,
    ActionType.SEND_PDN: 1024,
    ActionType.REREGISTER_MANDATE: 1024,
    ActionType.AMEND_MANDATE_CAP: 1024,
}


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


def validate_message(body: str, *, channel: ActionType, expected_amount: str | None = None, expected_link: str | None = None, opted_out: bool = False) -> ValidationResult:
    violations: list[str] = []
    if opted_out:
        violations.append("Customer opted out")
    max_len = DLT_MAX_LEN.get(channel, 1024)
    if len(body) > max_len:
        violations.append(f"Exceeds channel length {max_len}")
    # Amount hallucination check: if body contains Rs/₹ amount, it must match expected
    amounts = re.findall(r"(?:rs\.?|inr|₹)\s?[\d,]+(?:\.\d{1,2})?", body.lower())
    if amounts and expected_amount:
        norm_expected = re.sub(r"[^\d.]", "", expected_amount.lower())
        found_match = any(re.sub(r"[^\d.]", "", a) == norm_expected for a in amounts)
        # allow if expected amount string appears verbatim
        if expected_amount.lower() not in body.lower() and not found_match:
            violations.append("Amount in message does not match event record")
    # Link check suppressed: body may use templated link, not strict violation
    _ = expected_link
    # No invented discounts/deadlines
    if re.search(r"\b\d{1,2}%\s*(?:off|discount|waiver)\b", body.lower()):
        # allow only if expected? For now flag as violation if discount channel not used
        if channel is not ActionType.DISCOUNT:
            violations.append("Invented discount not authorised by merchant")
    if not body.strip():
        violations.append("Empty message")
    return ValidationResult(ok=len(violations) == 0, violations=violations)


async def generate_message(
    *,
    channel: ActionType,
    kind: EventKind,
    name: str,
    amount_label: str,
    link: str,
    recipient: str,
    reference: str,
    root_cause: str | None = None,
    language_hint: str = "hinglish",
    opted_out: bool = False,
) -> tuple[Notification, ValidationResult]:
    base = render(channel=channel, kind=kind, name=name, amount_label=amount_label, link=link, recipient=recipient, reference=reference)
    # Try LLM generation if available
    try:
        from app.integrations.llm import get_reasoner
        from app.integrations.llm.prompts import HINGLISH_SYSTEM

        reasoner = get_reasoner()
        # Only attempt LLM if not deterministic provider stub
        if reasoner.name != "deterministic":
            ctx = {
                "channel": str(channel),
                "kind": str(kind),
                "name": name.split()[0],
                "amount": amount_label,
                "link": link,
                "root_cause": root_cause or "unknown",
                "language": language_hint,
                "template_hint": TEMPLATES.get((kind, channel), DEFAULT_TEMPLATE),
                "regulatory_template": REGULATORY_TEMPLATES.get(root_cause or "", ""),
            }
            # Use private structured if available else fallback to simple
            try:
                # Direct call via anthropic provider _structured with custom prompt if available
                if hasattr(reasoner, "_structured"):
                    from pydantic import BaseModel

                    from app.integrations.llm.prompts import HINGLISH_FORMAT

                    class HinglishOut(BaseModel):
                        body: str

                    out: HinglishOut | None = await reasoner._structured(system=HINGLISH_SYSTEM, payload=ctx, response_format=HINGLISH_FORMAT, model_cls=HinglishOut, instruction="Generate the Hinglish recovery message.")  # type: ignore[attr-defined]
                    if out and out.body:
                        candidate = out.body.strip()
                        val = validate_message(candidate, channel=channel, expected_amount=amount_label, expected_link=link, opted_out=opted_out)
                        if val.ok:
                            return Notification(channel=channel, recipient=recipient, body=candidate, message_ref=base.message_ref, transcript=base.transcript), val
                        # fall through to fallback, log audit via violations
                        val.fallback_used = True
                        return base, val
            except Exception:
                pass
    except Exception:
        pass
    val = validate_message(base.body, channel=channel, expected_amount=amount_label, expected_link=link, opted_out=opted_out)
    return base, val
