"use client";

import { ChartFrame } from "@/components/charts/ChartFrame";
import { COHORT_COLOUR } from "@/components/charts/palette";
import { DataTable } from "@/components/ui/DataTable";
import { compact, inr, pct } from "@/lib/format";
import type { AbTest } from "@/lib/types";

/*
 * Four numbers do not need a plotting library, and the two measures have different units, so
 * they get their own scales rather than a shared second axis. Control stays deliberately
 * muted: the eye should land on the Revyn arm.
 */
function PairedBars({
  title,
  control,
  treatment,
  max,
  render,
  invert = false,
}: {
  title: string;
  control: number;
  treatment: number;
  max: number;
  render: (value: number) => string;
  invert?: boolean;
}) {
  const width = (value: number) => `${max > 0 ? Math.max((value / max) * 100, 1.5) : 1.5}%`;
  return (
    <div>
      <p className="text-xs text-ink-2">{title}</p>
      <div className="mt-2 space-y-1.5">
        {[
          { label: "Control (no Revyn)", value: control, colour: COHORT_COLOUR.control },
          { label: "Revyn", value: treatment, colour: COHORT_COLOUR.treatment },
        ].map((arm) => (
          <div key={arm.label} className="grid grid-cols-[8.5rem_1fr_auto] items-center gap-2 text-[11px]">
            <span className="truncate text-muted">{arm.label}</span>
            <span className="h-3 rounded-sm bg-grid">
              <span
                className="block h-full rounded-sm"
                style={{ width: width(arm.value), background: arm.colour }}
              />
            </span>
            <span className="w-16 text-right tabular-nums text-ink">{render(arm.value)}</span>
          </div>
        ))}
      </div>
      <p className="mt-1.5 text-[11px] text-muted">
        {invert ? "Lower is better." : "Higher is better."}
      </p>
    </div>
  );
}

export function AbCompare({ test }: { test: AbTest }) {
export function AbCompare({ test }: { test?: AbTest }) {
  if (!test || !test.control || !test.treatment) return null;
  const { control, treatment } = test;
  const arms = [control, treatment];

  return (
    <ChartFrame
      title="Control holdout vs Revyn"
      hint="Same population, randomly split. The result Revyn is aiming for is more money recovered from fewer customer touches."
      height="auto"
      table={
        <DataTable
          dense
          rowKey={(row) => row.cohort}
          rows={arms}
          columns={[
            { key: "arm", head: "Arm", cell: (row) => (row.cohort === "control" ? "Control" : "Revyn") },
            { key: "events", head: "Events", align: "right", cell: (row) => compact(row.events) },
            {
              key: "atrisk",
              head: "At risk",
              align: "right",
              cell: (row) => inr(row.revenue_at_risk_paise),
            },
            {
              key: "recovered",
              head: "Recovered",
              align: "right",
              cell: (row) => inr(row.recovered_paise),
            },
            { key: "rate", head: "Recovery rate", align: "right", cell: (row) => pct(row.recovery_rate, 1) },
            {
              key: "contacts",
              head: "Contacts / event",
              align: "right",
              cell: (row) => row.contacts_per_event.toFixed(2),
            },
          ]}
        />
      }
    >
      <div className="grid gap-5 sm:grid-cols-2">
        <PairedBars
          title="Recovery rate"
          control={control.recovery_rate}
          treatment={treatment.recovery_rate}
          max={Math.max(control.recovery_rate, treatment.recovery_rate, 0.01)}
          render={(value) => pct(value, 1)}
        />
        <PairedBars
          title="Customer contacts per event"
          control={control.contacts_per_event}
          treatment={treatment.contacts_per_event}
          max={Math.max(control.contacts_per_event, treatment.contacts_per_event, 0.01)}
          render={(value) => value.toFixed(2)}
          invert
        />
      </div>
    </ChartFrame>
  );
}
