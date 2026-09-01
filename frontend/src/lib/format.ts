/** Display helpers. All monetary inputs are integer paise. */

const RUPEE = "\u20B9";

export function inr(paise: number, options?: { precise?: boolean }): string {
  const rupees = Math.abs(paise) / 100;
  const sign = paise < 0 ? "-" : "";
  if (options?.precise) {
    return `${sign}${RUPEE}${rupees.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
  }
  if (rupees >= 1_00_00_000) return `${sign}${RUPEE}${(rupees / 1_00_00_000).toFixed(2)}Cr`;
  if (rupees >= 1_00_000) return `${sign}${RUPEE}${(rupees / 1_00_000).toFixed(2)}L`;
  if (rupees >= 1_000) return `${sign}${RUPEE}${(rupees / 1_000).toFixed(1)}K`;
  return `${sign}${RUPEE}${rupees.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

export function pct(value: number, digits = 0): string {
  return `${(value * 100).toFixed(digits)}%`;
}

export function signed(paise: number): string {
  return `${paise >= 0 ? "+" : ""}${inr(paise)}`;
}

export function compact(value: number): string {
  return value.toLocaleString("en-IN");
}

export function relativeTime(iso: string | null): string {
  if (!iso) return "-";
  const then = new Date(iso).getTime();
  const seconds = Math.round((Date.now() - then) / 1000);
  const future = seconds < 0;
  const abs = Math.abs(seconds);
  const [value, unit] =
    abs < 60
      ? [abs, "s"]
      : abs < 3600
        ? [Math.round(abs / 60), "m"]
        : abs < 86400
          ? [Math.round(abs / 3600), "h"]
          : [Math.round(abs / 86400), "d"];
  return future ? `in ${value}${unit}` : `${value}${unit} ago`;
}

export function clockTime(iso: string | null): string {
  if (!iso) return "-";
  return new Date(iso).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
}

export function dateTime(iso: string | null): string {
  if (!iso) return "-";
  return new Date(iso).toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function titleCase(value: string): string {
  return value
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

export function hourLabel(hour: number): string {
  const suffix = hour < 12 ? "AM" : "PM";
  const display = hour % 12 === 0 ? 12 : hour % 12;
  return `${display}${suffix}`;
}
