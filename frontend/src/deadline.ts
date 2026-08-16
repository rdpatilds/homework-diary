export type Urgency = "today" | "soon" | "later";

export type Countdown = {
  /** Large numeral shown on the spine. */
  value: string;
  /** Unit beneath it. */
  unit: string;
  urgency: Urgency;
};

const HOUR = 3600_000;
const DAY = 24 * HOUR;

/** Everything about a deadline is derived from one number: the gap. No stored
 * flags to keep in sync. */
export function countdown(dueAt: string, asOf: Date): Countdown {
  const gap = new Date(dueAt).getTime() - asOf.getTime();
  if (gap < HOUR) {
    const minutes = Math.max(1, Math.round(gap / 60_000));
    return { value: String(minutes), unit: minutes === 1 ? "min" : "mins", urgency: "today" };
  }
  if (gap < DAY) {
    const hours = Math.round(gap / HOUR);
    return { value: String(hours), unit: hours === 1 ? "hour" : "hours", urgency: "today" };
  }
  const days = Math.floor(gap / DAY);
  return {
    value: String(days),
    unit: days === 1 ? "day" : "days",
    urgency: days <= 2 ? "soon" : "later",
  };
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
