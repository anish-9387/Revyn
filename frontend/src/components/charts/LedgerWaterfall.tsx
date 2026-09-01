"use client";

import { ChartFrame } from "@/components/charts/ChartFrame";
import { inr } from "@/lib/format";

interface Step {
  label: string;
  value: number;
  kind: "base" | "subtract" | "total";
  note: string;
}

/**
 * The headline KPI is a subtraction, so it is drawn as one: gross recovery minus what would
 * have come back anyway, minus what the recovery cost.
 */
export function LedgerWaterfall({
  gross,
  organic,
  cost,
  incremental,
}: {
  gross: number;
  organic: number;
  cost: number;
  incremental: number;
}) {
  const steps: Step[] = [
    { label: "Gross recovered", value: gross, kind: "base", note: "Money that came back after Revyn acted" },
    {
      label: "Would have recovered anyway",
      value: -organic,
      kind: "subtract",
      note: "Organic baseline from the control holdout and the model",
    },
    { label: "Recovery cost", value: -cost, kind: "subtract", note: "Messages, calls, discounts, escalations" },
    {
      label: "Incremental net recovered",
      value: incremental,
      kind: "total",
      note: "What Revyn can actually take credit for",
    },
  ];
  const scale = Math.max(gross, 1);

  return (
    <ChartFrame
      title="Incremental recovery ledger"
      hint="Gross recovery flatters every recovery tool. This is the number that survives subtraction."
      height="auto"
    >
      <ul className="space-y-3">
        {steps.map((step) => {
          const width = (Math.abs(step.value) / scale) * 100;
          const isTotal = step.kind === "total";
          const colour =
            step.kind === "base"
              ? "var(--series-1)"
              : step.kind === "subtract"
                ? "var(--axis)"
                : "var(--series-3)";
          return (
            <li key={step.label}>
              <div className="flex items-baseline justify-between gap-3 text-xs">
                <span className={isTotal ? "font-medium text-ink" : "text-ink-2"}>{step.label}</span>
                <span
                  className="tabular-nums"
                  style={{ color: step.kind === "subtract" ? "var(--muted)" : "var(--ink)" }}
                >
                  {step.value < 0 ? `− ${inr(-step.value)}` : inr(step.value)}
                </span>
              </div>
              <div className={`mt-1 h-3 w-full rounded-sm bg-grid ${isTotal ? "mt-1.5 h-4" : ""}`}>
                <span
                  className="block h-full rounded-sm"
                  style={{ width: `${Math.max(width, 0.6)}%`, background: colour }}
                />
              </div>
              <p className="mt-1 text-[11px] text-muted">{step.note}</p>
            </li>
          );
        })}
      </ul>
    </ChartFrame>
  );
}
