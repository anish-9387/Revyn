"use client";

import { useMemo } from "react";

import { Badge } from "@/components/ui/Badge";
import { Card, CardHead, PageHead } from "@/components/ui/Card";
import { DataTable } from "@/components/ui/DataTable";
import { ShareBar } from "@/components/ui/Meter";
import { Resource } from "@/components/ui/State";
import { api } from "@/lib/api";
import { compact, inr, pct, titleCase } from "@/lib/format";
import { useResource } from "@/lib/hooks";
import { LOSS_CLASS_LABEL, LOSS_CLASS_ORDER, actionLabel, causeLabel } from "@/lib/labels";
import type { EventKind, PlaybookEntry } from "@/lib/types";

/** Weighted across every context: which action wins for this merchant, regardless of segment. */
function channelRollup(entries: PlaybookEntry[]) {
  const totals = new Map<string, { trials: number; wins: number }>();
  for (const entry of entries) {
    for (const alt of [
      { action: entry.best_action, recovery_rate: entry.recovery_rate, trials: entry.trials },
      ...entry.alternatives,
    ]) {
      const row = totals.get(alt.action) ?? { trials: 0, wins: 0 };
      row.trials += alt.trials;
      row.wins += alt.recovery_rate * alt.trials;
      totals.set(alt.action, row);
    }
  }
  return [...totals.entries()]
    .filter(([, row]) => row.trials > 0)
    .map(([action, row]) => ({ action, trials: row.trials, rate: row.wins / row.trials }))
    .sort((a, b) => b.rate - a.rate);
}

export default function Playbook() {
  const playbook = useResource(api.playbook, { intervalMs: 20000 });
  const channels = useMemo(() => channelRollup(playbook.data?.entries ?? []), [playbook.data]);
  const best = channels[0];
  const worst = channels[channels.length - 1];

  return (
    <>
      <PageHead
        title="Merchant recovery memory"
        hint="Revyn does not assume what works. It learns per segment - loss class, cause layer, ticket size - and remembers only what it has actually tried."
      />

      <div className="grid gap-4 xl:grid-cols-[1fr_20rem]">
        <Card>
          <CardHead
            title="What works for this merchant"
            hint="Channel performance pooled across every segment, weighted by how often each was tried."
          />
          {channels.length === 0 ? (
            <p className="py-6 text-xs text-muted">No outcomes recorded yet. Run a recovery cycle first.</p>
          ) : (
            <div className="space-y-2">
              {channels.map((row) => (
                <ShareBar
                  key={row.action}
                  label={`${actionLabel(row.action)} · ${compact(row.trials)} tries`}
                  value={pct(row.rate, 1)}
                  share={row.rate}
                  showShare={false}
                  colour={row.rate >= 0.5 ? "var(--good)" : row.rate >= 0.25 ? "var(--series-4)" : "var(--serious)"}
                />
              ))}
            </div>
          )}
        </Card>

        <Card>
          <CardHead title="The learned quirk" hint="Not configured by anyone - discovered from outcomes." />
          {best && worst && best.action !== worst.action ? (
            <p className="text-xs leading-relaxed text-ink-2">
              <span className="text-good">{actionLabel(best.action)}</span> recovers{" "}
              <span className="tabular-nums">{pct(best.rate, 1)}</span> of the events it touches, while{" "}
              <span className="text-serious">{actionLabel(worst.action)}</span> only manages{" "}
              <span className="tabular-nums">{pct(worst.rate, 1)}</span>. Revenue-weighted, that gap is why the
              Strategist keeps reaching for the first and stops paying for the second - even where both are allowed
              by policy.
            </p>
          ) : (
            <p className="text-xs text-muted">Not enough distinct outcomes yet to separate the channels.</p>
          )}
          <p className="mt-3 border-t border-hairline pt-3 text-[11px] leading-relaxed text-muted">
            A segment is only trusted once it has{" "}
            <span className="tabular-nums text-ink-2">{playbook.data?.min_trials_for_confidence ?? 0}</span> trials.
            Below that Revyn uses broader benchmarks rather than a small-sample hunch.
          </p>
        </Card>
      </div>

      <Resource {...playbook} empty="No learned segments yet.">
        {(data) =>
          LOSS_CLASS_ORDER.filter((kind) => data.entries.some((e) => e.loss_class === kind)).map((kind) => {
            const rows = data.entries
              .filter((entry) => entry.loss_class === kind)
              .sort((a, b) => b.recovered_paise - a.recovered_paise);
            return (
              <Card key={kind}>
                <CardHead
                  title={LOSS_CLASS_LABEL[kind as EventKind]}
                  hint={`${compact(rows.length)} learned segments`}
                />
                <DataTable
                  dense
                  rows={rows}
                  rowKey={(row) => row.context_key}
                  columns={[
                    {
                      key: "segment",
                      head: "Segment",
                      cell: (row) => (
                        <span>
                          {causeLabel(row.cause_layer)}
                          <span className="text-muted"> &middot; {titleCase(row.value_band)} ticket</span>
                        </span>
                      ),
                    },
                    {
                      key: "best",
                      head: "Best known action",
                      cell: (row) => (
                        <span className="flex items-center gap-2">
                          {row.best_action_label}
                          {row.trials >= data.min_trials_for_confidence ? (
                            <Badge tone="good">trusted</Badge>
                          ) : (
                            <Badge tone="warning">thin evidence</Badge>
                          )}
                        </span>
                      ),
                    },
                    {
                      key: "rate",
                      head: "Recovery rate",
                      align: "right",
                      cell: (row) => <span className="tabular-nums">{pct(row.recovery_rate, 1)}</span>,
                    },
                    { key: "trials", head: "Trials", align: "right", cell: (row) => compact(row.trials) },
                    {
                      key: "recovered",
                      head: "Recovered",
                      align: "right",
                      cell: (row) => inr(row.recovered_paise),
                    },
                    {
                      key: "alts",
                      head: "Runners-up",
                      cell: (row) =>
                        row.alternatives.length === 0 ? (
                          <span className="text-muted">nothing else tried</span>
                        ) : (
                          <span className="text-[11px] text-muted">
                            {row.alternatives
                              .slice(0, 2)
                              .map((alt) => `${alt.label} ${pct(alt.recovery_rate, 0)} (${alt.trials})`)
                              .join(" · ")}
                          </span>
                        ),
                    },
                  ]}
                />
              </Card>
            );
          })
        }
      </Resource>
    </>
  );
}
