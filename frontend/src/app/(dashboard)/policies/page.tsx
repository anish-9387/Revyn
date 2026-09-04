"use client";

import { useState } from "react";

import { useLive } from "@/components/layout/AppShell";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHead, PageHead } from "@/components/ui/Card";
import { NumberField, Toggle } from "@/components/ui/Field";
import { ErrorNote, SkeletonBlock } from "@/components/ui/State";
import { KeyValue } from "@/components/ui/StatTile";
import { api } from "@/lib/api";
import { dateTime, inr, pct } from "@/lib/format";
import { useAction, useResource } from "@/lib/hooks";
import type { Policy } from "@/lib/types";

const rupees = (paise: number) => Math.round(paise / 100);

export default function Policies() {
  const live = useLive();
  const policy = useResource(api.policy, { intervalMs: 20000 });
  const { pending, error, run, clearError } = useAction();
  const [draft, setDraft] = useState<Policy | null>(null);
  const [baseVersion, setBaseVersion] = useState<number | null>(null);

  // Adjusted during render, not in an effect: a version bump means the server won and local
  // edits are stale. Polling between bumps leaves the draft alone.
  if (policy.data && policy.data.version !== baseVersion) {
    setBaseVersion(policy.data.version);
    setDraft(policy.data);
  }

  if (!draft) return policy.error ? <ErrorNote message={policy.error} onRetry={policy.refresh} /> : <SkeletonBlock panel />;

  const set = <K extends keyof Policy>(key: K, value: Policy[K]) =>
    setDraft((current) => (current ? { ...current, [key]: value } : current));

  const saved = policy.data;
  const changed = saved ? DIRTY_FIELDS.filter((key) => draft[key] !== saved[key]) : [];
  const running = draft.automation_enabled && !draft.paused;

  const save = () =>
    run("save", async () => {
      const patch = Object.fromEntries(changed.map((key) => [key, draft[key]])) as Partial<Policy>;
      await api.updatePolicy(patch);
      await Promise.all([policy.refresh(), live.refresh()]);
    });

  const toggleAutomation = (enabled: boolean) =>
    run("kill", async () => {
      await api.killSwitch(enabled);
      await Promise.all([policy.refresh(), live.refresh()]);
    });

  return (
    <>
      <PageHead
        title="Guardrails"
        hint="Every limit here is enforced in code before an action can execute. Nothing downstream can widen them at run time."
        actions={
          <>
            {changed.length > 0 ? (
              <Badge tone="warning">{changed.length} unsaved</Badge>
            ) : (
              <Badge tone="good">in sync</Badge>
            )}
            <Button variant="primary" onClick={save} disabled={changed.length === 0} loading={pending === "save"}>
              Save policy
            </Button>
          </>
        }
      />

      {error ? <ErrorNote message={error} onRetry={clearError} /> : null}

      <Card>
        <CardHead
          title="Kill switch"
          hint="One control stops every outbound action immediately. In-flight journeys are paused, not lost."
          actions={
            <Badge tone={running ? "good" : "critical"}>
              {running ? "automation live" : "automation halted"}
            </Badge>
          }
        />
        <div className="grid gap-4 md:grid-cols-2">
          <Toggle
            label="Autonomous execution"
            hint="When off, Revyn keeps detecting and planning but never contacts a customer or retries a charge."
            checked={draft.automation_enabled}
            onChange={toggleAutomation}
            disabled={pending === "kill"}
          />
          <KeyValue
            items={[
              ["Policy", `${draft.name} · v${draft.version}`],
              ["Last changed", dateTime(draft.updated_at)],
              ["Paused", draft.paused ? "Yes" : "No"],
            ]}
          />
        </div>
      </Card>

      <div className="grid gap-4 xl:grid-cols-3">
        <Card>
          <CardHead title="Friction budget" hint="Per customer, per journey. Exhaust it and Revyn stops, silently." />
          <div className="space-y-4">
            <NumberField
              label="Maximum contacts"
              value={draft.max_contacts}
              onChange={(next) => set("max_contacts", next)}
              max={10}
              hint="Counts every email, SMS, WhatsApp and voice attempt together."
            />
            <NumberField
              label="Maximum retries"
              value={draft.max_retries}
              onChange={(next) => set("max_retries", next)}
              max={6}
              hint="Silent gateway retries. Not visible to the customer, but they still cost money."
            />
            <NumberField
              label="Maximum discount offers"
              value={draft.max_discount_offers}
              onChange={(next) => set("max_discount_offers", next)}
              max={5}
            />
            <NumberField
              label="Maximum voice attempts"
              value={draft.max_voice_attempts}
              onChange={(next) => set("max_voice_attempts", next)}
              max={5}
            />
            <NumberField
              label="Contact cooldown"
              value={draft.contact_cooldown_minutes}
              onChange={(next) => set("contact_cooldown_minutes", next)}
              max={2880}
              step={15}
              suffix="min"
              hint="Minimum gap between two touches, across all journeys for the same customer."
            />
          </div>
        </Card>

        <Card>
          <CardHead title="Money limits" hint="Discount ceilings and the point where a human must sign off." />
          <div className="space-y-4">
            <NumberField
              label="Maximum discount"
              value={draft.max_discount_pct}
              onChange={(next) => set("max_discount_pct", next)}
              max={50}
              suffix="%"
              hint="A hard ceiling. No recommendation can exceed it, whatever the expected value."
            />
            <NumberField
              label="Discount approval threshold"
              value={draft.discount_approval_pct}
              onChange={(next) => set("discount_approval_pct", next)}
              max={50}
              suffix="%"
              hint="Discounts at or above this need a human."
            />
            <NumberField
              label="Human approval above"
              value={rupees(draft.human_approval_amount_paise)}
              onChange={(next) => set("human_approval_amount_paise", next * 100)}
              step={500}
              max={1000000}
              suffix="₹"
              hint={`Currently ${inr(draft.human_approval_amount_paise)}.`}
            />
            <NumberField
              label="Voice approval above"
              value={rupees(draft.voice_approval_amount_paise)}
              onChange={(next) => set("voice_approval_amount_paise", next * 100)}
              step={500}
              max={1000000}
              suffix="₹"
              hint={`Currently ${inr(draft.voice_approval_amount_paise)}.`}
            />
            <NumberField
              label="Minimum expected value"
              value={rupees(draft.min_expected_value_paise)}
              onChange={(next) => set("min_expected_value_paise", next * 100)}
              step={10}
              max={100000}
              suffix="₹"
              hint="Below this, doing nothing is the better decision and Revyn takes it."
            />
          </div>
        </Card>

        <Card>
          <CardHead title="Confidence and timing" hint="When Revyn is allowed to act, and how patiently." />
          <div className="space-y-4">
            <NumberField
              label="Minimum confidence"
              value={draft.min_confidence}
              onChange={(next) => set("min_confidence", next)}
              max={1}
              step={0.01}
              hint={`Acts only when the calibrated recovery probability clears ${pct(draft.min_confidence, 0)}.`}
            />
            <NumberField
              label="Retry delay"
              value={draft.retry_delay_minutes}
              onChange={(next) => set("retry_delay_minutes", next)}
              max={1440}
              step={5}
              suffix="min"
            />
            <NumberField
              label="Follow-up delay"
              value={draft.followup_delay_hours}
              onChange={(next) => set("followup_delay_hours", next)}
              max={168}
              suffix="hrs"
            />
            <NumberField
              label="Journey expiry"
              value={draft.journey_ttl_hours}
              onChange={(next) => set("journey_ttl_hours", next)}
              max={720}
              suffix="hrs"
              hint="After this, a journey expires rather than chasing indefinitely."
            />
          </div>
        </Card>
      </div>

      <Card>
        <CardHead title="Behavioural safeguards" hint="Rules that stop Revyn making a bad situation worse." />
        <div className="grid gap-5 md:grid-cols-2">
          <Toggle
            label="Respect quiet hours"
            hint={`No customer contact between ${draft.quiet_hours_start}:00 and ${draft.quiet_hours_end}:00 local time. Retries still run - they are silent.`}
            checked={draft.quiet_hours_enforced}
            onChange={(next) => set("quiet_hours_enforced", next)}
          />
          <Toggle
            label="Degradation retry guard"
            hint="Suppress retries on a payment route while it is failing abnormally, instead of burning attempts against a broken gateway."
            checked={draft.degradation_retry_guard}
            onChange={(next) => set("degradation_retry_guard", next)}
          />
          <NumberField
            label="Quiet hours start"
            value={draft.quiet_hours_start}
            onChange={(next) => set("quiet_hours_start", next)}
            max={23}
            suffix="hr"
          />
          <NumberField
            label="Quiet hours end"
            value={draft.quiet_hours_end}
            onChange={(next) => set("quiet_hours_end", next)}
            max={23}
            suffix="hr"
          />
        </div>
        <p className="mt-4 border-t border-hairline pt-3 text-[11px] leading-relaxed text-muted">
          Changes are versioned and written to the audit trail with the actor that made them. Test a change on the{" "}
          strategy simulator before saving it here - the simulator replays real at-risk events against both policies.
        </p>
      </Card>
    </>
  );
}

const DIRTY_FIELDS = [
  "max_contacts",
  "max_retries",
  "max_discount_offers",
  "max_voice_attempts",
  "contact_cooldown_minutes",
  "max_discount_pct",
  "discount_approval_pct",
  "human_approval_amount_paise",
  "voice_approval_amount_paise",
  "min_expected_value_paise",
  "min_confidence",
  "retry_delay_minutes",
  "followup_delay_hours",
  "journey_ttl_hours",
  "quiet_hours_start",
  "quiet_hours_end",
  "quiet_hours_enforced",
  "degradation_retry_guard",
] as const satisfies readonly (keyof Policy)[];
