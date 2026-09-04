"use client";

const INPUT =
  "hairline rounded-lg bg-raised px-3 text-[13px] text-ink transition-colors placeholder:text-muted hover:border-hairline-strong focus:border-series-1";

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
      <span className="mt-1.5 flex items-center gap-2">
        <input
          type="number"
          value={value}
          min={min}
          max={max}
          step={step}
          onChange={(event) => onChange(Number(event.target.value))}
          className={`${INPUT} num h-10 w-full sm:h-9`}
        />
        {suffix ? <span className="text-xs whitespace-nowrap text-muted">{suffix}</span> : null}
      </span>
      {hint ? <span className="mt-1.5 block text-[11px] leading-relaxed text-muted">{hint}</span> : null}
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
        className={`press mt-0.5 flex h-6 w-11 shrink-0 items-center rounded-full border transition-colors duration-200 disabled:opacity-45 ${
          checked ? "border-series-1 bg-series-1" : "border-hairline bg-grid"
        }`}
      >
        <span
          className="block h-4 w-4 rounded-full bg-white shadow-soft transition-transform duration-300"
          style={{
            transform: `translateX(${checked ? 22 : 3}px)`,
            transitionTimingFunction: "var(--ease-spring)",
          }}
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
      <span className="whitespace-nowrap text-muted">{label}</span>
      <span className="relative inline-flex items-center">
        <select
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className={`${INPUT} h-9 cursor-pointer appearance-none pr-7`}
        >
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <span aria-hidden className="pointer-events-none absolute right-2.5 text-[8px] text-muted">
          ▼
        </span>
      </span>
    </label>
  );
}
