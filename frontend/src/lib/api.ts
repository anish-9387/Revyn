/** Typed client for the Revyn API. */

import type {
  ApprovalItem,
  AuditEntry,
  Decision,
  DegradationWindow,
  FailurePoint,
  Journey,
  JourneyDetail,
  LedgerEntry,
  LedgerSummary,
  LeakageGraph,
  ModelMetadata,
  Overview,
  Page,
  PlaybookEntry,
  Policy,
  RiskItem,
  ScopeHealth,
  SimulationResult,
} from "@/lib/types";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY ?? "";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type Query = Record<string, string | number | boolean | undefined | null>;

function buildUrl(path: string, query?: Query): string {
  const url = new URL(`${BASE_URL}${path}`);
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

async function request<T>(path: string, init?: RequestInit & { query?: Query }): Promise<T> {
  const { query, ...options } = init ?? {};
  const headers: Record<string, string> = { "Content-Type": "application/json", ...(options.headers as Record<string, string> | undefined) };
  if (API_KEY) headers["X-API-Key"] = API_KEY;
  const response = await fetch(buildUrl(path, query), {
    ...options,
    cache: "no-store",
    headers,
  });
  if (!response.ok) {
    const body = await response.text();
    let message = `${response.status} ${response.statusText}`;
    try {
      const parsed = JSON.parse(body) as { message?: string; detail?: string };
      message = parsed.message ?? parsed.detail ?? message;
    } catch {
      if (body) message = body.slice(0, 200);
    }
    throw new ApiError(response.status, message);
  }
  return (await response.json()) as T;
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body: JSON.stringify(body ?? {}) });

export const api = {
  overview: () => request<Overview>("/dashboard/overview"),
  health: () => request<{ status: string; seeded: boolean }>("/health/ready"),

  risk: (query?: Query) => request<Page<RiskItem>>("/risk", { query }),
  riskItem: (id: string) => request<RiskItem>(`/risk/${id}`),
  riskDecisions: (id: string) => request<Decision[]>(`/risk/${id}/decisions`),

  journeys: (query?: Query) => request<Page<Journey>>("/journeys", { query }),
  journey: (id: string) => request<JourneyDetail>(`/journeys/${id}`),
  pauseJourney: (id: string) => post<Journey>(`/journeys/${id}/pause`, { actor: "merchant" }),
  resumeJourney: (id: string) => post<Journey>(`/journeys/${id}/resume`, { actor: "merchant" }),
  stopJourney: (id: string, reason: string) =>
    post<Journey>(`/journeys/${id}/stop`, { actor: "merchant", reason }),

  decisions: (query?: Query) => request<Page<Decision>>("/decisions", { query }),
  decision: (id: string) =>
    request<{ decision: Decision; policy_explanations: string[]; considered: Decision["alternatives"] }>(
      `/decisions/${id}`,
    ),

  approvals: () => request<ApprovalItem[]>("/approvals"),
  approve: (actionId: string, note = "") =>
    post(`/approvals/${actionId}/approve`, { approver: "merchant", note }),
  reject: (actionId: string, reason = "") =>
    post(`/approvals/${actionId}/reject`, { approver: "merchant", reason }),

  policy: () => request<Policy>("/policies/active"),
  updatePolicy: (patch: Partial<Policy>) =>
    request<Policy>("/policies/active", { method: "PATCH", body: JSON.stringify(patch) }),
  killSwitch: (enabled: boolean) =>
    post<{ automation_enabled: boolean }>("/policies/kill-switch", { enabled, actor: "merchant" }),

  simulate: (overrides: Record<string, number | boolean>, sampleLimit = 400) =>
    post<SimulationResult>("/simulator/what-if", { overrides, sample_limit: sampleLimit }),
  applySimulation: (overrides: Record<string, number | boolean>) =>
    post<Policy>("/simulator/apply", { overrides }),

  ledgerSummary: () => request<LedgerSummary>("/ledger/summary"),
  ledgerEntries: (limit = 50) => request<LedgerEntry[]>("/ledger/entries", { query: { limit } }),

  leakage: () => request<LeakageGraph>("/leakage/graph"),
  insights: () =>
    request<{ insights: string[]; deterministic_insights: string[]; source: string }>(
      "/leakage/insights",
    ),
  playbook: () =>
    request<{ entries: PlaybookEntry[]; min_trials_for_confidence: number }>("/playbook"),

  degradation: () => request<DegradationWindow[]>("/degradation"),
  degradationLive: () =>
    request<{
      routes: ScopeHealth[];
      methods: ScopeHealth[];
      active: ScopeHealth[];
      window_minutes: number;
      min_attempts: number;
    }>("/degradation/live"),
  degradationSeries: (value: string, scope: "route" | "method" = "route", hours = 6) =>
    request<{ scope: string; value: string; points: FailurePoint[] }>("/degradation/series", {
      query: { value, scope, hours },
    }),

  audit: (query?: Query) => request<Page<AuditEntry>>("/audit", { query }),
  verifyAudit: () => request<{ valid: boolean; entries: number; head?: string; broken_at?: number }>(
    "/audit/verify",
  ),

  model: () => request<{ metadata: ModelMetadata; artifact_age_hours: number | null }>("/ops/model"),
  runCycle: () => post<{ cycle: number }>("/ops/cycle"),
  scan: () => post<Record<string, number>>("/ops/scan"),
  tick: () => post<Record<string, number>>("/ops/tick"),
  seed: (body?: { reset?: boolean; train_model?: boolean }) => post("/ops/seed", body ?? {}),
  injectTimeout: (count = 1) =>
    post<{ timeouts_armed: number }>("/ops/inject-timeout", { count }),
  extractPromise: (transcript: string) =>
    post<{ provider: string; result: Record<string, unknown> | null }>("/ops/extract-promise", {
      transcript,
    }),
};
