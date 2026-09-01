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
import { inr, pct, relativeTime, titleCase } from "@/lib/format";
import { useAction, useResource } from "@/lib/hooks";
import { actionLabel, causeLabel, LOSS_CLASS_LABEL } from "@/lib/labels";
import { href } from "@/lib/routes";
import type { ApprovalItem } from "@/lib/types";

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
              {items.map((item) => (
                <Card key={item.action.id}>
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
                    hint={`${item.event.customer.name} · ${titleCase(item.event.customer.segment)} · ${
                      LOSS_CLASS_LABEL[item.event.kind]
                    } · queued ${relativeTime(item.action.scheduled_at)}`}
                    actions={
                      <>
                        <Button
                          variant="primary"
                          size="sm"
                          loading={pending === item.action.id}
                          onClick={() => decide(item, true)}
                        >
                          Approve
                        </Button>
                        <Button
                          variant="danger"
                          size="sm"
                          loading={pending === item.action.id}
                          onClick={() => decide(item, false)}
                        >
                          Reject
                        </Button>
                      </>
                    }
                  />

                  <div className="grid gap-4 xl:grid-cols-[1fr_1.4fr]">
                    <div className="space-y-3">
                      <KeyValue
                        items={[
                          ["Amount at risk", inr(item.event.amount_paise, { precise: true })],
                          ["Diagnosed cause", causeLabel(item.event.root_cause)],
                          ["Action cost", inr(item.action.cost_paise)],
                          [
                            "Discount offered",
                            item.action.discount_pct ? `${item.action.discount_pct.toFixed(1)}%` : "none",
                          ],
                          [
                            "Expected recovery",
                            item.decision ? inr(item.decision.expected_recovery_paise) : "—",
                          ],
                          [
                            "Uplift over doing nothing",
                            item.decision ? `+${pct(item.decision.uplift, 1)}` : "—",
                          ],
                        ]}
                      />
                      <div className="space-y-1.5 border-t border-hairline pt-3">
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
                      <div>
                        <p className="mb-2 text-[11px] text-muted">
                          What else was on the table, priced identically:
                        </p>
                        <OptionTable
                          options={item.decision.alternatives}
                          chosen={item.decision.chosen_action}
                        />
                      </div>
                    ) : null}
                  </div>
                </Card>
              ))}

              <label className="block max-w-md">
                <span className="text-xs text-muted">Note attached to your next decision (optional)</span>
                <input
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                  placeholder="e.g. approved, strategic account"
                  className="hairline mt-1 w-full rounded-md bg-raised px-2.5 py-1.5 text-sm text-ink"
                />
              </label>
            </div>
          )
        }
      </Resource>
    </>
  );
}
