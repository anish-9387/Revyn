"use client";

import { CalibrationChart } from "@/components/charts/CalibrationChart";
import { LedgerWaterfall } from "@/components/charts/LedgerWaterfall";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHead, PageHead } from "@/components/ui/Card";
import { DataTable } from "@/components/ui/DataTable";
import { Resource, Spinner } from "@/components/ui/State";
import { KeyValue, StatRow, StatTile } from "@/components/ui/StatTile";
import { api } from "@/lib/api";
import { compact, inr, pct, relativeTime, titleCase } from "@/lib/format";
import { useResource } from "@/lib/hooks";
import { actionLabel } from "@/lib/labels";

export default function Ledger() {
  const summary = useResource(api.ledgerSummary, { intervalMs: 15000 });
  const entries = useResource(() => api.ledgerEntries(40), { intervalMs: 15000 });
  const model = useResource(api.model);

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
                  title="Organic baseline, measured"
                  hint="Read from the untouched control holdout where the sample is large enough, and from the model where it is not."
                />
                <KeyValue
                  items={[
                    [
                      "Control recovery rate",
                      `${pct(data.cohort_organic_rates.overall.rate, 1)} (n=${compact(data.cohort_organic_rates.overall.sample)})`,
                    ],
                    ...Object.entries(data.cohort_organic_rates.by_kind).map(
                      ([kind, stat]) =>
                        [titleCase(kind), `${pct(stat.rate, 1)} (n=${compact(stat.sample)})`] as [string, string],
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
        <CardHead
          title="Recovery confidence"
          hint="A probability is only useful if it is honest. These are holdout numbers, not training numbers."
        />
        {!model.data ? (
          <Spinner label="Loading model metrics" />
        ) : model.data.metadata.trained && model.data.metadata.holdout ? (
          <div className="grid gap-4 xl:grid-cols-[19rem_1fr]">
            <KeyValue
              items={[
                ["Algorithm", model.data.metadata.algorithm ?? "—"],
                ["Version", model.data.metadata.version ?? "—"],
                ["Training rows", compact(model.data.metadata.training_rows ?? 0)],
                ["Holdout events", compact(model.data.metadata.holdout.samples)],
                ["Brier score", model.data.metadata.holdout.brier_score.toFixed(3)],
                ["Log loss", model.data.metadata.holdout.log_loss.toFixed(3)],
                ["ROC AUC", model.data.metadata.holdout.roc_auc.toFixed(3)],
                ["Calibration error", model.data.metadata.holdout.calibration_error.toFixed(3)],
                ["Base recovery rate", pct(model.data.metadata.holdout.base_rate, 1)],
                [
                  "Artifact age",
                  model.data.artifact_age_hours === null ? "—" : `${model.data.artifact_age_hours.toFixed(1)}h`,
                ],
              ]}
            />
            <CalibrationChart bins={model.data.metadata.holdout.bins} />
          </div>
        ) : (
          <p className="text-xs leading-relaxed text-ink-2">
            <Badge tone="warning" className="mr-2">
              heuristic
            </Badge>
            No trained artifact is loaded, so Revyn is running its transparent heuristic predictor. Train one with{" "}
            <code className="text-muted">POST /api/v1/ops/model/train</code> to see calibration.
          </p>
        )}
      </Card>

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
