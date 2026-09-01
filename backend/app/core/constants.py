"""Domain vocabulary shared by engines, agents, persistence and the API."""

from __future__ import annotations

from enum import StrEnum


class EventKind(StrEnum):
    """A class of revenue loss Revyn can detect and recover."""

    PAYMENT_FAILURE = "payment_failure"
    CART_ABANDONMENT = "cart_abandonment"
    SUBSCRIPTION_FAILURE = "subscription_failure"
    OVERDUE_INVOICE = "overdue_invoice"


class EventStatus(StrEnum):
    AT_RISK = "at_risk"
    IN_RECOVERY = "in_recovery"
    RECOVERED = "recovered"
    LOST = "lost"
    SUPPRESSED = "suppressed"


class PaymentMethod(StrEnum):
    UPI = "upi"
    CARD = "card"
    NETBANKING = "netbanking"
    WALLET = "wallet"
    EMI = "emi"
    BANK_TRANSFER = "bank_transfer"


class CustomerSegment(StrEnum):
    VIP = "vip"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NEW = "new"


class CommunicationPreference(StrEnum):
    WHATSAPP = "whatsapp"
    SMS = "sms"
    EMAIL = "email"
    VOICE = "voice"


class Cohort(StrEnum):
    """A/B split that keeps incremental-recovery claims honest."""

    CONTROL = "control"
    TREATMENT = "treatment"


class FailureCode(StrEnum):
    # Customer side
    INSUFFICIENT_FUNDS = "insufficient_funds"
    AUTHENTICATION_FAILED = "authentication_failed"
    CARD_EXPIRED = "card_expired"
    INVALID_VPA = "invalid_vpa"
    PAYMENT_CANCELLED = "payment_cancelled"
    OTP_TIMEOUT = "otp_timeout"
    LIMIT_EXCEEDED = "limit_exceeded"
    # Payment side
    ISSUER_DECLINED = "issuer_declined"
    ISSUER_UNAVAILABLE = "issuer_unavailable"
    PSP_UNAVAILABLE = "psp_unavailable"
    GATEWAY_TIMEOUT = "gateway_timeout"
    GATEWAY_ERROR = "gateway_error"
    # Merchant side
    CHECKOUT_ERROR = "checkout_error"
    CONFIGURATION_ERROR = "configuration_error"
    # Non-payment loss classes
    CHECKOUT_TIMEOUT = "checkout_timeout"
    PRICE_HESITATION = "price_hesitation"
    METHOD_UNAVAILABLE = "method_unavailable"
    INVOICE_UNPAID = "invoice_unpaid"
    PROMISE_BROKEN = "promise_broken"


class CauseLayer(StrEnum):
    CUSTOMER = "customer"
    PAYMENT = "payment"
    MERCHANT = "merchant"
    SYSTEMIC = "systemic"
    INTENT = "intent"
    RECEIVABLE = "receivable"


class RootCause(StrEnum):
    INSUFFICIENT_BALANCE = "insufficient_balance"
    AUTH_FRICTION = "auth_friction"
    EXPIRED_INSTRUMENT = "expired_instrument"
    WRONG_INSTRUMENT_DETAILS = "wrong_instrument_details"
    DELIBERATE_ABANDONMENT = "deliberate_abandonment"
    TRANSIENT_BANK_DECLINE = "transient_bank_decline"
    HARD_BANK_DECLINE = "hard_bank_decline"
    ROUTE_TIMEOUT = "route_timeout"
    CHECKOUT_LATENCY = "checkout_latency"
    MERCHANT_MISCONFIGURATION = "merchant_misconfiguration"
    ROUTE_DEGRADATION = "route_degradation"
    METHOD_DEGRADATION = "method_degradation"
    PRICE_SENSITIVITY = "price_sensitivity"
    SESSION_DROPOFF = "session_dropoff"
    BUYER_CASHFLOW = "buyer_cashflow"
    APPROVAL_BOTTLENECK = "approval_bottleneck"
    DISPUTED_INVOICE = "disputed_invoice"
    UNKNOWN = "unknown"


class ActionType(StrEnum):
    DO_NOTHING = "do_nothing"
    RETRY_PAYMENT = "retry_payment"
    PAYMENT_LINK = "payment_link"
    ALT_PAYMENT_METHOD = "alt_payment_method"
    WHATSAPP = "whatsapp"
    SMS = "sms"
    EMAIL = "email"
    VOICE = "voice"
    DISCOUNT = "discount"
    HUMAN_ESCALATION = "human_escalation"
    PROMISE_FOLLOWUP = "promise_followup"


# Actions that consume a slot of the customer contact budget.
CONTACT_ACTIONS: frozenset[ActionType] = frozenset(
    {
        ActionType.PAYMENT_LINK,
        ActionType.WHATSAPP,
        ActionType.SMS,
        ActionType.EMAIL,
        ActionType.VOICE,
        ActionType.DISCOUNT,
        ActionType.PROMISE_FOLLOWUP,
    }
)

# Actions that move money through the payment gateway.
FINANCIAL_ACTIONS: frozenset[ActionType] = frozenset(
    {ActionType.RETRY_PAYMENT, ActionType.PAYMENT_LINK, ActionType.ALT_PAYMENT_METHOD}
)


class ActionStatus(StrEnum):
    PLANNED = "planned"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    EXECUTING = "executing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class JourneyState(StrEnum):
    DETECTED = "detected"
    ANALYZING = "analyzing"
    PLANNED = "planned"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    RECOVERED = "recovered"
    CLOSED = "closed"
    BLOCKED = "blocked"
    FAILED = "failed"
    PAUSED = "paused"
    EXPIRED = "expired"


TERMINAL_JOURNEY_STATES: frozenset[JourneyState] = frozenset(
    {
        JourneyState.RECOVERED,
        JourneyState.CLOSED,
        JourneyState.BLOCKED,
        JourneyState.FAILED,
        JourneyState.EXPIRED,
    }
)


class PolicyVerdict(StrEnum):
    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    BLOCK = "block"


class PolicyRule(StrEnum):
    """Stable identifiers so every gated action can explain itself."""

    AUTOMATION_DISABLED = "automation_disabled"
    JOURNEY_PAUSED = "journey_paused"
    CUSTOMER_OPTED_OUT = "customer_opted_out"
    CONTACT_BUDGET_EXHAUSTED = "contact_budget_exhausted"
    RETRY_BUDGET_EXHAUSTED = "retry_budget_exhausted"
    DISCOUNT_BUDGET_EXHAUSTED = "discount_budget_exhausted"
    VOICE_BUDGET_EXHAUSTED = "voice_budget_exhausted"
    COOLDOWN_ACTIVE = "cooldown_active"
    QUIET_HOURS = "quiet_hours"
    HIGH_VALUE_APPROVAL = "high_value_approval"
    DISCOUNT_APPROVAL = "discount_approval"
    VOICE_APPROVAL = "voice_approval"
    CONFIDENCE_BELOW_THRESHOLD = "confidence_below_threshold"
    VALUE_BELOW_THRESHOLD = "value_below_threshold"
    ALREADY_RECOVERED = "already_recovered"
    DEGRADATION_ACTIVE = "degradation_active"
    DUPLICATE_ACTION = "duplicate_action"
    COLLISION_DETECTED = "collision_detected"


class GatewayStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PENDING = "pending"
    # The call did not resolve - state must be verified before any retry.
    AMBIGUOUS = "ambiguous"


class AuditEvent(StrEnum):
    EVENT_DETECTED = "event_detected"
    DIAGNOSIS_COMPLETED = "diagnosis_completed"
    DECISION_MADE = "decision_made"
    POLICY_EVALUATED = "policy_evaluated"
    ACTION_SCHEDULED = "action_scheduled"
    ACTION_EXECUTED = "action_executed"
    ACTION_BLOCKED = "action_blocked"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_REJECTED = "approval_rejected"
    OUTCOME_VERIFIED = "outcome_verified"
    RECOVERY_BOOKED = "recovery_booked"
    JOURNEY_TRANSITION = "journey_transition"
    JOURNEY_CLOSED = "journey_closed"
    STRATEGY_UPDATED = "strategy_updated"
    DEGRADATION_DETECTED = "degradation_detected"
    DEGRADATION_CLEARED = "degradation_cleared"
    POLICY_UPDATED = "policy_updated"
    KILL_SWITCH_TOGGLED = "kill_switch_toggled"


class Actor(StrEnum):
    SYSTEM = "system"
    AGENT = "agent"
    HUMAN = "human"
    GATEWAY = "gateway"


class DegradationSeverity(StrEnum):
    NONE = "none"
    WATCH = "watch"
    ELEVATED = "elevated"
    CRITICAL = "critical"


class AttributionMethod(StrEnum):
    """How organic recovery - money that would have arrived anyway - is estimated."""

    COHORT = "cohort"
    MODEL = "model"
    BLENDED = "blended"


class AgentName(StrEnum):
    SENTINEL = "sentinel"
    INVESTIGATOR = "investigator"
    STRATEGIST = "strategist"
    OPTIMIZER = "optimizer"
    POLICY_OFFICER = "policy_officer"
    EXECUTOR = "executor"
    VERIFIER = "verifier"
    LEARNER = "learner"
