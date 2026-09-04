"use client";

import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHead, PageHead } from "@/components/ui/Card";
import { Select } from "@/components/ui/Field";
import { Pager } from "@/components/ui/Pager";
import { Resource } from "@/components/ui/State";
import { api } from "@/lib/api";
import { compact, dateTime, titleCase } from "@/lib/format";
import { useAction, useResource } from "@/lib/hooks";
import { agentLabel, termLabel } from "@/lib/labels";
import type { AuditEntry } from "@/lib/types";

const LIMIT = 30;

const EVENT_TYPES = [
  "event_detected",
  "diagnosis_completed",
  "decision_made",
  "policy_evaluated",
  "action_scheduled",
  "action_executed",
  "action_blocked",
  "approval_requested",
  "approval_granted",
  "approval_rejected",
  "outcome_verified",
  "recovery_booked",
  "journey_transition",
  "journey_closed",
  "degradation_detected",
  "degradation_cleared",
  "policy_updated",
  "kill_switch_toggled",
];

const ACTOR_TONE = { human: "accent", gateway: "neutral", agent: "good", system: "neutral" } as const;

/** Blocked and rejected entries are the ones a reviewer looks for, so they get the loud tones. */
function eventTone(type: string) {
  if (type.includes("blocked") || type.includes("rejected")) return "warning" as const;
  if (type.includes("degradation_detected") || type.includes("kill_switch")) return "critical" as const;
  if (type.includes("recovery_booked") || type.includes("verified")) return "good" as const;
  return "neutral" as const;
}

export default function Audit() {
  const [eventType, setEventType] = useState("");
  const [offset, setOffset] = useState(0);
  const [open, setOpen] = useState<string | null>(null);

  const query = useMemo(
    () => ({ limit: LIMIT, offset, ...(eventType ? { event_type: eventType } : {}) }),
    [eventType, offset],
  );
  const entries = useResource(() => api.audit(query), { intervalMs: 15000, deps: [query] });
  const integrity = useResource(api.verifyAudit);
  const { pending, run } = useAction();

  const recheck = () => run("verify", integrity.refresh);

  return (
    <>
      <PageHead
        title="Audit trail"
        hint="Every detection, decision, guardrail verdict and execution, in order. Each entry hashes the one before it, so a silent edit breaks the chain."
        actions={
          <>
            {integrity.data ? (
              integrity.data.valid ? (
                <Badge tone="good">chain intact · {compact(integrity.data.entries)} entries</Badge>
              ) : (
                <Badge tone="critical">broken at #{integrity.data.broken_at}</Badge>
              )
            ) : null}
            <Button onClick={recheck} loading={pending === "verify"}>
              Re-verify chain
            </Button>
          </>
        }
      />

      <Card>
        <CardHead
          title="Log"
          hint="Newest first. Open a row to read the exact payload the entry was hashed from."
          actions={
            <Select
              label="Event type"
              value={eventType}
              onChange={(next) => {
                setEventType(next);
                setOffset(0);
              }}
              options={[
                { value: "", label: "Everything" },
                ...EVENT_TYPES.map((value) => ({ value, label: titleCase(value) })),
              ]}
            />
          }
        />
        <Resource {...entries} empty="No audit entries recorded yet.">
          {(page) => (
            <>
              <ol className="space-y-1.5">
                {page.items.map((entry) => (
                  <Row key={entry.id} entry={entry} open={open === entry.id} onToggle={setOpen} />
                ))}
              </ol>
              <Pager total={page.total} limit={page.limit} offset={page.offset} onChange={setOffset} />
            </>
          )}
        </Resource>
      </Card>
    </>
  );
}

function Row({
  entry,
  open,
  onToggle,
}: {
  entry: AuditEntry;
  open: boolean;
  onToggle: (id: string | null) => void;
}) {
  const actor = ACTOR_TONE[entry.actor as keyof typeof ACTOR_TONE] ?? "neutral";
  // System entries carry no actor name; the actor itself is the answer to "who".
  const who =
    entry.actor === "agent" ? agentLabel(entry.actor_name) : entry.actor_name || termLabel(entry.actor);
  return (
    <li className="hairline rounded-lg bg-raised">
      <button
        type="button"
        onClick={() => onToggle(open ? null : entry.id)}
        aria-expanded={open}
        className="flex w-full flex-col gap-1.5 px-3 py-2.5 text-left md:flex-row md:items-center md:gap-3 md:py-2"
      >
        {/* One line from md up; on a phone the summary and the actor each take a row of their own. */}
        <span className="flex items-center gap-2 md:flex-none">
          <span className="w-11 shrink-0 text-[11px] tabular-nums text-muted md:w-14">#{entry.sequence}</span>
          <Badge tone={eventTone(entry.event_type)}>{titleCase(entry.event_type)}</Badge>
          <span aria-hidden className="ml-auto shrink-0 text-muted md:hidden">
            {open ? "−" : "+"}
          </span>
        </span>
        <span className="min-w-0 flex-1 text-xs text-ink-2 max-md:line-clamp-2 md:truncate">{entry.summary}</span>
        <span className="flex items-center gap-2 md:flex-none">
          <Badge tone={actor} glyph={false}>
            {who}
          </Badge>
          <span className="ml-auto shrink-0 text-[11px] whitespace-nowrap text-muted md:ml-0 md:w-32 md:text-right">
            {dateTime(entry.occurred_at)}
          </span>
          <span aria-hidden className="hidden w-3 shrink-0 text-muted md:inline">
            {open ? "−" : "+"}
          </span>
        </span>
      </button>
      {open ? (
        <div className="border-t border-hairline px-3 py-2.5">
          <dl className="grid gap-x-4 gap-y-1.5 text-[11px] sm:grid-cols-2">
            <Meta label="Entity" value={`${titleCase(entry.entity_type)} · ${entry.entity_id}`} />
            <Meta
              label="Actor"
              value={who.toLowerCase() === entry.actor ? who : `${who} · ${entry.actor}`}
            />
            <Meta label="Entry hash" value={entry.entry_hash} />
            <Meta label="Previous hash" value={entry.previous_hash} />
          </dl>
          <pre className="mt-2.5 max-h-64 overflow-auto rounded-md bg-surface p-2.5 text-[11px] leading-relaxed text-ink-2">
            {JSON.stringify(entry.payload, null, 2)}
          </pre>
        </div>
      ) : null}
    </li>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5 sm:flex-row sm:gap-2">
      <dt className="shrink-0 text-muted sm:w-24">{label}</dt>
      <dd className="min-w-0 font-mono break-all text-ink-2">{value}</dd>
    </div>
  );
}
