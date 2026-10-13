// PBL's holiday calendar (HOL-1, design sections 5.1 and 6): the Holiday Calendar page's rules, kept apart from the
// component so they are tested without a browser. The form's checks are the server's, so a year it would refuse is
// refused beside Save first; the server still decides. docs/agent/slices/hol-1-holiday-calendar.md.

import { type QueryUpdate, type QueryView, formatDay, initialQueryView, queryViewKeeping } from "../equipment/certificatesState";

export type CalendarState = { state_code: string; state_label: string; state_kind_code: string };

export type CalendarHoliday = {
  holiday_public_id: string;
  holiday_date: string;
  holiday_kind_code: string;
  holiday_kind_label: string;
  holiday_name: string;
  applies_to_code: string;
  states: { state_code: string; state_label: string }[];
};

export type CalendarYearSummary = {
  calendar_year: number;
  year_public_id: string | null;
  year_version: number | null;
  is_complete: boolean;
  complete_marked_by_display_name: string | null;
  complete_marked_at: string | null;
  holiday_count: number;
  updated_by_display_name: string | null;
  updated_at: string | null;
};

export type CalendarYears = { today: string; years: CalendarYearSummary[] };

export type CalendarYear = CalendarYearSummary & { today: string; holidays: CalendarHoliday[] };

export type CalendarYearAction = { year: CalendarYear; event: unknown };

/** What the page shows at once: the years to pick from, the year picked, and the states a holiday may name. */
export type CalendarAnswer = { years: CalendarYears; year: CalendarYear; states: CalendarState[] };

export const FIRST_YEAR = 2000;
export const LAST_YEAR = 2100;
export const NAME_MAX_LENGTH = 255;

export const ALL_INDIA = "ALL_INDIA";
export const STATES = "STATES";

// The words of the states' National and Festival Holidays Acts. The kind does not decide where a holiday applies: a
// state may count its own day among its national holidays, as Maharashtra does 1 May (design 1.2, point 2).
export const KIND_OPTIONS = [
  { code: "NATIONAL", label: "National holiday" },
  { code: "FESTIVAL", label: "Festival holiday" },
];

// --- The year picked --------------------------------------------------------------------------------------------

/** The year an address asks for (`?year=2027`), or none - the page then shows the year `yearToShow` gives. */
export function yearFromSearch(search: string): number | null {
  const value = new URLSearchParams(search).get("year");
  if (!value || !/^\d{4}$/.test(value)) return null;
  const year = Number(value);
  return year >= FIRST_YEAR && year <= LAST_YEAR ? year : null;
}

/**
 * The year the page reads: the one asked for, else India's current year - or, outside 2000 to 2100, the nearest year
 * the calendar keeps, so the page never asks the server for a year it refuses and stays usable (independent review,
 * HOL1-R2-001).
 */
export function yearToShow(asked: number | null, today: string): number {
  if (asked !== null) return asked;
  return Math.min(LAST_YEAR, Math.max(FIRST_YEAR, Number(today.slice(0, 4))));
}

/** "Not set up", "Being entered (version 2)" or "Complete (version 3)". */
export function yearStateText(year: Pick<CalendarYearSummary, "year_version" | "is_complete">): string {
  if (year.year_version === null) return "Not set up";
  return year.is_complete ? `Complete (version ${year.year_version})` : `Being entered (version ${year.year_version})`;
}

/** Why a year typed to start cannot be opened, or null. */
export function startYearProblem(text: string): string | null {
  const value = text.trim();
  if (!/^\d{4}$/.test(value)) return "Type a year of four digits.";
  const year = Number(value);
  if (year < FIRST_YEAR || year > LAST_YEAR) return `Choose a year from ${FIRST_YEAR} to ${LAST_YEAR}.`;
  return null;
}

/** Where a holiday applies, in words: "All of India", or the states named. */
export function appliesText(holiday: Pick<CalendarHoliday, "applies_to_code" | "states">): string {
  return holiday.applies_to_code === ALL_INDIA ? "All of India" : holiday.states.map((state) => state.state_label).join(", ");
}

// --- The form -----------------------------------------------------------------------------------------------------

/** One row of the form. `key` identifies the row on screen only; it is never sent. */
export type HolidayRow = { key: string; date: string; kind: string; name: string; appliesTo: string; states: string[] };

export type YearForm = { complete: boolean; rows: HolidayRow[] };

export function formFromYear(year: CalendarYear): YearForm {
  return {
    complete: year.is_complete,
    rows: year.holidays.map((holiday) => ({
      key: holiday.holiday_public_id,
      date: holiday.holiday_date,
      kind: holiday.holiday_kind_code,
      name: holiday.holiday_name,
      appliesTo: holiday.applies_to_code,
      states: holiday.states.map((state) => state.state_code),
    })),
  };
}

/** A new, empty row: a festival holiday for all of India, the most common. The key is passed in, so this stays pure. */
export function addRow(form: YearForm, key: string): YearForm {
  return { ...form, rows: [...form.rows, { key, date: "", kind: "FESTIVAL", name: "", appliesTo: ALL_INDIA, states: [] }] };
}

export function removeRow(form: YearForm, key: string): YearForm {
  return { ...form, rows: form.rows.filter((row) => row.key !== key) };
}

export function updateRow(form: YearForm, key: string, change: Partial<Omit<HolidayRow, "key">>): YearForm {
  return {
    ...form,
    rows: form.rows.map((row) => {
      if (row.key !== key) return row;
      const next = { ...row, ...change };
      // All of India names no states: choosing it clears them, as the server refuses both together.
      return next.appliesTo === ALL_INDIA ? { ...next, states: [] } : next;
    }),
  };
}

export function toggleState(form: YearForm, key: string, stateCode: string): YearForm {
  return {
    ...form,
    rows: form.rows.map((row) =>
      row.key !== key
        ? row
        : { ...row, states: row.states.includes(stateCode) ? row.states.filter((code) => code !== stateCode) : [...row.states, stateCode] },
    ),
  };
}

function isDate(value: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(value);
}

/**
 * Why the year cannot be saved, in words, or null: the server's checks (design section 5.1), each naming the date.
 * `stateLabels` are the states a holiday may name, by code.
 */
export function yearFormProblem(form: YearForm, calendarYear: number, stateLabels: Record<string, string>): string | null {
  for (const row of form.rows) {
    if (!isDate(row.date)) return "Enter a date for every holiday, or remove the empty row.";
  }
  const rows = [...form.rows].sort((a, b) => a.date.localeCompare(b.date));
  for (const row of rows) {
    const day = formatDay(row.date);
    if (Number(row.date.slice(0, 4)) !== calendarYear) return `${day} is not in ${calendarYear}. Enter only the holidays of ${calendarYear} here.`;
    if (!KIND_OPTIONS.some((option) => option.code === row.kind)) return `Choose whether the holiday on ${day} is a national or a festival holiday.`;
    if (!row.name.trim()) return `Give the holiday on ${day} a name.`;
    if (row.name.length > NAME_MAX_LENGTH) return `The name of the holiday on ${day} is longer than ${NAME_MAX_LENGTH} characters.`;
    if (row.appliesTo === STATES && row.states.length === 0) return `Choose at least one state for the holiday on ${day}, or make it apply to all of India.`;
    const unknown = row.states.find((code) => !(code in stateLabels));
    if (unknown) return `The holiday on ${day} names ${unknown}, which is not a state or union territory the platform knows.`;
  }
  const byDate = new Map<string, HolidayRow[]>();
  for (const row of rows) byDate.set(row.date, [...(byDate.get(row.date) ?? []), row]);
  for (const [date, entries] of byDate) {
    const day = formatDay(date);
    const allIndia = entries.filter((row) => row.appliesTo === ALL_INDIA);
    if (allIndia.length > 1) return `Two holidays on ${day} apply to all of India. Keep one.`;
    const named = entries.filter((row) => row.appliesTo === STATES).flatMap((row) => row.states);
    if (allIndia.length > 0 && named.length > 0) {
      return `${day} is already a holiday for all of India, so it cannot also be a holiday for ${stateLabels[named[0]]} alone.`;
    }
    const twice = named.find((code, index) => named.indexOf(code) !== index);
    if (twice) return `${day} is a holiday for ${stateLabels[twice]} twice. Keep one.`;
  }
  return null;
}

/** The request body. Names are sent trimmed; an all-India holiday sends no states. */
export function yearPayload(form: YearForm, expectedVersion: number | null): Record<string, unknown> {
  return {
    expected_version: expectedVersion,
    is_complete: form.complete,
    holidays: form.rows.map((row) => ({
      holiday_date: row.date,
      holiday_kind_code: row.kind,
      holiday_name: row.name.trim(),
      applies_to_code: row.appliesTo,
      state_codes: row.appliesTo === STATES ? [...row.states].sort() : [],
    })),
  };
}

function entriesByDate(rows: Pick<HolidayRow, "date" | "kind" | "name" | "appliesTo" | "states">[]): Map<string, string> {
  const grouped = new Map<string, string[]>();
  for (const row of rows) {
    const entry = JSON.stringify([row.kind, row.name.trim(), row.appliesTo, row.appliesTo === STATES ? [...row.states].sort() : []]);
    grouped.set(row.date, [...(grouped.get(row.date) ?? []), entry]);
  }
  return new Map([...grouped].map(([date, entries]) => [date, JSON.stringify(entries.sort())]));
}

/** The dates a save would add, remove or change - a change of kind, name or states - earliest first, as the server
 *  counts them (`rules.year_changes`). */
export function changedDates(form: YearForm, year: CalendarYear): string[] {
  const before = entriesByDate(formFromYear(year).rows);
  const after = entriesByDate(form.rows.filter((row) => isDate(row.date)));
  const dates = new Set([...before.keys(), ...after.keys()]);
  return [...dates].filter((date) => before.get(date) !== after.get(date)).sort();
}

/** Whether the form differs from the year as saved: Save is offered only then. */
export function yearFormChanged(form: YearForm, year: CalendarYear): boolean {
  return form.complete !== year.is_complete || form.rows.some((row) => !isDate(row.date)) || changedDates(form, year).length > 0;
}

/** The warning beside Save when a change touches a day already passed (Q3): log sheets will correct days already on an
 *  approved log sheet (8C); today nothing is billed. Null when no such day is touched. */
export function passedDaysWarning(form: YearForm, year: CalendarYear): string | null {
  const passed = changedDates(form, year).filter((date) => date < year.today);
  if (passed.length === 0) return null;
  const days = passed.map((date) => formatDay(date)).join(", ");
  return `This changes ${passed.length === 1 ? "a day" : "days"} already passed: ${days}. Every Work Order shows the calendar as it is now.`;
}

// --- The page as reads arrive -------------------------------------------------------------------------------------

export type CalendarPage = { view: QueryView<CalendarAnswer>; form: YearForm | null };

export function initialCalendarPage(): CalendarPage {
  return { view: initialQueryView<CalendarAnswer>(), form: null };
}

/**
 * The page after one update of a read (`createQueryController`, which shows only the latest read's answer), as the
 * reminder settings page does (alertSettingsState.ts): a read starting - another year, a session change - clears the
 * year and its unsaved form at once; `keepShown` keeps them while the same session reads the same year again after a
 * save refused as stale, so the page does not empty under the message beside Save. An answer replaces the form with
 * the year as saved.
 */
export function calendarPageAfter(page: CalendarPage, update: QueryUpdate<CalendarAnswer>, keepShown = false): CalendarPage {
  const view = queryViewKeeping(page.view, update, () => keepShown);
  if (update.kind === "answer" && view.answer) return { view, form: formFromYear(view.answer.year) };
  return { view, form: view.answer ? page.form : null };
}

/** The page after a save: the year as now saved, its form made from it, and its summary in the picker. */
export function calendarPageSaved(page: CalendarPage, saved: CalendarYear): CalendarPage {
  const answer = page.view.answer;
  if (!answer || answer.year.calendar_year !== saved.calendar_year) return page;
  const summary: CalendarYearSummary = {
    calendar_year: saved.calendar_year,
    year_public_id: saved.year_public_id,
    year_version: saved.year_version,
    is_complete: saved.is_complete,
    complete_marked_by_display_name: saved.complete_marked_by_display_name,
    complete_marked_at: saved.complete_marked_at,
    holiday_count: saved.holiday_count,
    updated_by_display_name: saved.updated_by_display_name,
    updated_at: saved.updated_at,
  };
  const listed = answer.years.years.some((item) => item.calendar_year === saved.calendar_year);
  const years = listed
    ? answer.years.years.map((item) => (item.calendar_year === saved.calendar_year ? summary : item))
    : [...answer.years.years, summary].sort((a, b) => a.calendar_year - b.calendar_year);
  return { view: { ...page.view, answer: { ...answer, year: saved, years: { ...answer.years, years } } }, form: formFromYear(saved) };
}

/** The years the picker offers: those the server lists, and the year shown even when it is not among them. */
export function pickerYears(answer: CalendarAnswer): CalendarYearSummary[] {
  const years = answer.years.years;
  if (years.some((item) => item.calendar_year === answer.year.calendar_year)) return years;
  return [...years, answer.year].sort((a, b) => a.calendar_year - b.calendar_year);
}
