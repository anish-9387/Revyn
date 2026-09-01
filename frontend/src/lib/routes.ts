import type { Route } from "next";

/** Ids come from the API at runtime, so dynamic hrefs cannot be checked statically. */
export const href = (path: string) => path as Route;

export const NAV = [
  { path: "/", label: "Command centre", hint: "Live revenue position" },
  { path: "/radar", label: "Risk radar", hint: "Every at-risk rupee, ranked" },
  { path: "/journeys", label: "Journeys", hint: "Recovery workflows in flight" },
  { path: "/approvals", label: "Approvals", hint: "Actions waiting on a human" },
  { path: "/decisions", label: "Decisions", hint: "Why each action was chosen" },
  { path: "/leakage", label: "Leakage graph", hint: "Where revenue escapes" },
  { path: "/simulator", label: "Strategy simulator", hint: "Test policy before it ships" },
  { path: "/ledger", label: "Incremental ledger", hint: "Credit Revyn can defend" },
  { path: "/playbook", label: "Recovery memory", hint: "What works for this merchant" },
  { path: "/policies", label: "Guardrails", hint: "Limits, budgets, kill switch" },
  { path: "/audit", label: "Audit trail", hint: "Hash-chained action log" },
] as const;
