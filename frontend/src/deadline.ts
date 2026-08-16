export type Urgency = "late" | "today" | "soon" | "later";

export type Countdown = {
  /** Large numeral shown on the spine. */
  value: string;
  /** Unit beneath it. */
  unit: string;
  urgency: Urgency;
};

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
    return { value: String(minutes), unit: minutes === 1 ? "min" : "mins", urgency };
  }
  if (size < DAY) {
    const hours = Math.round(size / HOUR);
    return { value: String(hours), unit: hours === 1 ? "hour" : "hours", urgency };
  }
  const days = Math.floor(size / DAY);
  return { value: String(days), unit: days === 1 ? "day" : "days", urgency };
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
