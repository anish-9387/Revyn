"use client";

import { useState } from "react";

import { FailureRateSeries } from "@/components/charts/FailureRateSeries";
import { HourlyRisk } from "@/components/charts/HourlyRisk";
import { seriesColour } from "@/components/charts/palette";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHead, PageHead } from "@/components/ui/Card";
import { DataTable } from "@/components/ui/DataTable";
import { ShareBar } from "@/components/ui/Meter";
import { Resource, Spinner } from "@/components/ui/State";
import { api } from "@/lib/api";
import { compact, inr, pct, titleCase } from "@/lib/format";
import { useResource } from "@/lib/hooks";
import { causeLabel, SEVERITY_TONE } from "@/lib/labels";
import type { LeakageSlice, ScopeHealth } from "@/lib/types";

const DIMENSIONS = [
  { key: "by_loss_class", title: "loss class", hint: "Which of the four leaks is largest" },
  { key: "by_payment_method", title: "payment method", hint: "Concentration risk lives here" },
  { key: "by_root_cause", title: "diagnosed cause", hint: "What is actually going wrong" },
  { key: "by_route", title: "gateway route", hint: "Infrastructure, not customers" },
  { key: "by_segment", title: "customer segment", hint: "Who is affected" },
  { key: "by_failure_code", title: "failure code", hint: "Raw signal from the gateway" },
] as const;

export default function Leakage() {
  const graph = useResource(api.leakage, { intervalMs: 20000 });
  const insights = useResource(api.insights);
  const live = useResource(api.degradationLive, { intervalMs: 15000 });
  const [dimension, setDimension] = useState<(typeof DIMENSIONS)[number]["key"]>("by_root_cause");

  return (
    <>
      <PageHead
        title="Revenue leakage graph"
        hint="The same money sliced every way that could change what you do about it."
      />

      <Card>
        <CardHead
          title="What the data says"
          hint="Derived from the live slices; every line cites the number it came from."
        />
        {insights.data ? (
          <ul className="space-y-2">
            {insights.data.insights.map((line) => (
              <li key={line} className="flex gap-2 text-xs leading-relaxed text-ink-2">
                <span aria-hidden className="text-series-1">
                  &#9656;
                </span>
                {line}
              </li>
            ))}
            <li className="pt-1 text-[11px] text-muted">source: {insights.data.source}</li>
          </ul>
        ) : (
          <Spinner label="Deriving insights" />
        )}
      </Card>

      <Resource {...graph} empty="Nothing at risk to slice.">
        {(data) => {
          const slices = data[dimension] as LeakageSlice[];
          const total = slices.reduce((sum, slice) => sum + slice.amount_paise, 0) || 1;
          return (
            <div className="grid gap-4 xl:grid-cols-[1.1fr_1fr]">
              <Card>
                <CardHead
                  title="Where revenue escapes"
                  hint={DIMENSIONS.find((entry) => entry.key === dimension)?.hint}
                  actions={
                    <div className="flex flex-wrap gap-1">
                      {DIMENSIONS.map((entry) => (
                        <button
                          key={entry.key}
                          onClick={() => setDimension(entry.key)}
                          aria-pressed={dimension === entry.key}
                          className={`rounded-md px-2 py-1 text-[11px] transition ${
                            dimension === entry.key
                              ? "bg-series-1/14 text-series-1"
                              : "text-muted hover:text-ink"
                          }`}
                        >
                          {entry.title}
                        </button>
                      ))}
                    </div>
                  }
                />
                <div className="space-y-2.5">
                  {slices.slice(0, 12).map((slice, index) => (
                    <ShareBar
                      key={slice.key}
                      label={dimension === "by_root_cause" ? causeLabel(slice.key) : slice.label}
                      value={inr(slice.amount_paise)}
                      share={slice.amount_paise / total}
                      colour={seriesColour(index)}
                    />
                  ))}
                </div>
                <p className="mt-3 text-[11px] leading-relaxed text-muted">
                  {compact(data.total_events)} open events worth {inr(data.total_at_risk_paise)}; Revyn expects{" "}
                  {inr(data.total_expected_recovery_paise)} of it back.
                </p>
              </Card>

              <div className="space-y-4">
                <HourlyRisk hourly={data.hourly} />
                <Card>
                  <CardHead
                    title="Loss rate by payment method"
                    hint="Unrecovered share, so a high-volume method with a healthy rate does not look like the problem."
                  />
                  <DataTable
                    dense
                    rows={data.method_loss_rates}
                    rowKey={(row) => row.payment_method}
                    columns={[
                      { key: "method", head: "Method", cell: (row) => titleCase(row.payment_method) },
                      { key: "events", head: "Events", align: "right", cell: (row) => compact(row.events) },
                      {
                        key: "unrecovered",
                        head: "Unrecovered",
                        align: "right",
                        cell: (row) => compact(row.unrecovered),
                      },
                      {
                        key: "rate",
                        head: "Loss rate",
                        align: "right",
                        cell: (row) => (
                          <span className={row.loss_rate > 0.5 ? "text-serious" : "text-ink"}>
                            {pct(row.loss_rate, 1)}
                          </span>
                        ),
                      },
                    ]}
                  />
                </Card>
              </div>
            </div>
          );
        }}
      </Resource>

      <Card>
        <CardHead
          title="Payment degradation detector"
          hint="Each scope is compared against its own 7-day baseline, with a minimum attempt count so a quiet window cannot raise an alarm."
        />
        {live.data ? (
          <>
            <div className="mb-4 flex flex-wrap gap-2">
              {live.data.active.length === 0 ? (
                <Badge tone="good">All routes and methods within baseline</Badge>
              ) : (
                live.data.active.map((scope) => (
                  <Badge
                    key={`${scope.scope_type}-${scope.scope_value}`}
                    tone={SEVERITY_TONE[scope.severity]}
                  >
                    {scope.scope_value} &middot; {scope.ratio.toFixed(2)}x baseline
                  </Badge>
                ))
              )}
            </div>
            <DataTable
              dense
              rows={[...live.data.routes, ...live.data.methods]}
              rowKey={(row) => `${row.scope_type}-${row.scope_value}`}
              columns={[
                { key: "scope", head: "Scope", cell: (row) => `${row.scope_type} · ${row.scope_value}` },
                {
                  key: "attempts",
                  head: "Attempts (45m)",
                  align: "right",
                  cell: (row) => compact(row.attempts),
                },
                { key: "observed", head: "Observed", align: "right", cell: (row) => pct(row.observed_rate, 1) },
                { key: "baseline", head: "Baseline", align: "right", cell: (row) => pct(row.baseline_rate, 1) },
                {
                  key: "ratio",
                  head: "Ratio",
                  align: "right",
                  cell: (row) => (
                    <span className={row.degraded ? "text-serious" : "text-muted"}>
                      {row.ratio.toFixed(2)}x
                    </span>
                  ),
                },
                {
                  key: "severity",
                  head: "Severity",
                  cell: (row) => <Badge tone={SEVERITY_TONE[row.severity]}>{titleCase(row.severity)}</Badge>,
                },
              ]}
            />
          </>
        ) : (
          <Spinner label="Reading route health" />
        )}
      </Card>

      {live.data && live.data.routes.length > 0 ? <RouteSeries route={worst(live.data.routes)} /> : null}
    </>
  );
}

const worst = (routes: ScopeHealth[]) =>
  routes.reduce((best, row) => (row.ratio > best.ratio ? row : best), routes[0]);

/** The detector's claim only reads if the series is shown against the same baseline it used. */
function RouteSeries({ route }: { route: ScopeHealth }) {
  const series = useResource(() => api.degradationSeries(route.scope_value, 8), {
    intervalMs: 20000,
    deps: [route.scope_value],
  });
  if (!series.data) return <Spinner label="Loading failure-rate series" />;
  return (
    <FailureRateSeries
      points={series.data.points}
      route={series.data.route}
      baseline={route.baseline_rate}
    />
  );
}
