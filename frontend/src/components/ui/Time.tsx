"use client";

import { useEffect, useState } from "react";

import { dateTime, relativeTime } from "@/lib/format";

export function useNow(intervalMs = 30000): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
  return now;
}

export function RelativeTime({ iso, className }: { iso: string | null; className?: string }) {
  const now = useNow(30000);
  const [mounted, setMounted] = useState(false);
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => setMounted(true), []);
  if (!iso) return <span className={className}>-</span>;
  if (!mounted) return <span className={className} suppressHydrationWarning>{relativeTime(iso, now)}</span>;
  return <span className={className} suppressHydrationWarning>{relativeTime(iso, now)}</span>;
}

export function DateTime({ iso, className }: { iso: string | null; className?: string }) {
  const [mounted, setMounted] = useState(false);
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => setMounted(true), []);
  if (!mounted) return <span className={className} suppressHydrationWarning>-</span>;
  return <span className={className} suppressHydrationWarning>{dateTime(iso)}</span>;
}
