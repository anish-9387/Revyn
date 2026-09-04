/** Response shapes mirrored from the Revyn API. Money is always integer paise. */

export type EventKind =
  | "payment_failure"
  | "cart_abandonment"
  | "subscription_failure"
  | "overdue_invoice";

export type EventStatus = "at_risk" | "in_recovery" | "recovered" | "lost" | "suppressed";

export type JourneyState =
  | "detected"
  | "analyzing"
  | "planned"
  | "awaiting_approval"
  | "approved"
  | "executing"
  | "verifying"
  | "recovered"
  | "closed"
  | "blocked"
  | "failed"
  | "paused"
  | "expired";

export type ActionStatus =
  | "planned"
  | "awaiting_approval"
  | "approved"
  | "executing"
  | "succeeded"
  | "failed"
  | "blocked"
  | "cancelled"
  | "skipped";

export type PolicyVerdict = "allow" | "require_approval" | "block";

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface Customer {
  id: string;
  external_ref: string;
  name: string;
  email: string;
  phone: string;
  segment: string;
  ltv_paise: number;
  average_order_value_paise: number;
  previous_payment_count: number;
  previous_success_rate: number;
  historical_recovery_rate: number;
  communication_preference: string;
  opted_out: boolean;
}

export interface RiskItem {
  id: string;
  external_ref: string;
  kind: EventKind;
  status: EventStatus;
  cohort: "control" | "treatment";
  amount_paise: number;
  occurred_at: string;
  payment_method: string;
  issuer: string;
  route: string;
  failure_code: string | null;
  failure_reason: string | null;
  retry_count: number;
  risk_score: number;
  urgency_score: number;
  priority_score: number;
  recovery_probability: number;
  organic_probability: number;
  expected_recovery_paise: number;
  root_cause: string;
  cause_layer: string | null;
  cause_confidence: number;
  recovered_amount_paise: number;
  customer: Customer;
  journey_id: string | null;
  journey_state: JourneyState | null;
}

export interface ActionOption {
  action: string;
  label: string;
  probability: number;
  uplift: number;
  expected_recovery_paise: number;
  expected_value_paise: number;
  intervention_cost_paise: number;
  discount_cost_paise: number;
  friction_cost_paise: number;
  systemic_penalty_paise: number;
  friction_score: number;
  discount_pct: number;
  verdict: PolicyVerdict;
  blocked_reasons: string[];
}

export interface AgentStep {
  agent: string;
  summary: string;
  detail: Record<string, unknown>;
  duration_ms: number;
}

export interface Decision {
  id: string;
  event_id: string;
  event_ref: string | null;
  amount_paise: number | null;
  journey_id: string | null;
  chosen_action: string;
  recovery_probability: number;
  organic_probability: number;
  uplift: number;
  expected_recovery_paise: number;
  expected_value_paise: number;
  policy_verdict: PolicyVerdict;
  policy_reasons: string[];
  alternatives: ActionOption[];
  rationale: string[];
  evidence: string[];
  agent_trace: AgentStep[];
  model_version: string;
  reasoning_provider: string;
  created_at: string;
}

export interface RecoveryAction {
  id: string;
  journey_id: string;
  decision_id: string | null;
  sequence: number;
  action_type: string;
  status: ActionStatus;
  scheduled_at: string;
  executed_at: string | null;
  cost_paise: number;
  friction_score: number;
  discount_pct: number;
  provider_ref: string | null;
  blocked_reasons: string[];
  error: string | null;
  result: Record<string, unknown>;
}

export interface PlanStep {
  action: string;
  label: string;
  delay_minutes: number;
  reason: string;
}

export interface Journey {
  id: string;
  event_id: string;
  event_ref: string | null;
  amount_paise: number | null;
  customer_name: string | null;
  customer_id: string;
  state: JourneyState;
  strategy_key: string;
  step_index: number;
  next_action_at: string | null;
  closed_at: string | null;
  close_reason: string | null;
  contacts_used: number;
  retries_used: number;
  discounts_used: number;
  voice_used: number;
  recovered_amount_paise: number;
  cost_paise: number;
  promise_date: string | null;
  promise_confidence: number;
  plan: PlanStep[];
  transitions: { from: string; to: string; at: string; reason: string }[];
  created_at: string;
}

export interface BudgetLine {
  used: number;
  limit: number;
}

export interface JourneyDetail extends Journey {
  event: RiskItem;
  actions: RecoveryAction[];
  decisions: Decision[];
  friction_budget: {
    contacts: BudgetLine;
    retries: BudgetLine;
    discounts: BudgetLine;
    voice: BudgetLine;
    exhausted: boolean;
    blocking: string[];
  };
}

export interface ApprovalItem {
  action: RecoveryAction;
  journey_id: string;
  event: RiskItem;
  reasons: string[];
  explanations: string[];
  decision: Decision | null;
}

export interface Policy {
  id: string;
  name: string;
  version: number;
  automation_enabled: boolean;
  paused: boolean;
  max_contacts: number;
  max_retries: number;
  max_discount_offers: number;
  max_voice_attempts: number;
  human_approval_amount_paise: number;
  discount_approval_pct: number;
  voice_approval_amount_paise: number;
  min_confidence: number;
  min_expected_value_paise: number;
  retry_delay_minutes: number;
  followup_delay_hours: number;
  contact_cooldown_minutes: number;
  journey_ttl_hours: number;
  quiet_hours_start: number;
  quiet_hours_end: number;
  quiet_hours_enforced: boolean;
  degradation_retry_guard: boolean;
  max_discount_pct: number;
  updated_at: string;
}

export interface CohortArm {
  cohort: string;
  events: number;
  revenue_at_risk_paise: number;
  recovered_events: number;
  recovered_paise: number;
  customer_contacts: number;
  cost_paise: number;
  recovery_rate: number;
  contacts_per_event: number;
}

export interface AbTest {
  control: CohortArm;
  treatment: CohortArm;
  recovery_rate_lift: number;
  contact_delta_per_event: number;
}

export interface ScopeHealth {
  scope_type: "route" | "method";
  scope_value: string;
  attempts: number;
  failures: number;
  observed_rate: number;
  baseline_rate: number;
  ratio: number;
  severity: "none" | "watch" | "elevated" | "critical";
  degraded: boolean;
  /** False below the attempt floor: the ratio is real but too thin to call. */
  scored: boolean;
}

export interface CalibrationBin {
  lower: number;
  upper: number;
  count: number;
  predicted: number;
  observed: number;
}

export interface ModelMetadata {
  trained: boolean;
  version?: string;
  algorithm?: string;
  trained_at?: string;
  training_rows?: number;
  holdout?: {
    samples: number;
    positives: number;
    brier_score: number;
    log_loss: number;
    roc_auc: number;
    calibration_error: number;
    base_rate: number;
    bins: CalibrationBin[];
  };
}

export interface Overview {
  revenue_at_risk_paise: number;
  expected_recovery_paise: number;
  gross_recovered_paise: number;
  incremental_net_paise: number;
  organic_estimate_paise: number;
  recovery_cost_paise: number;
  at_risk_by_kind: {
    kind: EventKind;
    events: number;
    amount_paise: number;
    expected_recovery_paise: number;
  }[];
  events: { open: number; recovered: number; lost: number };
  journeys: { by_state: Record<string, number>; active: number };
  pending_approvals: number;
  customer_contacts: number;
  safety: {
    actions_executed: number;
    duplicate_executions: number;
    policy_blocks: number;
    rejected_actions: number;
    unauthorized_actions: number;
  };
  ab_test: AbTest;
  degradation: ScopeHealth[];
  top_opportunities: {
    event_id: string;
    event_ref: string;
    customer_ref: string;
    loss_class: EventKind;
    amount_paise: number;
    risk_score: number;
    priority_score: number;
    recovery_probability: number;
    expected_recovery_paise: number;
    root_cause: string;
  }[];
  activity: ActivityRow[];
  runtime: {
    gateway: string;
    reasoning_provider: string;
    llm_model: string | null;
    model: ModelMetadata;
    scheduler: {
      running: boolean;
      interval_seconds: number;
      cycles: number;
      last_error: string | null;
      clock_speedup: number;
    };
    clock_speedup: number;
  };
}

export interface ActivityRow {
  action_id: string;
  journey_id: string;
  event_ref: string;
  customer_ref: string;
  action: string;
  status: ActionStatus;
  amount_paise: number;
  recovered_paise: number;
  loss_class: EventKind;
  scheduled_at: string | null;
  executed_at: string | null;
  blocked_reasons: string[];
}

export interface LeakageSlice {
  key: string;
  label: string;
  events: number;
  amount_paise: number;
  expected_recovery_paise: number;
}

export interface LeakageGraph {
  total_events: number;
  total_at_risk_paise: number;
  total_expected_recovery_paise: number;
  by_loss_class: LeakageSlice[];
  by_payment_method: LeakageSlice[];
  by_root_cause: LeakageSlice[];
  by_failure_code: LeakageSlice[];
  by_route: LeakageSlice[];
  by_segment: LeakageSlice[];
  hourly: { hour: number; events: number; amount_paise: number }[];
  method_loss_rates: {
    payment_method: string;
    events: number;
    unrecovered: number;
    loss_rate: number;
  }[];
}

export interface SimulationArm {
  label: string;
  events: number;
  revenue_at_risk_paise: number;
  expected_recovery_paise: number;
  expected_incremental_paise: number;
  intervention_cost_paise: number;
  discount_cost_paise: number;
  customer_contacts: number;
  interventions: number;
  do_nothing: number;
  approvals_required: number;
  blocked: number;
  action_mix: Record<string, number>;
  net_expected_paise: number;
}

export interface SimulationResult {
  sample_size: number;
  current: SimulationArm;
  proposed: SimulationArm;
  legacy_baseline: SimulationArm;
  delta: {
    expected_recovery_delta_paise: number;
    net_expected_delta_paise: number;
    incremental_delta_paise: number;
    contact_delta: number;
    contact_change_pct: number;
    intervention_delta: number;
    discount_cost_delta_paise: number;
    approval_delta: number;
  };
  delta_vs_legacy: SimulationResult["delta"];
  current_policy: Record<string, number | boolean | string>;
  proposed_policy: Record<string, number | boolean | string>;
  changed_fields: Record<string, { from: number | boolean | string; to: number | boolean | string }>;
}

export interface LedgerEntry {
  id: string;
  event_id: string;
  journey_id: string | null;
  cohort: string;
  action: string;
  gross_recovered_paise: number;
  organic_estimate_paise: number;
  cost_paise: number;
  incremental_net_paise: number;
  attribution_method: string;
  organic_probability: number;
  created_at: string;
}

export interface LedgerSummary {
  entries: number;
  gross_recovered_paise: number;
  organic_estimate_paise: number;
  cost_paise: number;
  incremental_net_paise: number;
  cost_per_recovery_paise: number;
  by_action: {
    action: string;
    recoveries: number;
    gross_recovered_paise: number;
    incremental_net_paise: number;
    cost_paise: number;
  }[];
  cohort_organic_rates: {
    by_kind: Record<string, { rate: number; sample: number }>;
    overall: { rate: number; sample: number };
  };
}

export interface PlaybookEntry {
  context_key: string;
  loss_class: string;
  cause_layer: string;
  value_band: string;
  best_action: string;
  best_action_label: string;
  recovery_rate: number;
  trials: number;
  recovered_paise: number;
  alternatives: { action: string; label: string; recovery_rate: number; trials: number }[];
}

export interface AuditEntry {
  id: string;
  sequence: number;
  occurred_at: string;
  actor: string;
  actor_name: string;
  event_type: string;
  entity_type: string;
  entity_id: string;
  summary: string;
  payload: Record<string, unknown>;
  entry_hash: string;
  previous_hash: string;
}

export interface DegradationWindow {
  id: string;
  scope_type: string;
  scope_value: string;
  status: string;
  severity: string;
  detected_at: string;
  resolved_at: string | null;
  baseline_failure_rate: number;
  observed_failure_rate: number;
  ratio: number;
  affected_events: number;
  recommendation: string;
  detail: Record<string, unknown>;
}

export interface FailurePoint {
  at: string;
  attempts: number;
  failures: number;
  failure_rate: number;
}
