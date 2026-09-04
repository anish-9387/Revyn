"use client";

import Link from "next/link";
import { use } from "react";

import { DecisionPanel } from "@/components/domain/DecisionPanel";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHead, PageHead } from "@/components/ui/Card";
import { DataTable } from "@/components/ui/DataTable";
import { Meter } from "@/components/ui/Meter";
import { Resource } from "@/components/ui/State";
import { KeyValue } from "@/components/ui/StatTile";
import { api } from "@/lib/api";
import { dateTime, inr, pct, relativeTime, titleCase } from "@/lib/format";
import { useAction, useResource } from "@/lib/hooks";
import {
  ACTION_STATUS_TONE,
  actionLabel,
  causeLabel,
  JOURNEY_TONE,
  LOSS_CLASS_LABEL,
  methodLabel,
  termLabel,
} from "@/lib/labels";
import { href } from "@/lib/routes";

export default function JourneyPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const journey = useResource(() => api.journey(id), { intervalMs: 6000, deps: [id] });
  const { pending, error, run } = useAction();

  const control = (key: string, task: () => Promise<unknown>) =>
    void run(key, async () => (await task(), journey.refresh()));

  return (
    <Resource {...journey} empty="Journey not found.">
      {(data) => (
        <>
          <PageHead
            title={`${data.event.external_ref} — ${LOSS_CLASS_LABEL[data.event.kind]}`}
            hint={`${data.event.customer.name} · ${termLabel(data.event.customer.segment)} · ${inr(
              data.event.amount_paise,
              { precise: true },
            )} at risk`}
            actions={
              <>
                <Badge tone={JOURNEY_TONE[data.state]}>{titleCase(data.state)}</Badge>
                {data.state === "paused" ? (
                  <Button
                    variant="primary"
                    size="sm"
                    loading={pending === "resume"}
                    onClick={() => control("resume", () => api.resumeJourney(data.id))}
                  >
                    Resume
                  </Button>
                ) : (
                  <Button
                    size="sm"
                    loading={pending === "pause"}
                    disabled={Boolean(data.closed_at)}
                    onClick={() => control("pause", () => api.pauseJourney(data.id))}
                  >
                    Pause
                  </Button>
                )}
                <Button
                  variant="danger"
                  size="sm"
                  loading={pending === "stop"}
                  disabled={Boolean(data.closed_at)}
                  onClick={() =>
                    control("stop", () => api.stopJourney(data.id, "merchant stopped from dashboard"))
                  }
                >
                  Stop
                </Button>
              </>
            }
          />
          {error ? <p className="text-xs text-critical">{error}</p> : null}

          <div className="grid gap-4 xl:grid-cols-3">
            <Card>
              <CardHead title="Event" hint="What Revyn observed, before anything was decided." />
              <KeyValue
                items={[
                  ["Diagnosed cause", causeLabel(data.event.root_cause)],
                  ["Cause confidence", pct(data.event.cause_confidence, 0)],
                  ["Payment message", data.event.failure_reason ?? "—"],
                  ["Method / route", `${methodLabel(data.event.payment_method)} · ${data.event.route}`],
                  ["Retries before Revyn", String(data.event.retry_count)],
                  ["Occurred", dateTime(data.event.occurred_at)],
                  ["Cohort", data.event.cohort === "control" ? "Control holdout" : "Revyn managed"],
                ]}
              />
            </Card>

            <Card>
              <CardHead
                title="Friction budget"
                hint="Hard caps on how much of the customer relationship this recovery may spend."
              />
              <div className="space-y-3">
                <Meter label="Contacts" {...data.friction_budget.contacts} />
                <Meter label="Retries" {...data.friction_budget.retries} />
                <Meter label="Discount offers" {...data.friction_budget.discounts} />
                <Meter label="Voice calls" {...data.friction_budget.voice} />
              </div>
              {data.friction_budget.blocking.length > 0 ? (
                <p className="mt-3 text-[11px] leading-relaxed text-warning">
                  △ Exhausted: {data.friction_budget.blocking.join(", ")}
                </p>
              ) : null}
            </Card>

            <Card>
              <CardHead title="Outcome" hint="Money and promises attached to this workflow." />
              <KeyValue
                items={[
                  [
                    "Recovered",
                    <span
                      key="rec"
                      className={data.recovered_amount_paise ? "text-delta-up" : "text-muted"}
                    >
                      {data.recovered_amount_paise ? inr(data.recovered_amount_paise) : "not yet"}
                    </span>,
                  ],
                  ["Recovery cost", inr(data.cost_paise)],
                  ["Promise to pay", data.promise_date ? dateTime(data.promise_date) : "none captured"],
                  ["Promise confidence", data.promise_date ? pct(data.promise_confidence, 0) : "—"],
                  ["Next action", data.closed_at ? "—" : relativeTime(data.next_action_at)],
                  [
                    "Closed",
                    data.closed_at ? `${dateTime(data.closed_at)} · ${data.close_reason ?? ""}` : "open",
                  ],
                ]}
              />
            </Card>
          </div>

          <div className="grid gap-4 xl:grid-cols-[1.4fr_1fr]">
            <Card>
              <CardHead
                title="Actions taken"
                hint="Each step carries its own idempotency key, so a retry after a timeout cannot double-charge."
              />
              <DataTable
                dense
                rows={data.actions}
                rowKey={(row) => row.id}
                empty="No steps executed yet."
                columns={[
                  { key: "seq", head: "#", cell: (row) => row.sequence + 1, width: "2.5rem" },
                  { key: "action", head: "Action", cell: (row) => actionLabel(row.action_type) },
                  {
                    key: "status",
                    head: "Status",
                    cell: (row) => (
                      <span title={row.blocked_reasons.join(", ") || row.error || undefined}>
                        <Badge tone={ACTION_STATUS_TONE[row.status]}>{titleCase(row.status)}</Badge>
                      </span>
                    ),
                  },
                  { key: "cost", head: "Cost", align: "right", cell: (row) => inr(row.cost_paise) },
                  {
                    key: "ref",
                    head: "Provider ref",
                    cell: (row) => (
                      <span className="text-[11px] text-muted">{row.provider_ref ?? "—"}</span>
                    ),
                  },
                  {
                    key: "when",
                    head: "When",
                    align: "right",
                    cell: (row) => relativeTime(row.executed_at ?? row.scheduled_at),
                  },
                ]}
              />
            </Card>

            <Card>
              <CardHead title="Planned journey" hint="Every step is re-gated immediately before it fires." />
              <ol className="space-y-2">
                {data.plan.map((step, index) => (
                  <li
                    key={`${step.action}-${index}`}
                    className={`hairline rounded-lg px-3 py-2 ${
                      index === data.step_index ? "bg-series-1/10" : "bg-raised"
                    }`}
                  >
                    <p className="text-xs font-medium text-ink">
                      {index + 1}. {step.label}
                      <span className="ml-1.5 font-normal text-muted">
                        {step.delay_minutes > 0
                          ? `after ${
                              step.delay_minutes >= 60
                                ? `${(step.delay_minutes / 60).toFixed(0)}h`
                                : `${step.delay_minutes}m`
                            }`
                          : "immediately"}
                      </span>
                    </p>
                    <p className="mt-0.5 text-[11px] leading-relaxed text-ink-2">{step.reason}</p>
                  </li>
                ))}
              </ol>
            </Card>
          </div>

          <Card>
            <CardHead title="State transitions" hint="Every move is recorded with the reason that caused it." />
            <ol className="flex flex-wrap items-center gap-1.5">
              {data.transitions.map((move, index) => (
                <li key={`${move.at}-${index}`} className="flex items-center gap-1.5">
                  <span
                    className="hairline rounded-md bg-raised px-2 py-1 text-[11px] text-ink-2"
                    title={`${move.reason} · ${dateTime(move.at)}`}
                  >
                    {titleCase(move.to)}
                  </span>
                  {index < data.transitions.length - 1 ? (
                    <span aria-hidden className="text-muted">
                      &rarr;
                    </span>
                  ) : null}
                </li>
              ))}
            </ol>
          </Card>

          {data.decisions.length > 0 ? (
            <>
              <h2 className="text-sm font-semibold text-ink">Why this plan</h2>
              <DecisionPanel decision={data.decisions[0]} />
              {data.decisions.length > 1 ? (
                <p className="text-[11px] text-muted">
                  {data.decisions.length - 1} earlier decision for this journey —{" "}
                  <Link
                    href={href(`/decisions/${data.decisions[1].id}`)}
                    className="text-series-1 underline underline-offset-2"
                  >
                    see the previous one
                  </Link>
                  .
                </p>
              ) : null}
            </>
          ) : null}
        </>
      )}
    </Resource>
  );
}
