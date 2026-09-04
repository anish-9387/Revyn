"use client";

import Link from "next/link";
import { use } from "react";

import { DecisionPanel } from "@/components/domain/DecisionPanel";
import { PageHead } from "@/components/ui/Card";
import { Resource } from "@/components/ui/State";
import { api } from "@/lib/api";
import { dateTime } from "@/lib/format";
import { useResource } from "@/lib/hooks";
import { actionLabel } from "@/lib/labels";
import { href } from "@/lib/routes";

export default function DecisionPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const explained = useResource(() => api.decision(id), { deps: [id] });

  return (
    <Resource {...explained} empty="Decision not found.">
      {({ decision, policy_explanations }) => (
        <>
          <PageHead
            title={`Decision — ${actionLabel(decision.chosen_action)}`}
            hint={`Recorded ${dateTime(decision.created_at)} — every option that was priced, and why this one won.`}
            actions={
              decision.journey_id ? (
                <Link
                  href={href(`/journeys/${decision.journey_id}`)}
                  className="text-xs text-series-1 underline underline-offset-2"
                >
                  Open journey
                </Link>
              ) : null
            }
          />
          <DecisionPanel decision={decision} explanations={policy_explanations} />
        </>
      )}
    </Resource>
  );
}
