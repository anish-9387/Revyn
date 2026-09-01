"use client";

import { useState } from "react";

import { AGENT_LABEL } from "@/lib/labels";
import type { AgentStep } from "@/lib/types";

/** The reasoning chain, in order, with each agent's own numbers available underneath. */
export function AgentTrace({ steps }: { steps: AgentStep[] }) {
  const [open, setOpen] = useState<string | null>(null);
  if (steps.length === 0) return <p className="text-xs text-muted">No trace recorded.</p>;

  return (
    <ol className="space-y-1.5">
      {steps.map((step, index) => {
        const expanded = open === step.agent;
        return (
          <li key={`${step.agent}-${index}`} className="hairline rounded-lg bg-raised">
            <button
              type="button"
              onClick={() => setOpen(expanded ? null : step.agent)}
              aria-expanded={expanded}
              className="flex w-full items-start gap-3 px-3 py-2 text-left"
            >
              <span className="mt-0.5 w-4 shrink-0 text-[11px] tabular-nums text-muted">{index + 1}</span>
              <span className="min-w-0 flex-1">
                <span className="text-xs font-medium text-ink">
                  {AGENT_LABEL[step.agent] ?? step.agent}
                </span>
                <span className="mt-0.5 block text-xs leading-relaxed text-ink-2">{step.summary}</span>
              </span>
              <span className="shrink-0 text-[11px] tabular-nums text-muted">{step.duration_ms}ms</span>
            </button>
            {expanded ? (
              <pre className="max-h-64 overflow-auto border-t border-hairline px-3 py-2 text-[11px] leading-relaxed text-ink-2">
                {JSON.stringify(step.detail, null, 2)}
              </pre>
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}
