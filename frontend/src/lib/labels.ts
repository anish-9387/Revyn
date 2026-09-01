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

export const SEVERITY_TONE: Record<string, Tone> = {
  none: "neutral",
  watch: "warning",
  elevated: "serious",
  critical: "critical",
};

export function actionLabel(action: string): string {
  return ACTION_LABEL[action] ?? action.replace(/_/g, " ");
}

export function causeLabel(cause: string): string {
  return CAUSE_LABEL[cause] ?? cause.replace(/_/g, " ");
}
