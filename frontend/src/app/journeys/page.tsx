"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Card, PageHead } from "@/components/ui/Card";
import { DataTable } from "@/components/ui/DataTable";
import { Select } from "@/components/ui/Field";
import { Pager } from "@/components/ui/Pager";
import { Resource } from "@/components/ui/State";
import { api } from "@/lib/api";
import { compact, inr, relativeTime, titleCase } from "@/lib/format";
import { useResource } from "@/lib/hooks";
import { actionLabel, JOURNEY_TONE } from "@/lib/labels";
import { href } from "@/lib/routes";
import type { JourneyState } from "@/lib/types";

const LIMIT = 25;

const STATES: JourneyState[] = [
  "detected",
  "planned",
  "awaiting_approval",
  "approved",
  "executing",
  "verifying",
  "recovered",
  "closed",
  "blocked",
  "failed",
  "paused",
  "expired",
];

export default function Journeys() {
  const router = useRouter();
  const [state, setState] = useState("");
  const [offset, setOffset] = useState(0);
  const page = useResource(() => api.journeys({ state, limit: LIMIT, offset }), {
    intervalMs: 10000,
    deps: [state, offset],
  });

  return (
    <>
      <PageHead
        title="Recovery journeys"
        hint="Each detected loss runs as an explicit state machine. Nothing advances without passing the guardrails again."
        actions={
          <Select
            label="State"
            value={state}
            onChange={(next) => (setState(next), setOffset(0))}
            options={[
              { value: "", label: "All states" },
              ...STATES.map((value) => ({ value, label: titleCase(value) })),
            ]}
          />
        }
      />

      <Card>
        <Resource {...page} empty="No journeys yet — run one cycle from the top bar.">
          {(data) => (
            <>
              <DataTable
                rows={data.items}
                rowKey={(row) => row.id}
                onRowClick={(row) => router.push(href(`/journeys/${row.id}`))}
                columns={[
                  {
                    key: "state",
                    head: "State",
                    cell: (row) => <Badge tone={JOURNEY_TONE[row.state]}>{titleCase(row.state)}</Badge>,
                  },
                  {
                    key: "strategy",
                    head: "Strategy",
                    cell: (row) => (
                      <span>
                        <span className="text-ink">{titleCase(row.strategy_key)}</span>
                        <span className="block text-[11px] text-muted">
                          step {row.step_index + 1} of {row.plan.length || 1}
                          {row.plan[row.step_index] ? ` · ${actionLabel(row.plan[row.step_index].action)}` : ""}
                        </span>
                      </span>
                    ),
                  },
                  {
                    key: "budget",
                    head: "Touches used",
                    cell: (row) => (
                      <span className="text-[11px] text-ink-2">
                        {row.contacts_used} contacts · {row.retries_used} retries · {row.discounts_used} offers
                      </span>
                    ),
                  },
                  {
                    key: "recovered",
                    head: "Recovered",
                    align: "right",
                    cell: (row) =>
                      row.recovered_amount_paise ? (
                        <span className="text-delta-up">{inr(row.recovered_amount_paise)}</span>
                      ) : (
                        <span className="text-muted">—</span>
                      ),
                  },
                  { key: "cost", head: "Cost", align: "right", cell: (row) => inr(row.cost_paise) },
                  {
                    key: "next",
                    head: "Next action",
                    align: "right",
                    cell: (row) =>
                      row.closed_at ? (
                        <span className="text-muted" title={row.close_reason ?? undefined}>
                          closed {relativeTime(row.closed_at)}
                        </span>
                      ) : (
                        relativeTime(row.next_action_at)
                      ),
                  },
                ]}
              />
              <Pager total={data.total} limit={LIMIT} offset={offset} onChange={setOffset} />
              <p className="mt-2 text-[11px] text-muted">{compact(data.total)} journeys.</p>
            </>
          )}
        </Resource>
      </Card>
    </>
  );
}
