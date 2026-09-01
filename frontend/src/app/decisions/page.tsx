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
import { inr, pct, relativeTime } from "@/lib/format";
import { useResource } from "@/lib/hooks";
import { ACTION_LABEL, actionLabel, VERDICT_TONE } from "@/lib/labels";
import { href } from "@/lib/routes";

const LIMIT = 25;

export default function Decisions() {
  const router = useRouter();
  const [action, setAction] = useState("");
  const [verdict, setVerdict] = useState("");
  const [offset, setOffset] = useState(0);
  const page = useResource(() => api.decisions({ action, verdict, limit: LIMIT, offset }), {
    intervalMs: 12000,
    deps: [action, verdict, offset],
  });

  return (
    <>
      <PageHead
        title="Decision log"
        hint="Every choice Revyn made, with the alternatives it rejected and the price it put on each one."
        actions={
          <>
            <Select
              label="Action"
              value={action}
              onChange={(next) => (setAction(next), setOffset(0))}
              options={[
                { value: "", label: "All actions" },
                ...Object.entries(ACTION_LABEL).map(([value, label]) => ({ value, label })),
              ]}
            />
            <Select
              label="Guardrail"
              value={verdict}
              onChange={(next) => (setVerdict(next), setOffset(0))}
              options={[
                { value: "", label: "Any verdict" },
                { value: "allow", label: "Allowed" },
                { value: "require_approval", label: "Needed approval" },
                { value: "block", label: "Blocked" },
              ]}
            />
          </>
        }
      />

      <Card>
        <Resource {...page} empty="No decisions recorded yet.">
          {(data) => (
            <>
              <DataTable
                rows={data.items}
                rowKey={(row) => row.id}
                onRowClick={(row) => router.push(href(`/decisions/${row.id}`))}
                columns={[
                  { key: "action", head: "Chosen action", cell: (row) => actionLabel(row.chosen_action) },
                  {
                    key: "verdict",
                    head: "Guardrail",
                    cell: (row) => (
                      <span title={row.policy_reasons.join(", ")}>
                        <Badge tone={VERDICT_TONE[row.policy_verdict]}>
                          {row.policy_verdict.replace(/_/g, " ")}
                        </Badge>
                      </span>
                    ),
                  },
                  {
                    key: "p",
                    head: "P(recover)",
                    align: "right",
                    cell: (row) => pct(row.recovery_probability, 1),
                  },
                  {
                    key: "organic",
                    head: "P(organic)",
                    align: "right",
                    cell: (row) => <span className="text-muted">{pct(row.organic_probability, 1)}</span>,
                  },
                  {
                    key: "uplift",
                    head: "Uplift",
                    align: "right",
                    cell: (row) => (
                      <span className={row.uplift > 0 ? "text-delta-up" : "text-muted"}>
                        {row.uplift > 0 ? "+" : ""}
                        {pct(row.uplift, 1)}
                      </span>
                    ),
                  },
                  {
                    key: "ev",
                    head: "Expected value",
                    align: "right",
                    cell: (row) => inr(row.expected_value_paise),
                  },
                  {
                    key: "options",
                    head: "Options priced",
                    align: "right",
                    cell: (row) => row.alternatives.length,
                  },
                  { key: "when", head: "When", align: "right", cell: (row) => relativeTime(row.created_at) },
                ]}
              />
              <Pager total={data.total} limit={LIMIT} offset={offset} onChange={setOffset} />
            </>
          )}
        </Resource>
      </Card>
    </>
  );
}
