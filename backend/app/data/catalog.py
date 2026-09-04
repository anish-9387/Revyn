"""Static domain knowledge: interventions, root-cause library and failure mapping.

Everything an agent is allowed to propose is enumerated here. The LLM may rank and
explain these entries but can never invent one, which is what keeps the action space
of the system bounded.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.constants import (
    ActionType,
    CauseLayer,
    EventKind,
    FailureCode,
    PaymentMethod,
    RootCause,
)


@dataclass(frozen=True, slots=True)
class Intervention:
    action: ActionType
    label: str
    #: Direct cost of one attempt, in paise. Discounts add a share of the amount.
    cost_paise: int
    #: 0..1 customer annoyance weight, priced into expected value.
    friction_score: float
    #: Prior probability of recovery before any context is applied.
    base_success: float
    consumes_contact: bool
    touches_gateway: bool
    description: str
    discount_pct: float = 0.0


INTERVENTIONS: dict[ActionType, Intervention] = {
    ActionType.DO_NOTHING: Intervention(
        action=ActionType.DO_NOTHING,
        label="Do nothing",
        cost_paise=0,
        friction_score=0.0,
        base_success=0.0,
        consumes_contact=False,
        touches_gateway=False,
        description="Let the customer recover organically. Chosen when nothing else pays for itself.",
    ),
    ActionType.RETRY_PAYMENT: Intervention(
        action=ActionType.RETRY_PAYMENT,
        label="Delayed retry",
        cost_paise=200,
        friction_score=0.02,
        base_success=0.22,
        consumes_contact=False,
        touches_gateway=True,
        description="Re-attempt the same instrument after a cooldown. Silent and cheap.",
    ),
    ActionType.PAYMENT_LINK: Intervention(
        action=ActionType.PAYMENT_LINK,
        label="Payment link",
        cost_paise=300,
        friction_score=0.12,
        base_success=0.34,
        consumes_contact=True,
        touches_gateway=True,
        description="Send a fresh hosted checkout so the customer can pick another instrument.",
    ),
    ActionType.ALT_PAYMENT_METHOD: Intervention(
        action=ActionType.ALT_PAYMENT_METHOD,
        label="Alternative method",
        cost_paise=250,
        friction_score=0.10,
        base_success=0.36,
        consumes_contact=True,
        touches_gateway=True,
        description="Route around the failing instrument by suggesting a healthier method.",
    ),
    ActionType.WHATSAPP: Intervention(
        action=ActionType.WHATSAPP,
        label="WhatsApp nudge",
        cost_paise=65,
        friction_score=0.15,
        base_success=0.40,
        consumes_contact=True,
        touches_gateway=False,
        description="Conversational reminder on the highest-response channel.",
    ),
    ActionType.SMS: Intervention(
        action=ActionType.SMS,
        label="SMS reminder",
        cost_paise=25,
        friction_score=0.18,
        base_success=0.30,
        consumes_contact=True,
        touches_gateway=False,
        description="Fallback reminder for customers without WhatsApp reachability.",
    ),
    ActionType.EMAIL: Intervention(
        action=ActionType.EMAIL,
        label="Email reminder",
        cost_paise=5,
        friction_score=0.06,
        base_success=0.22,
        consumes_contact=True,
        touches_gateway=False,
        description="Low-friction reminder, effective for B2B receivables.",
    ),
    ActionType.VOICE: Intervention(
        action=ActionType.VOICE,
        label="Voice agent call",
        cost_paise=900,
        friction_score=0.55,
        base_success=0.52,
        consumes_contact=True,
        touches_gateway=False,
        description="Outbound call that can capture a promise to pay. High cost, high friction.",
    ),
    ActionType.DISCOUNT: Intervention(
        action=ActionType.DISCOUNT,
        label="Recovery offer",
        cost_paise=65,
        friction_score=0.20,
        base_success=0.46,
        consumes_contact=True,
        touches_gateway=False,
        description="Bounded incentive. The discount itself is charged against recovered revenue.",
        discount_pct=8.0,
    ),
    ActionType.HUMAN_ESCALATION: Intervention(
        action=ActionType.HUMAN_ESCALATION,
        label="Human escalation",
        cost_paise=12_000,
        friction_score=0.30,
        base_success=0.62,
        consumes_contact=False,
        touches_gateway=False,
        description="Hand the case to a collections owner. Reserved for high value or disputes.",
    ),
    ActionType.PROMISE_FOLLOWUP: Intervention(
        action=ActionType.PROMISE_FOLLOWUP,
        label="Promise follow-up",
        cost_paise=65,
        friction_score=0.16,
        base_success=0.44,
        consumes_contact=True,
        touches_gateway=False,
        description="Check a captured promise-to-pay on its due date and escalate if broken.",
    ),
    ActionType.REREGISTER_MANDATE: Intervention(
        action=ActionType.REREGISTER_MANDATE,
        label="Re-register mandate",
        cost_paise=150,
        friction_score=0.25,
        base_success=0.48,
        consumes_contact=True,
        touches_gateway=True,
        description="Send re-registration link for AFA / UPI-PIN reverification.",
    ),
    ActionType.AMEND_MANDATE_CAP: Intervention(
        action=ActionType.AMEND_MANDATE_CAP,
        label="Amend mandate cap",
        cost_paise=100,
        friction_score=0.18,
        base_success=0.52,
        consumes_contact=True,
        touches_gateway=True,
        description="Request customer to authorise a higher mandate cap.",
    ),
    ActionType.SEND_PDN: Intervention(
        action=ActionType.SEND_PDN,
        label="Pre-debit notification",
        cost_paise=20,
        friction_score=0.08,
        base_success=0.35,
        consumes_contact=True,
        touches_gateway=False,
        description="Send RBI-mandated 24h pre-debit notification; doubles as balance top-up nudge.",
    ),
    ActionType.SWITCH_RAIL: Intervention(
        action=ActionType.SWITCH_RAIL,
        label="Switch rail",
        cost_paise=250,
        friction_score=0.12,
        base_success=0.38,
        consumes_contact=True,
        touches_gateway=True,
        description="Move recurring charge from failing rail to healthier one.",
    ),
}

#: Actions each loss class can legally use. A cart that never reached the gateway
#: has nothing to retry; an invoice cannot be charged without customer action.
ALLOWED_ACTIONS: dict[EventKind, tuple[ActionType, ...]] = {
    EventKind.PAYMENT_FAILURE: (
        ActionType.RETRY_PAYMENT,
        ActionType.PAYMENT_LINK,
        ActionType.ALT_PAYMENT_METHOD,
        ActionType.WHATSAPP,
        ActionType.SMS,
        ActionType.EMAIL,
        ActionType.VOICE,
        ActionType.DISCOUNT,
        ActionType.HUMAN_ESCALATION,
        ActionType.REREGISTER_MANDATE,
        ActionType.AMEND_MANDATE_CAP,
        ActionType.SEND_PDN,
        ActionType.SWITCH_RAIL,
        ActionType.DO_NOTHING,
    ),
    EventKind.CART_ABANDONMENT: (
        ActionType.PAYMENT_LINK,
        ActionType.WHATSAPP,
        ActionType.SMS,
        ActionType.EMAIL,
        ActionType.DISCOUNT,
        ActionType.DO_NOTHING,
    ),
    EventKind.SUBSCRIPTION_FAILURE: (
        ActionType.RETRY_PAYMENT,
        ActionType.PAYMENT_LINK,
        ActionType.ALT_PAYMENT_METHOD,
        ActionType.WHATSAPP,
        ActionType.SMS,
        ActionType.EMAIL,
        ActionType.VOICE,
        ActionType.HUMAN_ESCALATION,
        ActionType.REREGISTER_MANDATE,
        ActionType.AMEND_MANDATE_CAP,
        ActionType.SEND_PDN,
        ActionType.SWITCH_RAIL,
        ActionType.DO_NOTHING,
    ),
    EventKind.OVERDUE_INVOICE: (
        ActionType.PAYMENT_LINK,
        ActionType.EMAIL,
        ActionType.WHATSAPP,
        ActionType.SMS,
        ActionType.VOICE,
        ActionType.PROMISE_FOLLOWUP,
        ActionType.HUMAN_ESCALATION,
        ActionType.DO_NOTHING,
    ),
}

REGULATORY_ALLOWED_ACTIONS: dict[RootCause, tuple[ActionType, ...]] = {
    RootCause.MANDATE_ABSENT: (ActionType.REREGISTER_MANDATE, ActionType.SWITCH_RAIL, ActionType.HUMAN_ESCALATION, ActionType.DO_NOTHING),
    RootCause.MANDATE_REVOKED: (ActionType.REREGISTER_MANDATE, ActionType.HUMAN_ESCALATION, ActionType.DO_NOTHING),
    RootCause.MANDATE_CAP_EXCEEDED: (ActionType.AMEND_MANDATE_CAP, ActionType.REREGISTER_MANDATE, ActionType.HUMAN_ESCALATION, ActionType.DO_NOTHING),
    RootCause.PDN_MISSING: (ActionType.SEND_PDN, ActionType.WHATSAPP, ActionType.SMS, ActionType.EMAIL, ActionType.DO_NOTHING),
    RootCause.AFA_THRESHOLD_BREACH: (ActionType.REREGISTER_MANDATE, ActionType.PAYMENT_LINK, ActionType.HUMAN_ESCALATION, ActionType.DO_NOTHING),
    RootCause.EXECUTION_WINDOW_MISS: (ActionType.RETRY_PAYMENT, ActionType.SEND_PDN, ActionType.DO_NOTHING),
}


@dataclass(frozen=True, slots=True)
class CauseProfile:
    cause: RootCause
    layer: CauseLayer
    label: str
    #: True when the condition usually clears on its own within minutes.
    transient: bool
    #: True when re-charging the same instrument can plausibly succeed.
    retryable: bool
    #: Multiplier on the organic (no-intervention) recovery baseline.
    organic_multiplier: float
    narrative: str
    #: Per-action multiplier on the base success rate. Missing keys default to 1.0.
    affinity: dict[ActionType, float] = field(default_factory=dict)


CAUSE_LIBRARY: dict[RootCause, CauseProfile] = {
    RootCause.TRANSIENT_BANK_DECLINE: CauseProfile(
        cause=RootCause.TRANSIENT_BANK_DECLINE,
        layer=CauseLayer.PAYMENT,
        label="Temporary bank-side decline",
        transient=True,
        retryable=True,
        organic_multiplier=1.35,
        narrative="The issuer declined a technically valid attempt and usually clears within the hour.",
        affinity={
            ActionType.RETRY_PAYMENT: 1.95,
            ActionType.ALT_PAYMENT_METHOD: 1.15,
            ActionType.PAYMENT_LINK: 1.05,
            ActionType.WHATSAPP: 0.90,
            ActionType.DISCOUNT: 0.70,
        },
    ),
    RootCause.HARD_BANK_DECLINE: CauseProfile(
        cause=RootCause.HARD_BANK_DECLINE,
        layer=CauseLayer.PAYMENT,
        label="Hard issuer decline",
        transient=False,
        retryable=False,
        organic_multiplier=0.75,
        narrative="The issuer rejected the instrument outright; the same instrument will fail again.",
        affinity={
            ActionType.RETRY_PAYMENT: 0.25,
            ActionType.ALT_PAYMENT_METHOD: 1.45,
            ActionType.PAYMENT_LINK: 1.20,
        },
    ),
    RootCause.INSUFFICIENT_BALANCE: CauseProfile(
        cause=RootCause.INSUFFICIENT_BALANCE,
        layer=CauseLayer.CUSTOMER,
        label="Insufficient funds",
        transient=True,
        retryable=True,
        organic_multiplier=1.10,
        narrative="Balance was short at the moment of capture; recovery tracks the customer payday cycle.",
        affinity={
            ActionType.RETRY_PAYMENT: 0.55,
            ActionType.WHATSAPP: 1.25,
            ActionType.PAYMENT_LINK: 1.20,
            ActionType.DISCOUNT: 1.30,
            ActionType.VOICE: 1.10,
        },
    ),
    RootCause.AUTH_FRICTION: CauseProfile(
        cause=RootCause.AUTH_FRICTION,
        layer=CauseLayer.CUSTOMER,
        label="Authentication friction",
        transient=True,
        retryable=True,
        organic_multiplier=1.20,
        narrative="The customer dropped out of an OTP or 3DS step rather than refusing to pay.",
        affinity={
            ActionType.RETRY_PAYMENT: 1.20,
            ActionType.PAYMENT_LINK: 1.35,
            ActionType.ALT_PAYMENT_METHOD: 1.25,
            ActionType.WHATSAPP: 1.10,
        },
    ),
    RootCause.EXPIRED_INSTRUMENT: CauseProfile(
        cause=RootCause.EXPIRED_INSTRUMENT,
        layer=CauseLayer.CUSTOMER,
        label="Expired payment instrument",
        transient=False,
        retryable=False,
        organic_multiplier=0.55,
        narrative="Stored credentials are no longer chargeable, so the customer must supply new ones.",
        affinity={
            ActionType.RETRY_PAYMENT: 0.12,
            ActionType.PAYMENT_LINK: 1.45,
            ActionType.ALT_PAYMENT_METHOD: 1.50,
            ActionType.WHATSAPP: 1.20,
        },
    ),
    RootCause.WRONG_INSTRUMENT_DETAILS: CauseProfile(
        cause=RootCause.WRONG_INSTRUMENT_DETAILS,
        layer=CauseLayer.CUSTOMER,
        label="Incorrect instrument details",
        transient=False,
        retryable=False,
        organic_multiplier=0.70,
        narrative="The VPA or card details do not resolve, so a corrected instrument is required.",
        affinity={
            ActionType.RETRY_PAYMENT: 0.18,
            ActionType.PAYMENT_LINK: 1.40,
            ActionType.ALT_PAYMENT_METHOD: 1.40,
        },
    ),
    RootCause.ROUTE_TIMEOUT: CauseProfile(
        cause=RootCause.ROUTE_TIMEOUT,
        layer=CauseLayer.PAYMENT,
        label="Gateway route timeout",
        transient=True,
        retryable=True,
        organic_multiplier=1.30,
        narrative="The route did not respond in time. Payment state is uncertain until verified.",
        affinity={
            ActionType.RETRY_PAYMENT: 1.60,
            ActionType.ALT_PAYMENT_METHOD: 1.30,
            ActionType.PAYMENT_LINK: 1.05,
        },
    ),
}

CAUSE_LIBRARY.update(
    {
        RootCause.ROUTE_DEGRADATION: CauseProfile(
            cause=RootCause.ROUTE_DEGRADATION,
            layer=CauseLayer.SYSTEMIC,
            label="Payment route degradation",
            transient=True,
            retryable=False,
            organic_multiplier=1.25,
            narrative="Failures are concentrated on one route, so retrying adds load without adding revenue.",
            affinity={
                ActionType.RETRY_PAYMENT: 0.35,
                ActionType.ALT_PAYMENT_METHOD: 1.60,
                ActionType.PAYMENT_LINK: 1.10,
                ActionType.WHATSAPP: 0.95,
            },
        ),
        RootCause.METHOD_DEGRADATION: CauseProfile(
            cause=RootCause.METHOD_DEGRADATION,
            layer=CauseLayer.SYSTEMIC,
            label="Payment method degradation",
            transient=True,
            retryable=False,
            organic_multiplier=1.20,
            narrative="An entire method is underperforming its baseline; steer volume elsewhere.",
            affinity={
                ActionType.RETRY_PAYMENT: 0.40,
                ActionType.ALT_PAYMENT_METHOD: 1.70,
                ActionType.PAYMENT_LINK: 1.15,
            },
        ),
        RootCause.CHECKOUT_LATENCY: CauseProfile(
            cause=RootCause.CHECKOUT_LATENCY,
            layer=CauseLayer.MERCHANT,
            label="Checkout latency",
            transient=True,
            retryable=True,
            organic_multiplier=1.05,
            narrative="The customer waited too long on the merchant checkout before the attempt landed.",
            affinity={
                ActionType.PAYMENT_LINK: 1.40,
                ActionType.WHATSAPP: 1.15,
                ActionType.RETRY_PAYMENT: 0.60,
            },
        ),
        RootCause.MERCHANT_MISCONFIGURATION: CauseProfile(
            cause=RootCause.MERCHANT_MISCONFIGURATION,
            layer=CauseLayer.MERCHANT,
            label="Merchant configuration issue",
            transient=False,
            retryable=False,
            organic_multiplier=0.60,
            narrative="The attempt cannot succeed until a merchant-side setting is corrected.",
            affinity={
                ActionType.RETRY_PAYMENT: 0.30,
                ActionType.HUMAN_ESCALATION: 1.60,
                ActionType.PAYMENT_LINK: 0.90,
            },
        ),
        RootCause.PRICE_SENSITIVITY: CauseProfile(
            cause=RootCause.PRICE_SENSITIVITY,
            layer=CauseLayer.INTENT,
            label="Price sensitivity",
            transient=False,
            retryable=False,
            organic_multiplier=0.65,
            narrative="The cart was priced above the customer threshold rather than blocked by a failure.",
            affinity={
                ActionType.DISCOUNT: 1.70,
                ActionType.WHATSAPP: 1.10,
                ActionType.EMAIL: 0.95,
                ActionType.PAYMENT_LINK: 0.95,
                ActionType.RETRY_PAYMENT: 0.20,
                ActionType.VOICE: 0.70,
                ActionType.HUMAN_ESCALATION: 0.60,
            },
        ),
        RootCause.SESSION_DROPOFF: CauseProfile(
            cause=RootCause.SESSION_DROPOFF,
            layer=CauseLayer.INTENT,
            label="Session drop-off",
            transient=True,
            retryable=False,
            organic_multiplier=0.90,
            narrative="Intent was real and the session simply ended; a direct link often finishes the job.",
            affinity={
                ActionType.PAYMENT_LINK: 1.50,
                ActionType.WHATSAPP: 1.30,
                ActionType.SMS: 1.10,
                ActionType.DISCOUNT: 1.05,
            },
        ),
        RootCause.DELIBERATE_ABANDONMENT: CauseProfile(
            cause=RootCause.DELIBERATE_ABANDONMENT,
            layer=CauseLayer.INTENT,
            label="Deliberate abandonment",
            transient=False,
            retryable=False,
            organic_multiplier=0.30,
            narrative="Comparison shopping or a changed mind. Contacting this customer mostly buys friction.",
            affinity={
                ActionType.DISCOUNT: 1.10,
                ActionType.WHATSAPP: 0.70,
                ActionType.SMS: 0.55,
                ActionType.EMAIL: 0.60,
                ActionType.PAYMENT_LINK: 0.70,
                ActionType.ALT_PAYMENT_METHOD: 0.50,
                ActionType.RETRY_PAYMENT: 0.15,
                ActionType.VOICE: 0.45,
                ActionType.HUMAN_ESCALATION: 0.50,
            },
        ),
        RootCause.BUYER_CASHFLOW: CauseProfile(
            cause=RootCause.BUYER_CASHFLOW,
            layer=CauseLayer.RECEIVABLE,
            label="Buyer cashflow delay",
            transient=True,
            retryable=False,
            organic_multiplier=1.15,
            narrative="The buyer intends to pay but is sequencing payables, which makes a promise worth capturing.",
            affinity={
                ActionType.PROMISE_FOLLOWUP: 1.60,
                ActionType.VOICE: 1.30,
                ActionType.HUMAN_ESCALATION: 1.35,
                ActionType.EMAIL: 1.10,
            },
        ),
        RootCause.APPROVAL_BOTTLENECK: CauseProfile(
            cause=RootCause.APPROVAL_BOTTLENECK,
            layer=CauseLayer.RECEIVABLE,
            label="Internal approval bottleneck",
            transient=True,
            retryable=False,
            organic_multiplier=1.25,
            narrative="The invoice is stuck in the buyer approval chain rather than disputed.",
            affinity={
                ActionType.EMAIL: 1.50,
                ActionType.HUMAN_ESCALATION: 1.35,
                ActionType.WHATSAPP: 1.20,
                ActionType.PROMISE_FOLLOWUP: 1.25,
            },
        ),
        RootCause.DISPUTED_INVOICE: CauseProfile(
            cause=RootCause.DISPUTED_INVOICE,
            layer=CauseLayer.RECEIVABLE,
            label="Disputed invoice",
            transient=False,
            retryable=False,
            organic_multiplier=0.40,
            narrative="A commercial disagreement blocks payment, so automation cannot resolve it.",
            affinity={
                ActionType.HUMAN_ESCALATION: 1.90,
                ActionType.VOICE: 1.20,
                ActionType.EMAIL: 0.80,
                ActionType.SMS: 0.40,
            },
        ),
        RootCause.UNKNOWN: CauseProfile(
            cause=RootCause.UNKNOWN,
            layer=CauseLayer.PAYMENT,
            label="Undetermined",
            transient=False,
            retryable=True,
            organic_multiplier=1.0,
            narrative="Evidence is insufficient for a confident diagnosis; the safest action wins.",
            affinity={},
        ),
        RootCause.MANDATE_ABSENT: CauseProfile(
            cause=RootCause.MANDATE_ABSENT,
            layer=CauseLayer.REGULATORY,
            label="No mandate on file",
            transient=False,
            retryable=False,
            organic_multiplier=0.15,
            narrative="No valid mandate exists for this customer; retrying is guaranteed to fail.",
            affinity={ActionType.REREGISTER_MANDATE: 1.8, ActionType.SWITCH_RAIL: 1.3, ActionType.RETRY_PAYMENT: 0.05},
        ),
        RootCause.MANDATE_REVOKED: CauseProfile(
            cause=RootCause.MANDATE_REVOKED,
            layer=CauseLayer.REGULATORY,
            label="Mandate revoked by customer",
            transient=False,
            retryable=False,
            organic_multiplier=0.10,
            narrative="Customer revoked the mandate; only re-registration can resolve this.",
            affinity={ActionType.REREGISTER_MANDATE: 1.9, ActionType.RETRY_PAYMENT: 0.03},
        ),
        RootCause.MANDATE_CAP_EXCEEDED: CauseProfile(
            cause=RootCause.MANDATE_CAP_EXCEEDED,
            layer=CauseLayer.REGULATORY,
            label="Charge exceeds mandate cap",
            transient=False,
            retryable=False,
            organic_multiplier=0.20,
            narrative="Subscription amount exceeds authorised mandate cap; needs cap amendment.",
            affinity={ActionType.AMEND_MANDATE_CAP: 1.85, ActionType.REREGISTER_MANDATE: 1.2, ActionType.RETRY_PAYMENT: 0.04},
        ),
        RootCause.PDN_MISSING: CauseProfile(
            cause=RootCause.PDN_MISSING,
            layer=CauseLayer.REGULATORY,
            label="Pre-debit notification not delivered",
            transient=False,
            retryable=False,
            organic_multiplier=0.25,
            narrative="RBI requires PDN 24h before debit; without it the debit is blocked.",
            affinity={ActionType.SEND_PDN: 1.9, ActionType.WHATSAPP: 1.1, ActionType.RETRY_PAYMENT: 0.06},
        ),
        RootCause.AFA_THRESHOLD_BREACH: CauseProfile(
            cause=RootCause.AFA_THRESHOLD_BREACH,
            layer=CauseLayer.REGULATORY,
            label="Amount exceeds AFA-free ceiling",
            transient=False,
            retryable=False,
            organic_multiplier=0.18,
            narrative="Amount > ₹15,000 requires fresh customer authentication per RBI e-mandate.",
            affinity={ActionType.REREGISTER_MANDATE: 1.7, ActionType.PAYMENT_LINK: 1.25, ActionType.RETRY_PAYMENT: 0.05},
        ),
        RootCause.EXECUTION_WINDOW_MISS: CauseProfile(
            cause=RootCause.EXECUTION_WINDOW_MISS,
            layer=CauseLayer.REGULATORY,
            label="Outside NPCI execution window",
            transient=True,
            retryable=False,
            organic_multiplier=0.90,
            narrative="Presented during NPCI peak window 10:00-13:00 IST; technical decline, not customer fault.",
            affinity={ActionType.RETRY_PAYMENT: 1.1, ActionType.SEND_PDN: 0.95},
        ),
    }
)


#: Prior weights from an observed failure code to candidate causes. The investigator
#: re-weights these with transaction, customer and systemic evidence.
FAILURE_CAUSE_PRIORS: dict[FailureCode, tuple[tuple[RootCause, float], ...]] = {
    FailureCode.INSUFFICIENT_FUNDS: ((RootCause.INSUFFICIENT_BALANCE, 0.92),),
    FailureCode.AUTHENTICATION_FAILED: (
        (RootCause.AUTH_FRICTION, 0.74),
        (RootCause.TRANSIENT_BANK_DECLINE, 0.18),
    ),
    FailureCode.OTP_TIMEOUT: ((RootCause.AUTH_FRICTION, 0.88),),
    FailureCode.CARD_EXPIRED: ((RootCause.EXPIRED_INSTRUMENT, 0.95),),
    FailureCode.INVALID_VPA: ((RootCause.WRONG_INSTRUMENT_DETAILS, 0.90),),
    FailureCode.PAYMENT_CANCELLED: (
        (RootCause.DELIBERATE_ABANDONMENT, 0.62),
        (RootCause.AUTH_FRICTION, 0.24),
    ),
    FailureCode.LIMIT_EXCEEDED: (
        (RootCause.HARD_BANK_DECLINE, 0.58),
        (RootCause.INSUFFICIENT_BALANCE, 0.30),
    ),
    FailureCode.ISSUER_DECLINED: (
        (RootCause.TRANSIENT_BANK_DECLINE, 0.56),
        (RootCause.HARD_BANK_DECLINE, 0.34),
    ),
    FailureCode.ISSUER_UNAVAILABLE: (
        (RootCause.ROUTE_DEGRADATION, 0.55),
        (RootCause.TRANSIENT_BANK_DECLINE, 0.35),
    ),
    FailureCode.PSP_UNAVAILABLE: (
        (RootCause.METHOD_DEGRADATION, 0.60),
        (RootCause.ROUTE_DEGRADATION, 0.30),
    ),
    FailureCode.GATEWAY_TIMEOUT: (
        (RootCause.ROUTE_TIMEOUT, 0.72),
        (RootCause.ROUTE_DEGRADATION, 0.20),
    ),
    FailureCode.GATEWAY_ERROR: (
        (RootCause.ROUTE_DEGRADATION, 0.48),
        (RootCause.ROUTE_TIMEOUT, 0.30),
    ),
    FailureCode.CHECKOUT_ERROR: ((RootCause.CHECKOUT_LATENCY, 0.70),),
    FailureCode.CONFIGURATION_ERROR: ((RootCause.MERCHANT_MISCONFIGURATION, 0.86),),
    FailureCode.CHECKOUT_TIMEOUT: (
        (RootCause.SESSION_DROPOFF, 0.66),
        (RootCause.CHECKOUT_LATENCY, 0.22),
    ),
    FailureCode.PRICE_HESITATION: (
        (RootCause.PRICE_SENSITIVITY, 0.70),
        (RootCause.DELIBERATE_ABANDONMENT, 0.22),
    ),
    FailureCode.METHOD_UNAVAILABLE: ((RootCause.METHOD_DEGRADATION, 0.68),),
    FailureCode.INVOICE_UNPAID: (
        (RootCause.BUYER_CASHFLOW, 0.48),
        (RootCause.APPROVAL_BOTTLENECK, 0.34),
        (RootCause.DISPUTED_INVOICE, 0.14),
    ),
    FailureCode.PROMISE_BROKEN: (
        (RootCause.BUYER_CASHFLOW, 0.60),
        (RootCause.DISPUTED_INVOICE, 0.26),
    ),
    FailureCode.MANDATE_NOT_FOUND: ((RootCause.MANDATE_ABSENT, 0.96),),
    FailureCode.MANDATE_REVOKED: ((RootCause.MANDATE_REVOKED, 0.97),),
    FailureCode.MANDATE_AMOUNT_EXCEEDS: ((RootCause.MANDATE_CAP_EXCEEDED, 0.95),),
    FailureCode.PDN_NOT_DELIVERED: ((RootCause.PDN_MISSING, 0.94),),
    FailureCode.AFA_REQUIRED: ((RootCause.AFA_THRESHOLD_BREACH, 0.96),),
    FailureCode.MANDATE_PAUSED: ((RootCause.MANDATE_REVOKED, 0.70), (RootCause.MANDATE_ABSENT, 0.20)),
}

FAILURE_LABELS: dict[FailureCode, str] = {
    FailureCode.INSUFFICIENT_FUNDS: "Insufficient funds at capture",
    FailureCode.AUTHENTICATION_FAILED: "Authentication failed",
    FailureCode.CARD_EXPIRED: "Card expired",
    FailureCode.INVALID_VPA: "Invalid UPI handle",
    FailureCode.PAYMENT_CANCELLED: "Cancelled by customer",
    FailureCode.OTP_TIMEOUT: "OTP not submitted in time",
    FailureCode.LIMIT_EXCEEDED: "Transaction limit exceeded",
    FailureCode.ISSUER_DECLINED: "Declined by issuing bank",
    FailureCode.ISSUER_UNAVAILABLE: "Issuing bank unavailable",
    FailureCode.PSP_UNAVAILABLE: "UPI PSP unavailable",
    FailureCode.GATEWAY_TIMEOUT: "Gateway timed out",
    FailureCode.GATEWAY_ERROR: "Gateway error",
    FailureCode.CHECKOUT_ERROR: "Checkout error",
    FailureCode.CONFIGURATION_ERROR: "Payment configuration error",
    FailureCode.CHECKOUT_TIMEOUT: "Checkout session expired",
    FailureCode.PRICE_HESITATION: "Dropped at order summary",
    FailureCode.METHOD_UNAVAILABLE: "Preferred method unavailable",
    FailureCode.INVOICE_UNPAID: "Invoice past due date",
    FailureCode.PROMISE_BROKEN: "Promise to pay not honoured",
    FailureCode.MANDATE_NOT_FOUND: "No mandate on file",
    FailureCode.MANDATE_REVOKED: "Mandate revoked by customer",
    FailureCode.MANDATE_AMOUNT_EXCEEDS: "Charge exceeds mandate cap",
    FailureCode.PDN_NOT_DELIVERED: "Pre-debit notification not delivered",
    FailureCode.AFA_REQUIRED: "Additional factor authentication required",
    FailureCode.MANDATE_PAUSED: "Mandate paused",
}

#: Display names for the four loss classes, matching the wording the dashboard uses.
KIND_LABELS: dict[EventKind, str] = {
    EventKind.PAYMENT_FAILURE: "Payment failures",
    EventKind.CART_ABANDONMENT: "Checkout abandonment",
    EventKind.SUBSCRIPTION_FAILURE: "Subscription failures",
    EventKind.OVERDUE_INVOICE: "Overdue invoices",
}

#: Display names for payment methods; acronyms must not be title-cased into words.
METHOD_LABELS: dict[PaymentMethod, str] = {
    PaymentMethod.UPI: "UPI",
    PaymentMethod.CARD: "Card",
    PaymentMethod.NETBANKING: "Netbanking",
    PaymentMethod.WALLET: "Wallet",
    PaymentMethod.EMI: "EMI",
    PaymentMethod.BANK_TRANSFER: "Bank transfer",
}

#: Healthier alternatives suggested when a method degrades.
METHOD_FALLBACKS: dict[PaymentMethod, tuple[PaymentMethod, ...]] = {
    PaymentMethod.UPI: (PaymentMethod.CARD, PaymentMethod.NETBANKING, PaymentMethod.WALLET),
    PaymentMethod.CARD: (PaymentMethod.UPI, PaymentMethod.NETBANKING, PaymentMethod.EMI),
    PaymentMethod.NETBANKING: (PaymentMethod.UPI, PaymentMethod.CARD),
    PaymentMethod.WALLET: (PaymentMethod.UPI, PaymentMethod.CARD),
    PaymentMethod.EMI: (PaymentMethod.CARD, PaymentMethod.NETBANKING),
    PaymentMethod.BANK_TRANSFER: (PaymentMethod.UPI, PaymentMethod.NETBANKING),
}

ISSUERS: tuple[str, ...] = (
    "HDFC Bank",
    "ICICI Bank",
    "State Bank of India",
    "Axis Bank",
    "Kotak Mahindra",
    "Paytm Payments Bank",
    "Yes Bank",
    "IndusInd Bank",
)

ROUTES: tuple[str, ...] = (
    "route-upi-alpha",
    "route-upi-beta",
    "route-card-primary",
    "route-card-secondary",
    "route-nb-primary",
    "route-wallet-primary",
)


def intervention(action: ActionType) -> Intervention:
    return INTERVENTIONS[action]


def cause_profile(cause: RootCause) -> CauseProfile:
    return CAUSE_LIBRARY.get(cause, CAUSE_LIBRARY[RootCause.UNKNOWN])


def affinity(cause: RootCause, action: ActionType) -> float:
    return cause_profile(cause).affinity.get(action, 1.0)
