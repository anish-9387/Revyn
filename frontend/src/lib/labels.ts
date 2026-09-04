/** Human-readable labels for API enums, kept in one place. */

import type { ActionStatus, EventKind, JourneyState, PolicyVerdict } from "@/lib/types";

export const LOSS_CLASS_LABEL: Record<EventKind, string> = {
  payment_failure: "Payment failures",
  cart_abandonment: "Checkout abandonment",
  subscription_failure: "Subscription failures",
  overdue_invoice: "Overdue invoices",
};

export const LOSS_CLASS_SHORT: Record<EventKind, string> = {
  payment_failure: "Payments",
  cart_abandonment: "Abandonment",
  subscription_failure: "Subscriptions",
  overdue_invoice: "Invoices",
};

export const LOSS_CLASS_ORDER: EventKind[] = [
  "payment_failure",
  "cart_abandonment",
  "subscription_failure",
  "overdue_invoice",
];

export const ACTION_LABEL: Record<string, string> = {
  do_nothing: "Do nothing",
  retry_payment: "Delayed retry",
  payment_link: "Payment link",
  alt_payment_method: "Alternative method",
  whatsapp: "WhatsApp nudge",
  sms: "SMS reminder",
  email: "Email reminder",
  voice: "Voice agent call",
  discount: "Recovery offer",
  human_escalation: "Human escalation",
  promise_followup: "Promise follow-up",
};

export const CAUSE_LABEL: Record<string, string> = {
  insufficient_balance: "Insufficient funds",
  auth_friction: "Authentication friction",
  expired_instrument: "Expired instrument",
  wrong_instrument_details: "Incorrect instrument details",
  deliberate_abandonment: "Deliberate abandonment",
  transient_bank_decline: "Temporary bank decline",
  hard_bank_decline: "Hard issuer decline",
  route_timeout: "Gateway route timeout",
  checkout_latency: "Checkout latency",
  merchant_misconfiguration: "Merchant misconfiguration",
  route_degradation: "Route degradation",
  method_degradation: "Method degradation",
  price_sensitivity: "Price sensitivity",
  session_dropoff: "Session drop-off",
  buyer_cashflow: "Buyer cashflow delay",
  approval_bottleneck: "Approval bottleneck",
  disputed_invoice: "Disputed invoice",
  unknown: "Undetermined",
};

/** Mirrors the backend's method names, so prose and tables agree on casing. */
export const METHOD_LABEL: Record<string, string> = {
  upi: "UPI",
  card: "Card",
  netbanking: "Netbanking",
  wallet: "Wallet",
  emi: "EMI",
  bank_transfer: "Bank transfer",
};

export const AGENT_LABEL: Record<string, string> = {
  sentinel: "Sentinel",
  investigator: "Investigator",
  strategist: "Strategist",
  optimizer: "Optimizer",
  policy_officer: "Policy Officer",
  executor: "Executor",
  verifier: "Verifier",
  learner: "Learner",
};

export type Tone = "neutral" | "good" | "warning" | "serious" | "critical" | "accent";

export const JOURNEY_TONE: Record<JourneyState, Tone> = {
  detected: "neutral",
  analyzing: "accent",
  planned: "accent",
  awaiting_approval: "warning",
  approved: "accent",
  executing: "accent",
  verifying: "accent",
  recovered: "good",
  closed: "neutral",
  blocked: "serious",
  failed: "critical",
  paused: "warning",
  expired: "neutral",
};

export const ACTION_STATUS_TONE: Record<ActionStatus, Tone> = {
  planned: "neutral",
  awaiting_approval: "warning",
  approved: "accent",
  executing: "accent",
  succeeded: "good",
  failed: "critical",
  blocked: "serious",
  cancelled: "neutral",
  skipped: "neutral",
};

export const VERDICT_TONE: Record<PolicyVerdict, Tone> = {
  allow: "good",
  require_approval: "warning",
  block: "critical",
};

/** Matches the wording of the guardrail filter on the decisions page. */
export const VERDICT_LABEL: Record<PolicyVerdict, string> = {
  allow: "Allowed",
  require_approval: "Needed approval",
  block: "Blocked",
};

export const SEVERITY_TONE: Record<string, Tone> = {
  none: "neutral",
  watch: "warning",
  elevated: "serious",
  critical: "critical",
};

export function actionLabel(action: string): string {
  return ACTION_LABEL[action] ?? action.replace(/_/g, " ");
}

export function agentLabel(name: string): string {
  return AGENT_LABEL[name] ?? termLabel(name);
}

export function methodLabel(method: string): string {
  return METHOD_LABEL[method] ?? termLabel(method);
}

export function causeLabel(cause: string): string {
  return CAUSE_LABEL[cause] ?? cause.replace(/_/g, " ");
}

/** Mirrors the backend's gateway failure-code wording; a raw code reads like a leaked key. */
export const FAILURE_CODE_LABEL: Record<string, string> = {
  insufficient_funds: "Insufficient funds at capture",
  authentication_failed: "Authentication failed",
  card_expired: "Card expired",
  invalid_vpa: "Invalid UPI handle",
  payment_cancelled: "Cancelled by customer",
  otp_timeout: "OTP not submitted in time",
  limit_exceeded: "Transaction limit exceeded",
  issuer_declined: "Declined by issuing bank",
  issuer_unavailable: "Issuing bank unavailable",
  psp_unavailable: "UPI PSP unavailable",
  gateway_timeout: "Gateway timed out",
  gateway_error: "Gateway error",
  checkout_error: "Checkout error",
  configuration_error: "Payment configuration error",
  checkout_timeout: "Checkout session expired",
  price_hesitation: "Dropped at order summary",
  method_unavailable: "Preferred method unavailable",
  invoice_unpaid: "Invoice past due date",
  promise_broken: "Promise to pay not honoured",
};

export function failureCodeLabel(code: string): string {
  return FAILURE_CODE_LABEL[code] ?? termLabel(code);
}

const ACRONYMS: Record<string, string> = {
  upi: "UPI",
  emi: "EMI",
  neft: "NEFT",
  imps: "IMPS",
  vip: "VIP",
  sms: "SMS",
  otp: "OTP",
  cvv: "CVV",
  b2b: "B2B",
  b2c: "B2C",
};

/** Payments vocabulary arrives in mixed casing; acronyms must not be title-cased into words. */
export function termLabel(value: string): string {
  return value
    .replace(/[_-]+/g, " ")
    .split(" ")
    .filter(Boolean)
    .map((word) => ACRONYMS[word.toLowerCase()] ?? word[0].toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

/** Field names a simulation reports back as changed, in the wording the guardrails page uses. */
export const POLICY_FIELD_LABEL: Record<string, string> = {
  max_contacts: "Maximum contacts",
  max_retries: "Maximum retries",
  max_discount_offers: "Maximum discount offers",
  max_discount_pct: "Maximum discount",
  min_confidence: "Minimum confidence",
  min_expected_value_paise: "Minimum expected value",
  human_approval_amount_paise: "Human approval above",
  degradation_retry_guard: "Degradation retry guard",
  quiet_hours_enforced: "Quiet hours",
};

/** A strategy key is `loss class | cause family | value band`; read it as a sentence, not a key. */
export function strategyLabel(key: string): string {
  const [kind, family, band] = key.split("|");
  const head = LOSS_CLASS_LABEL[kind as EventKind] ?? termLabel(kind ?? key);
  return [head, family ? termLabel(family) : null, band ? `${termLabel(band)} ticket` : null]
    .filter(Boolean)
    .join(" · ");
}
