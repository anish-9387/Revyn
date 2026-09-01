"use client";

import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { ChartFrame } from "@/components/charts/ChartFrame";
import { AXIS } from "@/components/charts/palette";
import { VizTooltip } from "@/components/charts/VizTooltip";
import { compact, hourLabel, inr } from "@/lib/format";
import type { LeakageGraph } from "@/lib/types";

export function HourlyRisk({ hourly }: { hourly: LeakageGraph["hourly"] }) {
  const data = hourly.map((point) => ({
    hour: point.hour,
    label: hourLabel(point.hour),
    amount: point.amount_paise / 100,
    events: point.events,
  }));
  const peak = data.reduce((best, row) => (row.amount > best.amount ? row : best), data[0]);

  return (
    <ChartFrame
      title="When revenue breaks (IST)"
      hint={
        peak
          ? `Losses concentrate around ${peak.label} — ${inr(peak.amount * 100)} across ${compact(peak.events)} events.`
          : undefined
      }
      height={200}
    >
      <ResponsiveContainer>
        <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 8 }}>
          <defs>
            <linearGradient id="hourly-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--series-1)" stopOpacity={0.42} />
              <stop offset="100%" stopColor="var(--series-1)" stopOpacity={0.04} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke={AXIS.grid} vertical={false} />
          <XAxis
            dataKey="hour"
            stroke={AXIS.stroke}
            tick={AXIS.tick}
            tickLine={false}
            interval={2}
            tickFormatter={(hour: number) => hourLabel(hour)}
          />
          <YAxis
            stroke={AXIS.stroke}
            tick={AXIS.tick}
            tickLine={false}
            width={62}
            tickFormatter={(value: number) => inr(value * 100)}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const row = payload[0].payload as (typeof data)[number];
              return (
                <VizTooltip
                  title={`${row.label} hour`}
                  rows={[
                    { label: "At risk", value: inr(row.amount * 100), colour: "var(--series-1)" },
                    { label: "Events", value: compact(row.events) },
                  ]}
                />
              );
            }}
          />
          <Area
            type="monotone"
            dataKey="amount"
            stroke="var(--series-1)"
            strokeWidth={2}
            fill="url(#hourly-fill)"
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}
