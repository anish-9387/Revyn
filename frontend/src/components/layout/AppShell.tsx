"use client";

import { createContext, useContext, useMemo } from "react";

import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { ErrorNote } from "@/components/ui/State";
import { api } from "@/lib/api";
import { useAction, useResource } from "@/lib/hooks";
import type { Overview, Policy } from "@/lib/types";

interface Live {
  overview: Overview | null;
  policy: Policy | null;
  refresh: () => Promise<void>;
}

const LiveContext = createContext<Live>({ overview: null, policy: null, refresh: async () => {} });

/** Pages read the shared overview instead of each re-fetching it. */
export const useLive = () => useContext(LiveContext);

export function AppShell({ children }: { children: React.ReactNode }) {
  const overview = useResource(api.overview, { intervalMs: 8000 });
  const policy = useResource(api.policy, { intervalMs: 20000 });
  const { pending, error, run } = useAction();

  const refresh = useMemo(
    () => async () => {
      await Promise.all([overview.refresh(), policy.refresh()]);
    },
    [overview.refresh, policy.refresh],
  );

  const value = useMemo<Live>(
    () => ({ overview: overview.data, policy: policy.data, refresh }),
    [overview.data, policy.data, refresh],
  );

  const cycle = () => void run("cycle", async () => (await api.runCycle(), refresh()));
  const killSwitch = (enable: boolean) =>
    void run("kill", async () => (await api.killSwitch(enable), refresh()));

  return (
    <LiveContext.Provider value={value}>
      <div className="lg:flex">
        <Sidebar approvals={overview.data?.pending_approvals ?? 0} />
        <div className="min-w-0 flex-1 lg:h-dvh lg:overflow-y-auto">
          <TopBar
            overview={overview.data}
            automationEnabled={policy.data ? policy.data.automation_enabled && !policy.data.paused : true}
            updatedAt={overview.updatedAt}
            busy={pending}
            onCycle={cycle}
            onKillSwitch={killSwitch}
          />
          <main className="mx-auto max-w-[1500px] space-y-5 px-4 py-5">
            {overview.error ? (
              <ErrorNote
                message={`Backend unreachable — ${overview.error}. Start it with: uvicorn app.main:app --reload`}
                onRetry={() => void refresh()}
              />
            ) : null}
            {error ? <ErrorNote message={error} /> : null}
            {children}
          </main>
        </div>
      </div>
    </LiveContext.Provider>
  );
}
