"use client";

export function NumberField({
  label,
  hint,
  value,
  onChange,
  min = 0,
  max,
  step = 1,
  suffix,
}: {
  label: string;
  hint?: string;
  value: number;
  onChange: (next: number) => void;
  min?: number;
  max?: number;
  step?: number;
  suffix?: string;
}) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-ink-2">{label}</span>
      <span className="mt-1 flex items-center gap-2">
        <input
          type="number"
          value={value}
          min={min}
          max={max}
          step={step}
          onChange={(event) => onChange(Number(event.target.value))}
          className="hairline w-full rounded-md bg-raised px-2.5 py-1.5 text-sm tabular-nums text-ink"
        />
        {suffix ? <span className="text-xs whitespace-nowrap text-muted">{suffix}</span> : null}
      </span>
      {hint ? <span className="mt-1 block text-[11px] leading-relaxed text-muted">{hint}</span> : null}
    </label>
  );
}

export function Toggle({
  label,
  hint,
  checked,
  onChange,
  disabled = false,
}: {
  label: string;
  hint?: string;
  checked: boolean;
  onChange: (next: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <label className="flex items-start justify-between gap-4">
      <span>
        <span className="text-xs font-medium text-ink-2">{label}</span>
        {hint ? <span className="mt-0.5 block text-[11px] leading-relaxed text-muted">{hint}</span> : null}
      </span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={`mt-0.5 h-5 w-9 shrink-0 rounded-full border transition disabled:opacity-45 ${
          checked ? "border-series-1 bg-series-1" : "border-hairline bg-grid"
        }`}
      >
        <span
          className={`block h-3.5 w-3.5 rounded-full bg-white transition-transform ${
            checked ? "translate-x-4" : "translate-x-0.5"
          }`}
        />
      </button>
    </label>
  );
}

export function Select({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (next: string) => void;
}) {
  return (
    <label className="flex items-center gap-2 text-xs">
      <span className="text-muted">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="hairline rounded-md bg-raised px-2 py-1 text-xs text-ink"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
