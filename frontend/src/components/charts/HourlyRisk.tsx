"use client";

import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

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
        <BarChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 8 }} barCategoryGap={2}>
          <CartesianGrid stroke={AXIS.grid} vertical={false} />
          <XAxis
            dataKey="hour"
            stroke={AXIS.stroke}
            tick={AXIS.tick}
            tickLine={false}
            interval={3}
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
          {/* The peak hour is the one a merchant schedules around, so it is the only one accented. */}
          <Bar dataKey="amount" fill="var(--series-1)" radius={[2, 2, 0, 0]} isAnimationActive={false}>
            {data.map((row) => (
              <Cell key={row.hour} fillOpacity={row.hour === peak?.hour ? 1 : 0.4} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}
