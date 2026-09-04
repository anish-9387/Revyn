"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { ChartFrame } from "@/components/charts/ChartFrame";
import { AXIS, LOSS_CLASS_COLOUR } from "@/components/charts/palette";
import { VizTooltip } from "@/components/charts/VizTooltip";
import { DataTable } from "@/components/ui/DataTable";
import { compact, inr } from "@/lib/format";
import { LOSS_CLASS_ORDER, LOSS_CLASS_SHORT } from "@/lib/labels";
import type { EventKind, Overview } from "@/lib/types";

type Row = Overview["at_risk_by_kind"][number];

/** Four ticks have to fit a phone's axis, so the tick word is shorter than the label. */
const AXIS_WORD: Record<EventKind, string> = {
  payment_failure: "Payments",
  cart_abandonment: "Checkout",
  subscription_failure: "Renewals",
  overdue_invoice: "Invoices",
};

export function LeakageBars({ rows }: { rows: Row[] }) {
  const byKind = new Map(rows.map((row) => [row.kind, row]));
  const data = LOSS_CLASS_ORDER.map((kind) => {
    const row = byKind.get(kind);
    return {
      kind,
      label: LOSS_CLASS_SHORT[kind],
      axis: AXIS_WORD[kind],
      at_risk: (row?.amount_paise ?? 0) / 100,
      expected: (row?.expected_recovery_paise ?? 0) / 100,
      events: row?.events ?? 0,
    };
  });

  return (
    <ChartFrame
      title="Revenue at risk by loss class"
      hint="Bar height is money exposed; the tooltip carries what Revyn expects to bring back."
      height={250}
      table={
        <DataTable
          dense
          rowKey={(row) => row.kind}
          rows={data}
          columns={[
            { key: "label", head: "Loss class", cell: (row) => row.label },
            { key: "events", head: "Events", align: "right", cell: (row) => compact(row.events) },
            { key: "risk", head: "At risk", align: "right", cell: (row) => inr(row.at_risk * 100) },
            {
              key: "expected",
              head: "Expected recovery",
              align: "right",
              cell: (row) => inr(row.expected * 100),
            },
          ]}
        />
      }
    >
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 8 }}>
          <CartesianGrid stroke={AXIS.grid} vertical={false} />
          <XAxis
            dataKey="axis"
            interval={0}
            stroke={AXIS.stroke}
            tick={AXIS.tick}
            tickLine={false}
          />
          <YAxis
            stroke={AXIS.stroke}
            tick={AXIS.tick}
            tickLine={false}
            width={62}
            tickFormatter={(value: number) => inr(value * 100)}
          />
          <Tooltip
            cursor={{ fill: "var(--grid)", opacity: 0.4 }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const row = payload[0].payload as (typeof data)[number];
              return (
                <VizTooltip
                  title={row.label}
                  rows={[
                    { label: "At risk", value: inr(row.at_risk * 100), colour: LOSS_CLASS_COLOUR[row.kind] },
                    { label: "Expected recovery", value: inr(row.expected * 100) },
                    { label: "Events", value: compact(row.events) },
                  ]}
                />
              );
            }}
          />
          <Bar dataKey="at_risk" radius={[3, 3, 0, 0]} maxBarSize={72} isAnimationActive={false}>
            {data.map((row) => (
              <Cell key={row.kind} fill={LOSS_CLASS_COLOUR[row.kind as EventKind]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}
