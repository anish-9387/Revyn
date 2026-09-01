"use client";

import { AgentTrace } from "@/components/domain/AgentTrace";
import { OptionTable } from "@/components/domain/OptionTable";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHead } from "@/components/ui/Card";
import { KeyValue } from "@/components/ui/StatTile";
import { dateTime, inr, pct } from "@/lib/format";
import { actionLabel, VERDICT_TONE } from "@/lib/labels";
import type { Decision } from "@/lib/types";

export function DecisionPanel({
  decision,
  explanations = [],
}: {
  decision: Decision;
  explanations?: string[];
}) {
  return (
    <div className="grid gap-4 xl:grid-cols-[1.35fr_1fr]">
      <div className="space-y-4">
        <Card>
          <CardHead
            title={`Chosen: ${actionLabel(decision.chosen_action)}`}
            hint="Selected on expected value after cost, friction and guardrails — not on raw success probability."
            actions={<Badge tone={VERDICT_TONE[decision.policy_verdict]}>{decision.policy_verdict.replace(/_/g, " ")}</Badge>}
          />
          <KeyValue
            items={[
              ["P(recover | this action)", pct(decision.recovery_probability, 1)],
              ["P(recover | do nothing)", pct(decision.organic_probability, 1)],
              [
                "Causal uplift",
                <span key="uplift" className="text-delta-up">
                  +{pct(decision.uplift, 1)}
                </span>,
              ],
              ["Expected recovery", inr(decision.expected_recovery_paise)],
              ["Expected value after cost", inr(decision.expected_value_paise)],
              ["Model", decision.model_version],
              ["Reasoning", decision.reasoning_provider],
              ["Decided", dateTime(decision.created_at)],
            ]}
          />
          {decision.rationale.length > 0 ? (
            <ul className="mt-4 space-y-1.5 border-t border-hairline pt-3">
              {decision.rationale.map((line) => (
                <li key={line} className="text-xs leading-relaxed text-ink-2">
                  <span aria-hidden className="mr-1.5 text-series-1">
                    ▸
                  </span>
                  {line}
                </li>
              ))}
            </ul>
          ) : null}
        </Card>

        <Card>
          <CardHead
            title="Options considered"
            hint="Every allowed action was priced against the same event, so the comparison is apples to apples."
          />
          <OptionTable options={decision.alternatives} chosen={decision.chosen_action} />
        </Card>
      </div>

      <div className="space-y-4">
        <Card>
          <CardHead title="Evidence" hint="Each line is a number the investigator actually computed." />
          {decision.evidence.length > 0 ? (
            <ul className="space-y-1.5">
              {decision.evidence.map((line) => (
                <li key={line} className="text-xs leading-relaxed text-ink-2">
                  <span aria-hidden className="mr-1.5 text-muted">
                    •
                  </span>
                  {line}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-muted">No evidence recorded.</p>
          )}
        </Card>

        {decision.policy_reasons.length > 0 || explanations.length > 0 ? (
          <Card>
            <CardHead title="Guardrail findings" hint="Rules that fired while evaluating this action." />
            <ul className="space-y-1.5">
              {(explanations.length > 0 ? explanations : decision.policy_reasons).map((line) => (
                <li key={line} className="text-xs leading-relaxed text-ink-2">
                  <span aria-hidden className="mr-1.5 text-warning">
                    △
                  </span>
                  {line}
                </li>
              ))}
            </ul>
          </Card>
        ) : null}

        <Card>
          <CardHead title="Agent trace" hint="Expand a step to see what that agent passed on." />
          <AgentTrace steps={decision.agent_trace} />
        </Card>
      </div>
    </div>
  );
}
