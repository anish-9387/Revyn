"use client";

import { useState } from "react";

import { FailureRateSeries } from "@/components/charts/FailureRateSeries";
import { HourlyRisk } from "@/components/charts/HourlyRisk";
import { seriesColour } from "@/components/charts/palette";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHead, PageHead } from "@/components/ui/Card";
import { DataTable } from "@/components/ui/DataTable";
import { ShareBar } from "@/components/ui/Meter";
import { Resource, SkeletonBlock } from "@/components/ui/State";
import { api } from "@/lib/api";
import { compact, inr, pct, titleCase } from "@/lib/format";
import { useResource } from "@/lib/hooks";
import { causeLabel, LOSS_CLASS_LABEL, methodLabel, SEVERITY_TONE, termLabel } from "@/lib/labels";
import type { EventKind, LeakageSlice, ScopeHealth } from "@/lib/types";

/** `label` per dimension: causes and loss classes have written names, routes and codes are identifiers. */
const DIMENSIONS = [
  {
    key: "by_loss_class",
    title: "loss class",
    hint: "Which of the four leaks is largest",
    label: (slice: LeakageSlice) => LOSS_CLASS_LABEL[slice.key as EventKind] ?? termLabel(slice.label),
  },
  {
    key: "by_payment_method",
    title: "payment method",
    hint: "Concentration risk lives here",
    label: (slice: LeakageSlice) => methodLabel(slice.key),
  },
  {
    key: "by_root_cause",
    title: "diagnosed cause",
    hint: "What is actually going wrong",
    label: (slice: LeakageSlice) => causeLabel(slice.key),
  },
  { key: "by_route", title: "payment route", hint: "Infrastructure, not customers", label: (slice: LeakageSlice) => slice.label },
  {
    key: "by_segment",
    title: "customer segment",
    hint: "Who is affected",
    label: (slice: LeakageSlice) => termLabel(slice.label),
  },
  { key: "by_failure_code", title: "failure code", hint: "Signal from the payment system", label: (slice: LeakageSlice) => slice.label },
] as const;

export default function Leakage() {
  const graph = useResource(api.leakage, { intervalMs: 20000 });
  const insights = useResource(api.insights);
  const live = useResource(api.degradationLive, { intervalMs: 15000 });
  const [dimension, setDimension] = useState<(typeof DIMENSIONS)[number]["key"]>("by_root_cause");
  const focus = live.data ? loudest(live.data) : undefined;
  const scopes = live.data ? scoredFirst([...live.data.routes, ...live.data.methods]) : [];

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
          </ul>
        ) : (
          <SkeletonBlock label="Deriving insights" />
        )}
      </Card>

      <Resource {...graph} empty="Nothing at risk to slice.">
        {(data) => {
          const active = DIMENSIONS.find((entry) => entry.key === dimension) ?? DIMENSIONS[2];
          const slices = data[dimension] as LeakageSlice[];
          const total = slices.reduce((sum, slice) => sum + slice.amount_paise, 0) || 1;
          return (
            <div className="grid gap-4 xl:grid-cols-[1.1fr_1fr]">
              <Card className="self-start">
                <CardHead title="Where revenue escapes" hint={active.hint} />
                {/* Six dimensions is a filter row, not a card action: it scrolls rather than reflowing the head. */}
                <div role="group" aria-label="Slice revenue at risk by" className="scroll-fade -mx-1 mb-4 flex gap-1.5 overflow-x-auto px-1 pb-1">
                  {DIMENSIONS.map((entry) => (
                    <button
                      key={entry.key}
                      onClick={() => setDimension(entry.key)}
                      aria-pressed={dimension === entry.key}
                      className={`press shrink-0 rounded-full px-3 py-1.5 text-[11px] font-medium whitespace-nowrap transition-all ${dimension === entry.key ? "bg-ink text-white shadow-soft dark:bg-white dark:text-black" : "border border-hairline bg-raised text-muted hover:border-hairline-strong hover:text-ink"}`}
                    >
                      {entry.title}
                    </button>
                  ))}
                </div>
                <div className="space-y-2.5">
                  {slices.slice(0, 12).map((slice, index) => (
                    <ShareBar
                      key={slice.key}
                      label={active.label(slice)}
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
                      { key: "method", head: "Method", cell: (row) => methodLabel(row.payment_method) },
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
          hint={
            live.data
              ? `Each scope is compared against its own 7-day baseline over the last ${live.data.window_minutes} minutes. Below ${live.data.min_attempts} attempts the ratio is shown but not called, so a quiet window cannot raise an alarm.`
              : "Each scope is compared against its own 7-day baseline, with a minimum attempt count so a quiet window cannot raise an alarm."
          }
        />
        {live.data ? (
          <>
            <div className="mb-4 flex flex-wrap gap-2">
              {live.data.active.length === 0 ? (
                /* No scope measured means no verdict; only a scored scope can be cleared. */
                <Badge tone={scopes.some((row) => row.scored) ? "good" : "neutral"}>
                  {scopes.some((row) => row.scored)
                    ? "All scored routes and methods within baseline"
                    : "Nothing scored in this window"}
                </Badge>
              ) : (
                live.data.active.map((scope) => (
                  <Badge
                    key={`${scope.scope_type}-${scope.scope_value}`}
                    tone={SEVERITY_TONE[scope.severity]}
                  >
                    {scope.scope_type === "method" ? methodLabel(scope.scope_value) : scope.scope_value}{" "}
                    &middot; {scope.ratio.toFixed(2)}x baseline
                  </Badge>
                ))
              )}
            </div>
            <DataTable
              dense
              empty="No attempts recorded in this window."
              rows={scopes}
              rowKey={(row) => `${row.scope_type}-${row.scope_value}`}
              columns={[
                {
                  /* Route names already read as routes, so a scope-type prefix only stutters. */
                  key: "scope",
                  head: "Route or method",
                  cell: (row) =>
                    row.scope_type === "method" ? methodLabel(row.scope_value) : row.scope_value,
                },
                {
                  key: "attempts",
                  head: `Attempts (${live.data.window_minutes}m)`,
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
                  /* Below the floor there is no verdict to give, and the card hint says why. */
                  cell: (row) =>
                    row.scored ? (
                      <Badge tone={SEVERITY_TONE[row.severity]}>{titleCase(row.severity)}</Badge>
                    ) : (
                      <span className="text-muted" title="Too few attempts in the window to score">
                        &mdash;
                      </span>
                    ),
                },
              ]}
            />
          </>
        ) : (
          <SkeletonBlock label="Reading route health" />
        )}
      </Card>

      {focus ? <ScopeSeries scope={focus} /> : null}
    </>
  );
}

/** Scored scopes first, loudest ratio at the top; unscored rows keep their order below. */
const scoredFirst = (rows: ScopeHealth[]) =>
  [...rows].sort((a, b) =>
    a.scored === b.scored ? (a.scored ? b.ratio - a.ratio : 0) : a.scored ? -1 : 1,
  );

/** Chart what the detector is shouting about; when nothing is degraded, the weakest route. */
const loudest = (state: { routes: ScopeHealth[]; active: ScopeHealth[] }) =>
  (state.active.length > 0 ? state.active : state.routes).reduce<ScopeHealth | undefined>(
    (best, row) => (best && best.ratio > row.ratio ? best : row),
    undefined,
  );

/** The detector's claim only reads if the series is shown against the same baseline it used. */
function ScopeSeries({ scope }: { scope: ScopeHealth }) {
  const series = useResource(() => api.degradationSeries(scope.scope_value, scope.scope_type, 8), {
    intervalMs: 20000,
    deps: [scope.scope_type, scope.scope_value],
  });
  if (!series.data) return <SkeletonBlock panel label="Loading failure-rate series" />;
  return (
    <FailureRateSeries
      points={series.data.points}
      label={scope.scope_type === "method" ? methodLabel(scope.scope_value) : scope.scope_value}
      kind={scope.scope_type}
      baseline={scope.baseline_rate}
    />
  );
}
