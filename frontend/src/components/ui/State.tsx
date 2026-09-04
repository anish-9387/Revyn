export function Skeleton({ className = "h-4 w-full" }: { className?: string }) {
  return <span aria-hidden className={`skeleton block rounded-lg ${className}`} />;
}

export function SkeletonBlock({ rows = 4, label = "Loading", panel = false }: { rows?: number; label?: string; panel?: boolean }) {
  return (
    <div className={`space-y-2.5 ${panel ? "panel panel-sheen rounded-card p-4 sm:p-5" : "py-1"}`} role="status" aria-label={label}>
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} className={`h-4 ${i === 0 ? "w-2/5" : i % 3 === 0 ? "w-4/5" : "w-full"} ${i === 1 ? "h-6" : ""}`} />
      ))}
    </div>
  );
}

export function ErrorNote({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="animate-pop flex flex-wrap items-center gap-2 rounded-2xl border border-critical/25 bg-critical/10 px-3.5 py-3 text-[13px] font-medium text-critical">
      <span aria-hidden className="grid h-6 w-6 place-items-center rounded-full bg-critical/15 text-xs">!</span>
      <span className="min-w-0 flex-1 leading-relaxed">{message}</span>
      {onRetry ? <button onClick={onRetry} className="press rounded-full border border-critical/25 bg-surface px-3 py-1 text-xs font-semibold hover:bg-raised">Retry</button> : null}
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="animate-fade rounded-2xl border border-dashed border-axis/70 bg-raised/40 px-5 py-12 text-center backdrop-blur-sm">
      <div aria-hidden className="mx-auto grid h-10 w-10 place-items-center rounded-xl bg-surface border border-hairline text-muted">◌</div>
      <p className="mt-3 text-sm font-semibold text-ink">{title}</p>
      {hint ? <p className="mx-auto mt-1.5 max-w-sm text-xs leading-relaxed text-muted">{hint}</p> : null}
    </div>
  );
}

export function Resource<T>({
  data, error, loading, refresh, empty, children,
}: { data: T | null; error: string | null; loading: boolean; refresh?: () => void; empty?: string; children: (value: T) => React.ReactNode }) {
  if (error && !data) return <ErrorNote message={error} onRetry={refresh} />;
  if (loading && !data) return <SkeletonBlock panel />;
  if (!data) return <EmptyState title={empty ?? "Nothing here yet"} />;
  return <>{children(data)}</>;
}
