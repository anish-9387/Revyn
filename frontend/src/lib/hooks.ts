"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface Resource<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  refresh: () => Promise<void>;
  updatedAt: number | null;
}

/**
 * Fetches once and then polls. The dashboard tracks a live recovery loop, so stale data is
 * worse than an extra request; `intervalMs` of 0 disables polling.
 */
export function useResource<T>(
  loader: () => Promise<T>,
  options: { intervalMs?: number; deps?: unknown[] } = {},
): Resource<T> {
  const { intervalMs = 0, deps = [] } = options;
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [updatedAt, setUpdatedAt] = useState<number | null>(null);
  const loaderRef = useRef(loader);
  loaderRef.current = loader;
  const mounted = useRef(true);

  const refresh = useCallback(async () => {
    try {
      const next = await loaderRef.current();
      if (!mounted.current) return;
      setData(next);
      setError(null);
      setUpdatedAt(Date.now());
    } catch (cause) {
      if (!mounted.current) return;
      setError(cause instanceof Error ? cause.message : "Request failed");
    } finally {
      if (mounted.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    setLoading(true);
    void refresh();
    if (!intervalMs) return () => void (mounted.current = false);
    const timer = setInterval(() => void refresh(), intervalMs);
    return () => {
      mounted.current = false;
      clearInterval(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refresh, intervalMs, ...deps]);

  return { data, error, loading, refresh, updatedAt };
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

  return { pending, error, run, clearError: () => setError(null) };
}
