"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { DecisionPanel } from "@/components/domain/DecisionPanel";
import { Badge } from "@/components/ui/Badge";
import { IconButton } from "@/components/ui/Button";
import { Card, CardHead, PageHead } from "@/components/ui/Card";
import { DataTable } from "@/components/ui/DataTable";
import { Select } from "@/components/ui/Field";
import { Pager } from "@/components/ui/Pager";
import { Resource, SkeletonBlock } from "@/components/ui/State";
import { api } from "@/lib/api";
import { useResource } from "@/lib/hooks";
import { compact, inr, pct, relativeTime, titleCase } from "@/lib/format";
import { causeLabel, failureCodeLabel, JOURNEY_TONE, LOSS_CLASS_LABEL, LOSS_CLASS_ORDER, LOSS_CLASS_SHORT, methodLabel, termLabel } from "@/lib/labels";
import { href } from "@/lib/routes";
import type { RiskItem } from "@/lib/types";

const LIMIT = 25;

const ORDERS = [
  { value: "priority", label: "Priority (business value)" },
  { value: "amount", label: "Amount at risk" },
  { value: "risk", label: "Risk score" },
  { value: "recent", label: "Most recent" },
];

export default function RiskRadar() {
  const [kind, setKind] = useState("");
  const [order, setOrder] = useState("priority");
  const [offset, setOffset] = useState(0);
  const [focus, setFocus] = useState<RiskItem | null>(null);

  const page = useResource(() => api.risk({ kind, order_by: order, limit: LIMIT, offset }), {
    intervalMs: 12000,
    deps: [kind, order, offset],
  });

  return (
    <>
      <PageHead
        title="Revenue risk radar"
        hint="One ranked queue across all four loss classes. Priority blends amount, customer value, urgency and how badly the event is failing."
        actions={
          <>
            <Select
              label="Loss class"
              value={kind}
              onChange={(next) => (setKind(next), setOffset(0))}
              options={[
                { value: "", label: "All classes" },
                ...LOSS_CLASS_ORDER.map((value) => ({ value, label: LOSS_CLASS_LABEL[value] })),
              ]}
            />
            <Select label="Rank by" value={order} onChange={(next) => (setOrder(next), setOffset(0))} options={ORDERS} />
          </>
        }
      />

      <Card pad={false} className="p-4 sm:p-5">
        <Resource {...page} empty="Nothing at risk right now.">
          {(data) => (
            <>
              <DataTable
                rows={data.items}
                rowKey={(row) => row.id}
                onRowClick={(row) => setFocus(focus?.id === row.id ? null : row)}
                columns={[
                  {
                    key: "ref",
                    head: "Event",
                    cell: (row) => (
                      <span>
                        <span className="text-ink">{row.external_ref}</span>
                        <span className="block text-[11px] text-muted">
                          {LOSS_CLASS_SHORT[row.kind]} · {relativeTime(row.occurred_at)}
                        </span>
                      </span>
                    ),
                  },
                  {
                    key: "customer",
                    head: "Customer",
                    cell: (row) => (
                      <span>
                        <span className="text-ink">{row.customer.name}</span>
                        <span className="block text-[11px] text-muted">
                          {termLabel(row.customer.segment)} · LTV {inr(row.customer.ltv_paise)}
                        </span>
                      </span>
                    ),
                  },
                  {
                    key: "cause",
                    head: "Diagnosis",
                    cell: (row) => (
                      <span>
                        <span className="text-ink">{causeLabel(row.root_cause)}</span>
                        <span className="block text-[11px] text-muted">
                          {pct(row.cause_confidence, 0)} confidence
                          {row.failure_code ? ` · ${failureCodeLabel(row.failure_code)}` : ""}
                        </span>
                      </span>
                    ),
                  },
                  { key: "amount", head: "At risk", align: "right", cell: (row) => inr(row.amount_paise) },
                  {
                    key: "p",
                    head: "P(recover)",
                    align: "right",
                    cell: (row) => (
                      <span>
                        {pct(row.recovery_probability, 1)}
                        <span className="block text-[11px] text-muted">
                          organic {pct(row.organic_probability, 1)}
                        </span>
                      </span>
                    ),
                  },
                  {
                    key: "erv",
                    head: "Expected recovery",
                    align: "right",
                    cell: (row) => <span className="text-delta-up">{inr(row.expected_recovery_paise)}</span>,
                  },
                  {
                    key: "state",
                    head: "Workflow",
                    cell: (row) =>
                      row.journey_state ? (
                        <Link href={href(`/journeys/${row.journey_id}`)} onClick={(event) => event.stopPropagation()}>
                          <Badge tone={JOURNEY_TONE[row.journey_state]}>{titleCase(row.journey_state)}</Badge>
                        </Link>
                      ) : row.cohort === "control" ? (
                        <Badge tone="neutral" glyph={false}>
                          control holdout
                        </Badge>
                      ) : (
                        <span className="text-muted">not yet claimed</span>
                      ),
                  },
                ]}
              />
              <Pager total={data.total} limit={LIMIT} offset={offset} onChange={setOffset} />
              <p className="mt-2 text-[11px] text-muted">
                {compact(data.total)} open events. Rows in the control holdout are deliberately left alone so the
                incremental ledger has something to measure against.
              </p>
            </>
          )}
        </Resource>
      </Card>

      {focus ? <FocusPanel item={focus} onClose={() => setFocus(null)} /> : null}
    </>
  );
}

function FocusPanel({ item, onClose }: { item: RiskItem; onClose: () => void }) {
  const decisions = useResource(() => api.riskDecisions(item.id), { deps: [item.id] });
  const anchor = useRef<HTMLDivElement>(null);

  // Opening a row appends the panel below a long table; bring it to the reader instead.
  useEffect(() => {
    anchor.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [item.id]);

  return (
    <div ref={anchor} className="scroll-mt-20">
      <Card>
        <CardHead
          title={`${item.external_ref} - ${LOSS_CLASS_LABEL[item.kind]}`}
          hint={`${inr(item.amount_paise, { precise: true })} · ${methodLabel(item.payment_method)} via ${item.route} · ${
            item.failure_reason ?? "no payment message"
          }`}
          actions={
            <IconButton label="Close event detail" onClick={onClose}>
              ✕
            </IconButton>
          }
        />
        {decisions.loading ? (
          <SkeletonBlock label="Loading decision" />
        ) : decisions.data && decisions.data.length > 0 ? (
          <DecisionPanel decision={decisions.data[0]} />
        ) : (
          <p className="text-xs text-muted">
            No decision recorded yet - this event has been scored but not planned. Run one cycle to let the
            agents pick it up.
          </p>
        )}
      </Card>
    </div>
  );
}
