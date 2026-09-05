"use client";

import Link from "next/link";

import { AbCompare } from "@/components/charts/AbCompare";
import { LeakageBars } from "@/components/charts/LeakageBars";
import { useLive } from "@/components/layout/AppShell";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHead, CardLink, PageHead } from "@/components/ui/Card";
import { DataTable } from "@/components/ui/DataTable";
import { SkeletonBlock } from "@/components/ui/State";
import { KeyValue, StatRow, StatTile } from "@/components/ui/StatTile";
import { compact, inr, pct, relativeTime, titleCase } from "@/lib/format";
import { ACTION_STATUS_TONE, actionLabel, causeLabel, JOURNEY_TONE, LOSS_CLASS_SHORT, SEVERITY_TONE } from "@/lib/labels";
import { href } from "@/lib/routes";
import type { JourneyState } from "@/lib/types";

export default function CommandCentre() {
  const { overview } = useLive();
  if (!overview) return <SkeletonBlock panel rows={6} label="Reading the revenue position" />;

  const { safety, events, journeys, ab_test: ab } = overview;
  const recoveryRate = events.recovered + events.lost > 0
    ? events.recovered / (events.recovered + events.lost)
    : 0;

  return (
    <>
      <PageHead
        title="Command centre"
        hint="Revenue Revyn is protecting right now, and what it has already brought back."
      />

      {overview.degradation.length > 0 ? (
        <Card className="border-serious/40 bg-serious/8">
          <div className="flex flex-wrap items-center gap-3">
            {overview.degradation.map((scope) => (
              <Badge key={`${scope.scope_type}-${scope.scope_value}`} tone={SEVERITY_TONE[scope.severity]}>
                {titleCase(scope.severity)} · {scope.scope_value}
              </Badge>
            ))}
            <p className="text-xs text-ink-2">
              {overview.degradation
                .map(
                  (scope) =>
                    `${scope.scope_value} is failing at ${pct(scope.observed_rate, 1)} versus a ${pct(
                      scope.baseline_rate,
                      1,
                    )} baseline (${scope.ratio.toFixed(2)}x)`,
                )
                .join("; ")}
              . Retries on the affected scope are held back so Revyn does not burn attempts into a broken route.
            </p>
            <span className="ml-auto">
              <CardLink href="/leakage">Inspect</CardLink>
            </span>
          </div>
        </Card>
      ) : null}

      <StatRow>
        <StatTile
          label="Revenue at risk"
          value={inr(overview.revenue_at_risk_paise)}
          sub={`${compact(events.open)} open events · ${inr(overview.expected_recovery_paise)} expected back`}
        />
        <StatTile
          label="Gross recovered"
          value={inr(overview.gross_recovered_paise)}
          sub={`${compact(events.recovered)} of ${compact(events.recovered + events.lost)} closed events recovered (${pct(recoveryRate, 1)})`}
        />
        <StatTile
          label="Incremental net recovered"
          value={inr(overview.incremental_net_paise)}
          accent="var(--delta-up)"
          emphasis
          sub={`Gross minus ${inr(overview.organic_estimate_paise)} organic and ${inr(overview.recovery_cost_paise)} cost`}
        />
        <StatTile
          label="Customer touches spent"
          value={compact(overview.customer_contacts)}
          sub={`${ab?.treatment?.contacts_per_event?.toFixed(2) ?? "0.00"} per managed event · ${compact(overview.pending_approvals)} awaiting approval`}
        />
      </StatRow>

      <div className="grid gap-4 xl:grid-cols-2">
        <LeakageBars rows={overview.at_risk_by_kind} />
        <AbCompare test={ab} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHead
            title="Recovery workflows"
            hint="Every detected loss becomes a journey with an explicit state, so nothing sits in limbo."
            actions={
              <CardLink href="/journeys">Open</CardLink>
            }
          />
          <div className="flex flex-wrap gap-2">
            {Object.entries(journeys.by_state)
              .sort(([, left], [, right]) => right - left)
              .map(([state, count]) => (
                <Badge key={state} tone={JOURNEY_TONE[state as JourneyState] ?? "neutral"}>
                  {titleCase(state)} {count}
                </Badge>
              ))}
          </div>
          <p className="mt-3 text-xs text-muted">{compact(journeys.active)} journeys still in flight.</p>
        </Card>

        <Card>
          <CardHead
            title="Safety"
            hint="An autonomous system that touches money is judged on what it did not do."
            actions={
              <CardLink href="/audit">Audit trail</CardLink>
            }
          />
          <KeyValue
            items={[
              ["Actions executed", compact(safety.actions_executed)],
              [
                "Duplicate executions",
                <span key="dup" className={safety.duplicate_executions ? "text-critical" : "text-good"}>
                  {compact(safety.duplicate_executions)}
                </span>,
              ],
              [
                "Unauthorised actions",
                <span key="unauth" className={safety.unauthorized_actions ? "text-critical" : "text-good"}>
                  {compact(safety.unauthorized_actions)}
                </span>,
              ],
              ["Blocked by policy", compact(safety.policy_blocks)],
              ["Rejected by a human", compact(safety.rejected_actions)],
              ...(safety.npci_attempts_spent !== undefined ? [
                ["NPCI attempts spent", compact(safety.npci_attempts_spent)] satisfies [string, React.ReactNode],
                [
                  "Futile retries prevented",
                  <span key="futile" className={safety.futile_retries_prevented ? "text-good" : "text-muted"}>
                    {compact(safety.futile_retries_prevented ?? 0)}
                  </span>,
                ] satisfies [string, React.ReactNode],
                ["Mandates tracked", compact(safety.mandates_tracked ?? 0)] satisfies [string, React.ReactNode],
              ] : []),
            ]}
          />
        </Card>
      </div>

      <Card>
        <CardHead
          title="Highest-value opportunities"
          hint="Ranked by expected recovery, not by amount - a large hopeless invoice loses to a mid-size retry that will land."
          actions={
            <CardLink href="/radar">Full radar</CardLink>
          }
        />
        <DataTable
          rows={overview.top_opportunities}
          rowKey={(row) => row.event_id}
          empty="Nothing at risk right now."
          columns={[
            {
              key: "ref",
              head: "Event",
              cell: (row) => (
                <Link
                  href={href(`/radar?focus=${row.event_id}`)}
                  className="text-series-1 underline underline-offset-2"
                >
                  {row.event_ref}
                </Link>
              ),
            },
            { key: "kind", head: "Loss class", cell: (row) => LOSS_CLASS_SHORT[row.loss_class] },
            { key: "cause", head: "Diagnosed cause", cell: (row) => causeLabel(row.root_cause) },
            { key: "amount", head: "At risk", align: "right", cell: (row) => inr(row.amount_paise) },
            {
              key: "p",
              head: "Recovery prob.",
              align: "right",
              cell: (row) => pct(row.recovery_probability, 1),
            },
            {
              key: "erv",
              head: "Expected recovery",
              align: "right",
              cell: (row) => <span className="text-delta-up">{inr(row.expected_recovery_paise)}</span>,
            },
          ]}
        />
      </Card>

      <Card>
        <CardHead title="Recent actions" hint="What the agents did, most recent first." />
        <DataTable
          dense
          rows={overview.activity}
          rowKey={(row) => row.action_id}
          empty="No actions yet - run one cycle."
          columns={[
            { key: "event", head: "Event", cell: (row) => row.event_ref },
            { key: "action", head: "Action", cell: (row) => actionLabel(row.action) },
            {
              key: "status",
              head: "Status",
              cell: (row) => (
                <Badge tone={ACTION_STATUS_TONE[row.status] ?? "neutral"}>{titleCase(row.status)}</Badge>
              ),
            },
            { key: "amount", head: "Amount", align: "right", cell: (row) => inr(row.amount_paise) },
            {
              key: "recovered",
              head: "Recovered",
              align: "right",
              cell: (row) =>
                row.recovered_paise ? (
                  <span className="text-delta-up">{inr(row.recovered_paise)}</span>
                ) : (
                  <span className="text-muted">-</span>
                ),
            },
            {
              key: "when",
              head: "When",
              align: "right",
              cell: (row) => relativeTime(row.executed_at ?? row.scheduled_at),
            },
            {
              key: "journey",
              head: "",
              align: "right",
              cell: (row) => (
                <Link
                  href={href(`/journeys/${row.journey_id}`)}
                  className="text-series-1 underline underline-offset-2"
                >
                  open
                </Link>
              ),
            },
          ]}
        />
      </Card>
    </>
  );
}
