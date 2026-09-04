import type { Route } from "next";

export const href = (path: string) => path as Route;

export const NAV = [
  { path: "/", label: "Command centre", hint: "Live revenue position", icon: "grid" },
  { path: "/radar", label: "Risk radar", hint: "Every at-risk rupee, ranked", icon: "radar" },
  { path: "/journeys", label: "Journeys", hint: "Recovery workflows in flight", icon: "route" },
  { path: "/approvals", label: "Approvals", hint: "Actions waiting on a human", icon: "shield" },
  { path: "/decisions", label: "Decisions", hint: "Why each action was chosen", icon: "layers" },
  { path: "/leakage", label: "Leakage graph", hint: "Where revenue escapes", icon: "chart" },
  { path: "/simulator", label: "Strategy simulator", hint: "Test policy before it ships", icon: "flask" },
  { path: "/ledger", label: "Incremental ledger", hint: "Credit Revyn can defend", icon: "coins" },
  { path: "/playbook", label: "Recovery memory", hint: "What works for this merchant", icon: "book" },
  { path: "/policies", label: "Guardrails", hint: "Limits, budgets, kill switch", icon: "sliders" },
  { path: "/audit", label: "Audit trail", hint: "Hash-chained action log", icon: "scroll" },
] as const;
