"use client";

import { LedgerWaterfall } from "@/components/charts/LedgerWaterfall";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHead, PageHead } from "@/components/ui/Card";
import { DataTable } from "@/components/ui/DataTable";
import { Resource } from "@/components/ui/State";
import { KeyValue, StatRow, StatTile } from "@/components/ui/StatTile";
import { api } from "@/lib/api";
import { compact, inr, pct, relativeTime, titleCase } from "@/lib/format";
import { useResource } from "@/lib/hooks";
import { actionLabel, LOSS_CLASS_LABEL } from "@/lib/labels";
import type { EventKind } from "@/lib/types";

export default function Ledger() {
  const summary = useResource(api.ledgerSummary, { intervalMs: 15000 });
  const entries = useResource(() => api.ledgerEntries(40), { intervalMs: 15000 });

  return (
    <>
      <PageHead
        title="Incremental recovery ledger"
        hint="Gross recovery is easy to claim. This page counts only what Revyn can defend: recovery minus the organic baseline minus the cost of getting it."
      />

      <Resource {...summary} empty="Nothing booked yet.">
        {(data) => (
          <>
            <StatRow>
              <StatTile
                label="Incremental net recovered"
                value={inr(data.incremental_net_paise)}
                accent="var(--delta-up)"
                emphasis
                sub={`${compact(data.entries)} booked recoveries`}
              />
              <StatTile label="Gross recovered" value={inr(data.gross_recovered_paise)} sub="Before deductions" />
              <StatTile
                label="Organic estimate"
                value={inr(data.organic_estimate_paise)}
                sub="Would have returned anyway"
              />
              <StatTile
                label="Cost per recovery"
                value={inr(data.cost_per_recovery_paise, { precise: true })}
                sub={`${inr(data.cost_paise)} spent in total`}
              />
            </StatRow>

            <div className="grid gap-4 xl:grid-cols-2">
              <LedgerWaterfall
                gross={data.gross_recovered_paise}
                organic={data.organic_estimate_paise}
                cost={data.cost_paise}
                incremental={data.incremental_net_paise}
              />

              <Card>
                <CardHead
                  title="Baseline recovery rate"
                  hint="Measured from customers not contacted, so credit is given only for lift over organic behavior."
                />
                <KeyValue
                  items={[
                    [
                      "Control recovery rate",
                      `${pct(data.cohort_organic_rates.overall.rate, 1)} (n=${compact(data.cohort_organic_rates.overall.sample)})`,
                    ],
                    ...Object.entries(data.cohort_organic_rates.by_kind).map(
                      ([kind, stat]) =>
                        [
                          LOSS_CLASS_LABEL[kind as EventKind] ?? titleCase(kind),
                          `${pct(stat.rate, 1)} (n=${compact(stat.sample)})`,
                        ] as [string, string],
                    ),
                  ]}
                />
                <p className="mt-3 text-[11px] leading-relaxed text-muted">
                  A recovery is credited to Revyn only in proportion to how unlikely it was to happen on its own.
                </p>
              </Card>
            </div>

            <Card>
              <CardHead
                title="Which actions earned their keep"
                hint="Incremental net per action, not raw recovery count — cheap nudges often beat expensive escalations."
              />
              <DataTable
                rows={data.by_action}
                rowKey={(row) => row.action}
                columns={[
                  { key: "action", head: "Action", cell: (row) => actionLabel(row.action) },
                  { key: "n", head: "Recoveries", align: "right", cell: (row) => compact(row.recoveries) },
                  { key: "gross", head: "Gross", align: "right", cell: (row) => inr(row.gross_recovered_paise) },
                  { key: "cost", head: "Cost", align: "right", cell: (row) => inr(row.cost_paise) },
                  {
                    key: "net",
                    head: "Incremental net",
                    align: "right",
                    cell: (row) => (
                      <span className={row.incremental_net_paise > 0 ? "text-delta-up" : "text-serious"}>
                        {inr(row.incremental_net_paise)}
                      </span>
                    ),
                  },
                ]}
              />
            </Card>
          </>
        )}
      </Resource>

      <Card>
        <CardHead title="Booked recoveries" hint="Most recent first, with the attribution method used for each." />
        <Resource {...entries} empty="No recoveries booked yet.">
          {(rows) => (
            <DataTable
              dense
              rows={rows}
              rowKey={(row) => row.id}
              columns={[
                { key: "action", head: "Action", cell: (row) => actionLabel(row.action) },
                {
                  key: "cohort",
                  head: "Cohort",
                  cell: (row) => (
                    <Badge tone={row.cohort === "control" ? "neutral" : "accent"} glyph={false}>
                      {row.cohort}
                    </Badge>
                  ),
                },
                { key: "gross", head: "Gross", align: "right", cell: (row) => inr(row.gross_recovered_paise) },
                {
                  key: "organic",
                  head: "Organic",
                  align: "right",
                  cell: (row) => (
                    <span className="text-muted">
                      {inr(row.organic_estimate_paise)} &middot; {pct(row.organic_probability, 0)}
                    </span>
                  ),
                },
                { key: "cost", head: "Cost", align: "right", cell: (row) => inr(row.cost_paise) },
                {
                  key: "net",
                  head: "Incremental",
                  align: "right",
                  cell: (row) => <span className="text-delta-up">{inr(row.incremental_net_paise)}</span>,
                },
                {
                  key: "method",
                  head: "Attribution",
                  cell: (row) => <span className="text-[11px] text-muted">{titleCase(row.attribution_method)}</span>,
                },
                { key: "when", head: "When", align: "right", cell: (row) => relativeTime(row.created_at) },
              ]}
            />
          )}
        </Resource>
      </Card>
    </>
  );
}
