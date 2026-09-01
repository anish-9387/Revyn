"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { ChartFrame } from "@/components/charts/ChartFrame";
import { AXIS } from "@/components/charts/palette";
import { VizTooltip } from "@/components/charts/VizTooltip";
import { DataTable } from "@/components/ui/DataTable";
import { compact, pct } from "@/lib/format";
import type { CalibrationBin } from "@/lib/types";

/** Two series against the perfect-calibration diagonal: predicted vs what actually happened. */
export function CalibrationChart({ bins }: { bins: CalibrationBin[] }) {
  const data = bins.map((bin) => ({
    label: `${pct(bin.lower)}–${pct(bin.upper)}`,
    predicted: bin.predicted,
    observed: bin.observed,
    ideal: bin.predicted,
    count: bin.count,
  }));

  return (
    <ChartFrame
      title="Probability calibration"
      hint="When Revyn says 40%, roughly 40% should recover. Distance from the dashed diagonal is the error."
      legend={[
        { label: "Observed recovery rate", colour: "var(--series-1)" },
        { label: "Predicted probability", colour: "var(--series-2)" },
      ]}
      height={250}
      table={
        <DataTable
          dense
          rowKey={(row) => row.label}
          rows={data}
          columns={[
            { key: "bin", head: "Predicted band", cell: (row) => row.label },
            { key: "n", head: "Events", align: "right", cell: (row) => compact(row.count) },
            { key: "p", head: "Predicted", align: "right", cell: (row) => pct(row.predicted, 1) },
            { key: "o", head: "Observed", align: "right", cell: (row) => pct(row.observed, 1) },
          ]}
        />
      }
    >
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 4, right: 12, bottom: 0, left: 8 }}>
          <CartesianGrid stroke={AXIS.grid} vertical={false} />
          <XAxis dataKey="label" stroke={AXIS.stroke} tick={AXIS.tick} tickLine={false} />
          <YAxis
            stroke={AXIS.stroke}
            tick={AXIS.tick}
            tickLine={false}
            width={46}
            domain={[0, 1]}
            tickFormatter={(value: number) => pct(value)}
          />
          <Legend content={() => null} />
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const row = payload[0].payload as (typeof data)[number];
              return (
                <VizTooltip
                  title={`Predicted ${row.label}`}
                  rows={[
                    { label: "Observed", value: pct(row.observed, 1), colour: "var(--series-1)" },
                    { label: "Predicted", value: pct(row.predicted, 1), colour: "var(--series-2)" },
                    { label: "Events in bin", value: compact(row.count) },
                  ]}
                />
              );
            }}
          />
          <Line
            type="linear"
            dataKey="ideal"
            stroke="var(--axis)"
            strokeDasharray="5 4"
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="predicted"
            stroke="var(--series-2)"
            strokeWidth={2}
            dot={{ r: 2.5 }}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="observed"
            stroke="var(--series-1)"
            strokeWidth={2.5}
            dot={{ r: 3 }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}
