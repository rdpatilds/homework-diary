export type Urgency = "late" | "today" | "soon" | "later";

export type Countdown = {
  value: string;
  unit: string;
  /** Compact form for a chip, such as "2d". */
  short: string;
  urgency: Urgency;
};

/** The reference grades urgency into four tiers and colours every dot, chip and
 * numeral from them. One mapping so nothing drifts. */
export type Tier = "crit" | "high" | "med" | "low";

export function tierOf(state: "open" | "missed" | "done", urgency: Urgency): Tier {
  if (state === "done") return "low";
  if (state === "missed" || urgency === "today") return "crit";
  return urgency === "soon" ? "high" : "med";
}

const HOUR = 3600_000;
const DAY = 24 * HOUR;

/** Everything about a deadline is derived from one number: the gap. Total over
 * deadlines either side of now, so overdue work needs no second function. */
export function countdown(dueAt: string, asOf: Date): Countdown {
  const gap = new Date(dueAt).getTime() - asOf.getTime();
  const size = Math.abs(gap);
  const urgency: Urgency =
    gap < 0 ? "late" : size < DAY ? "today" : size < 3 * DAY ? "soon" : "later";

  if (size < HOUR) {
    const minutes = Math.max(1, Math.round(size / 60_000));
    const unit = minutes === 1 ? "min" : "mins";
    return { value: String(minutes), unit, short: `${minutes}m`, urgency };
  }
  if (size < DAY) {
    const hours = Math.round(size / HOUR);
    const unit = hours === 1 ? "hour" : "hours";
    return { value: String(hours), unit, short: `${hours}h`, urgency };
  }
  const days = Math.floor(size / DAY);
  const unit = days === 1 ? "day" : "days";
  return { value: String(days), unit, short: `${days}d`, urgency };
}

const WHEN = new Intl.DateTimeFormat(undefined, {
  weekday: "short",
  day: "numeric",
  month: "short",
  hour: "numeric",
  minute: "2-digit",
});

export function dueLabel(dueAt: string): string {
  return WHEN.format(new Date(dueAt));
}

/** `datetime-local` gives wall time with no zone. The server stores UTC, so
 * convert once, here, at the edge. */
export function localInputToIso(value: string): string {
  return new Date(value).toISOString();
}
