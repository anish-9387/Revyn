"use client";

import { createContext, useCallback, useContext, useMemo, useState } from "react";

import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { ErrorNote } from "@/components/ui/State";
import { api } from "@/lib/api";
import { useAction, useResource } from "@/lib/hooks";
import type { Overview, Policy } from "@/lib/types";

interface Live { overview: Overview | null; policy: Policy | null; refresh: () => Promise<void>; }

const LiveContext = createContext<Live>({ overview: null, policy: null, refresh: async () => {} });

export const useLive = () => useContext(LiveContext);

export function AppShell({ children }: { children: React.ReactNode }) {
  const overview = useResource(api.overview, { intervalMs: 8000 });
  const policy = useResource(api.policy, { intervalMs: 20000 });
  const { pending, error, run } = useAction();
  const [navOpen, setNavOpen] = useState(false);
  const { refresh: refreshOverview } = overview;
  const { refresh: refreshPolicy } = policy;
  const refresh = useCallback(async () => { await Promise.all([refreshOverview(), refreshPolicy()]); }, [refreshOverview, refreshPolicy]);
  const value = useMemo<Live>(() => ({ overview: overview.data, policy: policy.data, refresh }), [overview.data, policy.data, refresh]);
  const closeNav = useCallback(() => setNavOpen(false), []);
  const cycle = () => void run("cycle", async () => (await api.runCycle(), refresh()));
  const killSwitch = (enable: boolean) => void run("kill", async () => (await api.killSwitch(enable), refresh()));
  return (
    <LiveContext.Provider value={value}>
      <div className="relative z-10 lg:flex">
        <Sidebar approvals={overview.data?.pending_approvals ?? 0} open={navOpen} onClose={closeNav} />
        <div className="min-w-0 flex-1 lg:h-dvh lg:overflow-y-auto lg:overflow-x-hidden">
          <TopBar overview={overview.data} automationEnabled={policy.data ? policy.data.automation_enabled && !policy.data.paused : true} busy={pending} onCycle={cycle} onKillSwitch={killSwitch} onOpenNav={() => setNavOpen(true)} />
          <main className="stagger mx-auto max-w-[1560px] space-y-4 px-4 py-4 sm:space-y-5 sm:px-5 sm:py-5 lg:px-7 lg:py-6">
            {overview.error ? <ErrorNote message="Backend unreachable. Make sure the API server is running." onRetry={() => void refresh()} /> : null}
            {error ? <ErrorNote message={error} /> : null}
            {children}
          </main>
          <footer className="border-t border-hairline/60 px-4 py-4 text-center text-[11px] text-muted sm:px-5 lg:px-7" suppressHydrationWarning>
            <span className="inline-flex items-center gap-2">© 2026 Revyn · Revenue recovery, supervised · <span className="h-1.5 w-1.5 rounded-full bg-good animate-pulse" aria-hidden /> All systems nominal</span>
          </footer>
        </div>
      </div>
    </LiveContext.Provider>
  );
}
