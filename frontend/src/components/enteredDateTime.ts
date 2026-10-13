// A date and time typed into a date-and-time box (DateInput withTime) is India's time, whatever the browser's own zone
// (the entered-time fix, October 2026). The page sends it as the same moment in UTC with its zone, the API stores UTC,
// and the page shows what comes back in India's time (dateTimeDisplay.ts). The offer page once sent the typed time with
// no zone: the API stored it as UTC and the page showed it 5 hours 30 minutes late (a market rate typed at 10:30 shown
// at 4:00 pm). The API now refuses a time with no zone. India keeps no daylight saving, so its offset is always +05:30.
// enteredDateTime.test.ts fails when a page with a date-and-time box does not send it through here.

import { readApiDateTime } from "./dateTimeDisplay";

const INDIA_UTC_OFFSET = "+05:30";
const INDIA_UTC_OFFSET_MS = (5 * 60 + 30) * 60 * 1000;
/** What a date-and-time box holds: "2026-10-12T10:30", with seconds only when a page asks for them. */
const DATE_TIME_BOX_VALUE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,3})?)?$/;

/** A date-and-time box's value, India's time, as the UTC moment the API takes: "2026-10-12T10:30" becomes
 * "2026-10-12T05:00:00.000Z". Null when the box is empty or holds anything else. */
export function enteredIndiaTimeToUtc(value: string): string | null {
  const trimmed = value.trim();
  if (!DATE_TIME_BOX_VALUE.test(trimmed)) return null;
  const moment = new Date(`${trimmed}${INDIA_UTC_OFFSET}`);
  return Number.isNaN(moment.getTime()) ? null : moment.toISOString();
}

/** A time from the API (UTC; one with no zone is UTC) as a date-and-time box's value in India's time, for a form that
 * starts from a saved time: "2026-10-12T05:00:00" becomes "2026-10-12T10:30". Empty when there is none. */
export function apiDateTimeToIndiaInput(value: string | null | undefined): string {
  const moment = readApiDateTime(value);
  return moment ? new Date(moment.getTime() + INDIA_UTC_OFFSET_MS).toISOString().slice(0, 16) : "";
}

/** Now, in India's time, as a date-and-time box's value. */
export function nowAsIndiaInput(now: Date = new Date()): string {
  return apiDateTimeToIndiaInput(now.toISOString());
}
