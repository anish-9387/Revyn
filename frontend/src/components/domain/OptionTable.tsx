import { Badge } from "@/components/ui/Badge";
import { DataTable } from "@/components/ui/DataTable";
import { inr, pct } from "@/lib/format";
import { actionLabel, VERDICT_TONE } from "@/lib/labels";
import type { ActionOption } from "@/lib/types";

/** The full option set, priced. Showing the losers is what makes the winner defensible. */
export function OptionTable({ options, chosen }: { options: ActionOption[]; chosen: string }) {
  const ranked = [...options].sort((left, right) => right.expected_value_paise - left.expected_value_paise);
  return (
    <DataTable
      dense
      rows={ranked}
      rowKey={(row) => row.action}
      empty="No options were priced for this event."
      columns={[
        {
          key: "action",
          head: "Option",
          cell: (row) => (
            <span className={row.action === chosen ? "font-medium text-ink" : "text-ink-2"}>
              {row.action === chosen ? "→ " : ""}
              {actionLabel(row.action)}
            </span>
          ),
        },
        { key: "p", head: "P(recover)", align: "right", cell: (row) => pct(row.probability, 1) },
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
          key: "cost",
          head: "Cost",
          align: "right",
          cell: (row) => inr(row.intervention_cost_paise + row.discount_cost_paise),
        },
        { key: "friction", head: "Friction charge", align: "right", cell: (row) => inr(row.friction_cost_paise) },
        {
          key: "ev",
          head: "Expected value",
          align: "right",
          cell: (row) => (
            <span className={row.expected_value_paise > 0 ? "text-ink" : "text-muted"}>
              {inr(row.expected_value_paise)}
            </span>
          ),
        },
        {
          key: "verdict",
          head: "Guardrail",
          cell: (row) => (
            <span title={row.blocked_reasons.join(", ")}>
              <Badge tone={VERDICT_TONE[row.verdict]}>{row.verdict.replace(/_/g, " ")}</Badge>
            </span>
          ),
        },
      ]}
    />
  );
}
