const RUPEE = "\u20B9";

function formatIndian(n: number): string {
  const s = Math.trunc(n).toString();
  if (s.length <= 3) return s;
  const last3 = s.slice(-3);
  const rest = s.slice(0, -3);
  const parts: string[] = [];
  for (let i = rest.length; i > 0; i -= 2) {
    const start = Math.max(0, i - 2);
    parts.unshift(rest.slice(start, i));
  }
  return [...parts, last3].join(",");
}

export function inr(paise: number, options?: { precise?: boolean }): string {
  const rupees = Math.abs(paise) / 100;
  const sign = paise < 0 ? "-" : "";
  if (options?.precise) return `${sign}${RUPEE}${formatIndian(rupees)}`;
  if (rupees >= 1_00_00_000) return `${sign}${RUPEE}${(rupees / 1_00_00_000).toFixed(2)}Cr`;
  if (rupees >= 1_00_000) return `${sign}${RUPEE}${(rupees / 1_00_000).toFixed(2)}L`;
  if (rupees >= 1_000) return `${sign}${RUPEE}${(rupees / 1_000).toFixed(1)}K`;
  return `${sign}${RUPEE}${formatIndian(rupees)}`;
}

export function pct(value: number, digits = 0): string {
  return `${(value * 100).toFixed(digits)}%`;
}

export function signed(paise: number): string {
  return `${paise >= 0 ? "+" : ""}${inr(paise)}`;
}

export function compact(value: number): string {
  return formatIndian(value);
}

export function relativeTime(iso: string | null, nowMs?: number): string {
  if (!iso) return "-";
  const then = new Date(iso).getTime();
  const base = nowMs ?? Date.now();
  const seconds = Math.round((base - then) / 1000);
  const future = seconds < 0;
  const abs = Math.abs(seconds);
  if (abs < 60) return future ? "in moments" : "just now";
  const [value, unit] =
    abs < 3600
      ? [Math.round(abs / 60), "m"]
      : abs < 86400
        ? [Math.round(abs / 3600), "h"]
        : [Math.round(abs / 86400), "d"];
  return future ? `in ${value}${unit}` : `${value}${unit} ago`;
}

const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function clockTime(iso: string | null): string {
  if (!iso) return "-";
  const d = new Date(iso);
  const h = d.getHours().toString().padStart(2, "0");
  const m = d.getMinutes().toString().padStart(2, "0");
  return `${h}:${m}`;
}

export function dateTime(iso: string | null): string {
  if (!iso) return "-";
  const d = new Date(iso);
  const day = d.getDate().toString().padStart(2, "0");
  const mon = months[d.getMonth()];
  const h = d.getHours().toString().padStart(2, "0");
  const m = d.getMinutes().toString().padStart(2, "0");
  return `${day} ${mon}, ${h}:${m}`;
}

export function titleCase(value: string): string {
  return value.replace(/[_-]+/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function hourLabel(hour: number): string {
  const suffix = hour < 12 ? "AM" : "PM";
  const display = hour % 12 === 0 ? 12 : hour % 12;
  return `${display}${suffix}`;
}

export function plural(count: number, unit: string, many = `${unit}s`): string {
  return `${compact(count)} ${count === 1 ? unit : many}`;
}
