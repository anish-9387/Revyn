"use client";

import Link from "next/link";
import { useState } from "react";

import { OptionTable } from "@/components/domain/OptionTable";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHead, PageHead } from "@/components/ui/Card";
import { EmptyState, Resource } from "@/components/ui/State";
import { KeyValue } from "@/components/ui/StatTile";
import { api } from "@/lib/api";
import { inr, pct, plural, relativeTime } from "@/lib/format";
import { useAction, useResource } from "@/lib/hooks";
import { actionLabel, causeLabel, LOSS_CLASS_LABEL, termLabel } from "@/lib/labels";
import { href } from "@/lib/routes";
import type { ActionOption, ApprovalItem } from "@/lib/types";

export default function Approvals() {
  const queue = useResource(api.approvals, { intervalMs: 8000 });
  const { pending, error, run } = useAction();
  const [note, setNote] = useState("");

  const decide = (item: ApprovalItem, approve: boolean) =>
    void run(item.action.id, async () => {
      await (approve ? api.approve(item.action.id, note) : api.reject(item.action.id, note));
      setNote("");
      await queue.refresh();
    });

  return (
    <>
      <PageHead
        title="Awaiting your approval"
        hint="Revyn stops itself here. Large amounts, discounts and voice calls need a human before the money or the goodwill moves."
      />
      {error ? <p className="text-xs text-critical">{error}</p> : null}

      <Resource {...queue}>
        {(items) =>
          items.length === 0 ? (
            <EmptyState
              title="Nothing is waiting on you"
              hint="Every planned action currently sits inside the automated envelope your guardrails allow."
            />
          ) : (
            <div className="space-y-4">
              {/* The note applies to whichever card you act on next, so it sits above them all. */}
              <div className="panel panel-sheen stagger flex flex-col gap-3 rounded-card p-4 sm:flex-row sm:items-end sm:justify-between sm:gap-5">
                <div className="min-w-0">
                  <p className="text-sm text-ink">
                    {plural(items.length, "action")} waiting ·{" "}
                    <span className="num">
                      {inr(items.reduce((sum, item) => sum + item.event.amount_paise, 0))}
                    </span>{" "}
                    at risk
                  </p>
                  <p className="mt-0.5 text-[11px] text-muted">
                    Oldest queued {relativeTime(items[0].action.scheduled_at)}. Nothing here moves until you decide.
                  </p>
                </div>
                <label className="block w-full sm:max-w-xs">
                  <span className="text-[11px] text-muted">Note attached to your next decision (optional)</span>
                  <input
                    value={note}
                    onChange={(event) => setNote(event.target.value)}
                    placeholder="e.g. approved, strategic account"
                    className="hairline mt-1 w-full rounded-md bg-raised px-2.5 py-1.5 text-sm text-ink transition-colors focus:border-hairline-strong focus:outline-none"
                  />
                </label>
              </div>

              {items.map((item) => (
                <ApprovalCard
                  key={item.action.id}
                  item={item}
                  pending={pending}
                  onDecide={decide}
                />
              ))}
            </div>
          )
        }
      </Resource>
    </>
  );
}

/** One decision. The priced alternatives are the evidence behind it, so they fold away by default. */
function ApprovalCard({
  item,
  pending,
  onDecide,
}: {
  item: ApprovalItem;
  pending: string | null;
  onDecide: (item: ApprovalItem, approve: boolean) => void;
}) {
  const [showOptions, setShowOptions] = useState(false);
  const alternatives = item.decision?.alternatives ?? [];
  const runnerUp = alternatives
    .filter((option) => option.action !== item.decision?.chosen_action)
    .reduce<ActionOption | undefined>(
      (best, option) =>
        best && best.expected_value_paise > option.expected_value_paise ? best : option,
      undefined,
    );

  return (
    <Card>
      <CardHead
        title={
          <>
            {actionLabel(item.action.action_type)} —{" "}
            <Link
              href={href(`/journeys/${item.journey_id}`)}
              className="text-series-1 underline underline-offset-2"
            >
              {item.event.external_ref}
            </Link>
          </>
        }
        hint={`${item.event.customer.name} · ${termLabel(item.event.customer.segment)} · ${
          LOSS_CLASS_LABEL[item.event.kind]
        } · queued ${relativeTime(item.action.scheduled_at)}`}
        actions={
          <>
            <Button
              variant="primary"
              size="sm"
              loading={pending === item.action.id}
              onClick={() => onDecide(item, true)}
            >
              Approve
            </Button>
            <Button
              variant="danger"
              size="sm"
              loading={pending === item.action.id}
              onClick={() => onDecide(item, false)}
            >
              Reject
            </Button>
          </>
        }
      />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-[1fr_1fr]">
        <KeyValue
          items={[
            ["Amount at risk", inr(item.event.amount_paise, { precise: true })],
            ["Diagnosed cause", causeLabel(item.event.root_cause)],
            ["Action cost", inr(item.action.cost_paise)],
            [
              "Discount offered",
              item.action.discount_pct ? `${item.action.discount_pct.toFixed(1)}%` : "none",
            ],
            ["Expected recovery", item.decision ? inr(item.decision.expected_recovery_paise) : "—"],
            [
              "Uplift over doing nothing",
              item.decision ? `+${pct(item.decision.uplift, 1)}` : "—",
            ],
          ]}
        />
        <div className="space-y-1.5 max-md:border-t max-md:border-hairline max-md:pt-3">
          {item.explanations.map((line) => (
            <p key={line} className="text-xs leading-relaxed text-ink-2">
              <Badge tone="warning" className="mr-2">
                rule
              </Badge>
              {line}
            </p>
          ))}
        </div>
      </div>

      {item.decision ? (
        <div className="mt-4 border-t border-hairline pt-3">
          <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
            <p className="text-[11px] text-muted">
              {runnerUp ? (
                <>
                  Next best was {actionLabel(runnerUp.action)} at{" "}
                  <span className="num text-ink-2">{inr(runnerUp.expected_value_paise)}</span>{" "}
                  expected value.
                </>
              ) : (
                "No alternative was priced for this event."
              )}
            </p>
            <button
              type="button"
              onClick={() => setShowOptions((open) => !open)}
              aria-expanded={showOptions}
              className="press hairline rounded-full px-2.5 py-1 text-[11px] font-medium text-ink-2 transition-colors hover:border-hairline-strong hover:text-ink"
            >
              {showOptions ? "Hide options" : `Compare all ${alternatives.length} options`}
            </button>
          </div>
          {showOptions ? (
            <div className="animate-fade mt-3">
              <OptionTable options={alternatives} chosen={item.decision.chosen_action} />
            </div>
          ) : null}
        </div>
      ) : null}
    </Card>
  );
}
