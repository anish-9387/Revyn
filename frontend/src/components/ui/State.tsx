export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 py-10 text-xs text-muted" role="status">
      <span className="h-3 w-3 animate-spin rounded-full border-2 border-axis border-t-series-1" />
      {label}
    </div>
  );
}

export function ErrorNote({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="rounded-lg border border-critical/40 bg-critical/10 px-3 py-2 text-xs text-critical">
      <span aria-hidden>✕ </span>
      {message}
      {onRetry ? (
        <button onClick={onRetry} className="ml-2 underline underline-offset-2">
          retry
        </button>
      ) : null}
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="rounded-lg border border-dashed border-axis px-4 py-10 text-center">
      <p className="text-sm text-ink-2">{title}</p>
      {hint ? <p className="mt-1 text-xs text-muted">{hint}</p> : null}
    </div>
  );
}

/** Wraps the common load / fail / empty branches so pages stay about their content. */
export function Resource<T>({
  data,
  error,
  loading,
  refresh,
  empty,
  children,
}: {
  data: T | null;
  error: string | null;
  loading: boolean;
  refresh?: () => void;
  empty?: string;
  children: (value: T) => React.ReactNode;
}) {
  if (error && !data) return <ErrorNote message={error} onRetry={refresh} />;
  if (loading && !data) return <Spinner />;
  if (!data) return <EmptyState title={empty ?? "Nothing here yet"} />;
  return <>{children(data)}</>;
}
