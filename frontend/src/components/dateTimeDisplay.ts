// How a business date and time is shown: in India's time, whatever the browser's zone (AGENTS.md, "Date/time display
// rule"). The CRM tables store UTC without a zone, so the API sends "2026-10-04T10:00:00" for 15:30 in India; a time
// with no zone is therefore read as UTC. Four CRM pages once read it as the browser's own time and showed it 5 hours
// 30 minutes early (TB-1 finding TB1-604). Moved here unchanged from pages/resource-requirements/pageSession.ts, which
// re-exports it. A time a person types goes the other way, through enteredDateTime.ts.

const APP_DISPLAY_TIME_ZONE = "Asia/Kolkata";

/** A time from the API as a moment; one with no zone is UTC. Null when there is none or it cannot be read. */
export function readApiDateTime(value: string | null | undefined): Date | null {
  const trimmed = value?.trim();
  if (!trimmed) return null;
  const normalized = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(trimmed) ? trimmed : `${trimmed}Z`;
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "-";
  const date = readApiDateTime(value);
  if (!date) return value;
  return date.toLocaleString("en-IN", {
    timeZone: APP_DISPLAY_TIME_ZONE,
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });
}
