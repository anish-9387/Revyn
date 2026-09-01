"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface Resource<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  refresh: () => Promise<void>;
  updatedAt: number | null;
}

interface State<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  updatedAt: number | null;
}

const INITIAL = { data: null, error: null, loading: true, updatedAt: null };

const sameDeps = (a: unknown[], b: unknown[]) => a.length === b.length && a.every((v, i) => v === b[i]);

/**
 * Fetches once and then polls. The dashboard tracks a live recovery loop, so stale data is
 * worse than an extra request; `intervalMs` of 0 disables polling.
 */
export function useResource<T>(
  loader: () => Promise<T>,
  options: { intervalMs?: number; deps?: unknown[] } = {},
): Resource<T> {
  const { intervalMs = 0, deps = [] } = options;
  const [state, setState] = useState<State<T>>(INITIAL);
  const [lastDeps, setLastDeps] = useState(deps);
  const loaderRef = useRef(loader);
  const mounted = useRef(true);

  // Adjusted during render, not from an effect: new dependencies mean the data on screen belongs
  // to a different question, so it is dropped rather than shown under the new one.
  if (!sameDeps(lastDeps, deps)) {
    setLastDeps(deps);
    setState(INITIAL);
  }

  const load = useCallback(async () => {
    try {
      const next = await loaderRef.current();
      if (mounted.current) setState({ data: next, error: null, loading: false, updatedAt: Date.now() });
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : "Request failed";
      if (mounted.current) setState((prev) => ({ ...prev, error: message, loading: false }));
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    loaderRef.current = loader;
    void load();
    const timer = intervalMs ? setInterval(() => void load(), intervalMs) : null;
    return () => {
      mounted.current = false;
      if (timer) clearInterval(timer);
    };
    // The caller declares what the loader closes over; `loader` itself is a fresh closure each render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [load, intervalMs, ...deps]);

  return { ...state, refresh: load };
}

/** Tracks an async mutation so buttons can disable and surface failures. */
export function useAction() {
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async (key: string, task: () => Promise<unknown>) => {
    setPending(key);
    setError(null);
    try {
      await task();
      return true;
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Action failed");
      return false;
    } finally {
      setPending(null);
    }
  }, []);

  const clearError = useCallback(() => setError(null), []);

  return { pending, error, run, clearError };
}
