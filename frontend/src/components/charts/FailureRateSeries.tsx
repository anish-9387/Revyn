"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { ChartFrame } from "@/components/charts/ChartFrame";
import { AXIS } from "@/components/charts/palette";
import { VizTooltip } from "@/components/charts/VizTooltip";
import { clockTime, compact, pct } from "@/lib/format";
import type { FailurePoint } from "@/lib/types";

/** One series plus a baseline: the whole claim is "this route is worse than it usually is". */
export function FailureRateSeries({
  points,
  label,
  kind,
  baseline,
}: {
  points: FailurePoint[];
  label: string;
  kind: "route" | "method";
  baseline: number;
}) {
  const data = points.map((point) => ({
    at: point.at,
    label: clockTime(point.at),
    rate: point.failure_rate,
    attempts: point.attempts,
    failures: point.failures,
  }));

  return (
    <ChartFrame
      title={`Failure rate — ${label}`}
      hint={`Dashed line is the 7-day baseline for this ${kind} (${pct(baseline, 1)}). Attempts are in the tooltip, because a rate without a denominator can be a traffic dip.`}
      legend={[
        { label: "Observed failure rate", colour: "var(--series-2)" },
        { label: "7-day baseline", colour: "var(--axis)" },
      ]}
      height={230}
    >
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 4, right: 12, bottom: 0, left: 8 }}>
          <CartesianGrid stroke={AXIS.grid} vertical={false} />
          <XAxis
            dataKey="label"
            stroke={AXIS.stroke}
            tick={AXIS.tick}
            tickLine={false}
            minTickGap={28}
          />
          <YAxis
            stroke={AXIS.stroke}
            tick={AXIS.tick}
            tickLine={false}
            width={46}
            domain={[0, "auto"]}
            tickFormatter={(value: number) => pct(value)}
          />
          <ReferenceLine
            y={baseline}
            stroke="var(--axis)"
            strokeDasharray="5 4"
            label={{ value: "baseline", position: "insideTopLeft", fill: "var(--muted)", fontSize: 11 }}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const row = payload[0].payload as (typeof data)[number];
              return (
                <VizTooltip
                  title={row.label}
                  rows={[
                    { label: "Failure rate", value: pct(row.rate, 1), colour: "var(--series-2)" },
                    { label: "Baseline", value: pct(baseline, 1), colour: "var(--axis)" },
                    { label: "Attempts", value: compact(row.attempts) },
                    { label: "Failures", value: compact(row.failures) },
                  ]}
                  note={baseline > 0 ? `${(row.rate / baseline).toFixed(2)}x baseline` : undefined}
                />
              );
            }}
          />
          <Line
            type="monotone"
            dataKey="rate"
            stroke="var(--series-2)"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}
