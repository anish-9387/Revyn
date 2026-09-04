"use client";

import { useState } from "react";

import { ActionMixBars } from "@/components/charts/ActionMixBars";
import { useLive } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { Card, CardHead, PageHead } from "@/components/ui/Card";
import { NumberField, Toggle } from "@/components/ui/Field";
import { EmptyState, SkeletonBlock } from "@/components/ui/State";
import { KeyValue } from "@/components/ui/StatTile";
import { api } from "@/lib/api";
import { compact, inr, pct } from "@/lib/format";
import { useAction } from "@/lib/hooks";
import { POLICY_FIELD_LABEL, termLabel } from "@/lib/labels";
import type { SimulationArm, SimulationResult } from "@/lib/types";

type Overrides = Record<string, number | boolean>;

const rupees = (paise: number) => Math.round(paise / 100);
const fieldLabel = (field: string) => POLICY_FIELD_LABEL[field] ?? termLabel(field);

/** A changed field reads in the same units the form showed, not the paise the API speaks. */
const moveValue = (field: string, raw: number | boolean | string) =>
  typeof raw === "boolean"
    ? raw
      ? "on"
      : "off"
    : field.endsWith("_paise")
      ? inr(Number(raw))
      : String(raw);

export default function Simulator() {
  const { policy, refresh } = useLive();
  const [draft, setDraft] = useState<Overrides>({});
  const [result, setResult] = useState<SimulationResult | null>(null);
  const { pending, error, run } = useAction();

  if (!policy) return <SkeletonBlock panel label="Loading the live policy" />;

  const value = (field: keyof typeof policy) =>
    (draft[field] as number | boolean | undefined) ?? (policy[field] as number | boolean);
  const set = (field: string, next: number | boolean) => setDraft((state) => ({ ...state, [field]: next }));

  const simulate = () =>
    void run("simulate", async () => setResult(await api.simulate(draft, 400)));
  const apply = () =>
    void run("apply", async () => {
      await api.applySimulation(draft);
      setDraft({});
      setResult(null);
      await refresh();
    });

  return (
    <>
      <PageHead
        title="Recovery strategy simulator"
        hint="Score the whole open book under a proposed policy before it touches a single customer. Nothing is written until you apply it."
        actions={
          <>
            <Button variant="primary" size="sm" loading={pending === "simulate"} onClick={simulate}>
              Run simulation
            </Button>
            <Button
              size="sm"
              disabled={Object.keys(draft).length === 0}
              loading={pending === "apply"}
              onClick={apply}
            >
              Apply to live policy
            </Button>
          </>
        }
      />
      {error ? <p className="text-xs text-critical">{error}</p> : null}

      <div className="grid gap-4 xl:grid-cols-[20rem_1fr]">
        <Card>
          <CardHead title="Proposed policy" hint="Only changed fields are sent." />
          <div className="space-y-3.5">
            <NumberField
              label="Max contacts per customer"
              value={value("max_contacts") as number}
              onChange={(next) => set("max_contacts", next)}
              min={0}
              max={8}
            />
            <NumberField
              label="Max payment retries"
              value={value("max_retries") as number}
              onChange={(next) => set("max_retries", next)}
              min={0}
              max={6}
            />
            <NumberField
              label="Max discount offers"
              value={value("max_discount_offers") as number}
              onChange={(next) => set("max_discount_offers", next)}
              min={0}
              max={3}
            />
            <NumberField
              label="Max discount"
              value={value("max_discount_pct") as number}
              onChange={(next) => set("max_discount_pct", next)}
              min={0}
              max={40}
              step={0.5}
              suffix="%"
            />
            <NumberField
              label="Minimum confidence to act"
              hint="Below this recovery probability Revyn prefers to do nothing."
              value={value("min_confidence") as number}
              onChange={(next) => set("min_confidence", next)}
              min={0}
              max={1}
              step={0.01}
            />
            <NumberField
              label="Minimum expected value"
              value={rupees(value("min_expected_value_paise") as number)}
              onChange={(next) => set("min_expected_value_paise", next * 100)}
              min={0}
              step={10}
              suffix="₹"
              hint={`Currently ${inr(value("min_expected_value_paise") as number)}.`}
            />
            <NumberField
              label="Human approval above"
              value={rupees(value("human_approval_amount_paise") as number)}
              onChange={(next) => set("human_approval_amount_paise", next * 100)}
              min={0}
              step={500}
              suffix="₹"
              hint={`Currently ${inr(value("human_approval_amount_paise") as number)}.`}
            />
            <Toggle
              label="Hold retries during degradation"
              hint="Stops Revyn spending attempts into a route that is already failing."
              checked={value("degradation_retry_guard") as boolean}
              onChange={(next) => set("degradation_retry_guard", next)}
            />
            <Toggle
              label="Respect quiet hours"
              checked={value("quiet_hours_enforced") as boolean}
              onChange={(next) => set("quiet_hours_enforced", next)}
            />
          </div>
        </Card>

        <div className="space-y-4">
          {result ? (
            <Outcome result={result} />
          ) : (
            <EmptyState
              title="No simulation run yet"
              hint="Every open event is re-scored against the proposed guardrails, alongside the legacy fixed-retry workflow for reference."
            />
          )}
        </div>
      </div>
    </>
  );
}

const ARMS: { key: keyof Pick<SimulationResult, "legacy_baseline" | "current" | "proposed">; colour: string }[] = [
  { key: "legacy_baseline", colour: "var(--axis)" },
  { key: "current", colour: "var(--series-3)" },
  { key: "proposed", colour: "var(--series-1)" },
];

function Outcome({ result }: { result: SimulationResult }) {
  const { delta, delta_vs_legacy: legacyDelta, changed_fields: changed } = result;
  const fewerContacts = delta.contact_delta <= 0;
  const moreMoney = delta.net_expected_delta_paise >= 0;

  return (
    <>
      <Card>
        <CardHead
          title="Proposed against live"
          hint={`Scored on ${compact(result.sample_size)} open events. ${
            Object.keys(changed).length === 0
              ? "No fields changed yet — this is the live policy scored against itself."
              : Object.entries(changed)
                  .map(([field, move]) => `${fieldLabel(field)}: ${moveValue(field, move.from)} → ${moveValue(field, move.to)}`)
                  .join("; ")
          }`}
        />
        <div className="grid gap-4 sm:grid-cols-3">
          {ARMS.map(({ key, colour }) => (
            <ArmCard key={key} arm={result[key]} colour={colour} />
          ))}
        </div>
        <div className="mt-4 border-t border-hairline pt-3">
          <p className="text-xs leading-relaxed text-ink-2">
            {moreMoney && fewerContacts ? (
              <span className="text-delta-up">
                Better on both axes: {inr(Math.abs(delta.net_expected_delta_paise))} more expected net from{" "}
                {compact(Math.abs(delta.contact_delta))} fewer customer contacts.
              </span>
            ) : moreMoney ? (
              <>
                {inr(delta.net_expected_delta_paise)} more expected net, but{" "}
                {compact(delta.contact_delta)} additional customer contacts —{" "}
                {pct(Math.abs(delta.contact_change_pct), 0)} more friction spent.
              </>
            ) : (
              <span className="text-serious">
                This policy gives up {inr(Math.abs(delta.net_expected_delta_paise))} of expected net.
              </span>
            )}
          </p>
          <p className="mt-1.5 text-[11px] text-muted">
            Against the legacy fixed-retry workflow: {inr(legacyDelta.net_expected_delta_paise)} net and{" "}
            {compact(legacyDelta.contact_delta)} contacts.
          </p>
        </div>
      </Card>

      <ActionMixBars
        title="How the action mix shifts"
        hint="The interesting policies do not just do less — they redistribute effort towards actions that actually convert."
        arms={ARMS.map(({ key, colour }) => ({
          label: result[key].label,
          colour,
          mix: result[key].action_mix,
        }))}
      />
    </>
  );
}

function ArmCard({ arm, colour }: { arm: SimulationArm; colour: string }) {
  return (
    <div className="hairline rounded-lg bg-raised p-3">
      <p className="flex items-center gap-2 text-xs font-medium text-ink">
        <span aria-hidden className="inline-block h-2.5 w-2.5 rounded-[2px]" style={{ background: colour }} />
        {arm.label}
      </p>
      <p className="mt-2 text-lg font-semibold tabular-nums text-ink">{inr(arm.net_expected_paise)}</p>
      <p className="text-[11px] text-muted">expected net</p>
      <div className="mt-3">
        <KeyValue
          items={[
            ["Expected recovery", inr(arm.expected_recovery_paise)],
            ["Incremental", inr(arm.expected_incremental_paise)],
            ["Interventions", compact(arm.interventions)],
            ["Customer contacts", compact(arm.customer_contacts)],
            ["Left alone", compact(arm.do_nothing)],
            ["Needs approval", compact(arm.approvals_required)],
            ["Blocked", compact(arm.blocked)],
            ["Discount spend", inr(arm.discount_cost_paise)],
          ]}
        />
      </div>
    </div>
  );
}
