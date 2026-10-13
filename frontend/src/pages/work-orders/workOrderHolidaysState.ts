// Pure rules for the Work Order holidays section (Slice 7D Part 4; since HOL-1, the Work Order's changes to PBL's
// holiday calendar), kept out of the component so they can be tested without a browser DOM - the frontend has no
// component-test capability yet. The backend re-checks every rule and writes every refusal message; these keep the
// form from sending what it can already tell is incomplete.
//
// Every Work Order follows PBL's calendar for each line's site state, and the list holds its changes to it: a holiday
// added, or a calendar holiday made a working day at the normal or the overtime rate (HOL-1, Q4). One list for every
// line (owner decision 27). The answer beside it tells "follows PBL's calendar unchanged" from "not entered yet",
// which an empty list cannot (decision 29). docs/agent/slices/hol-1-holiday-calendar.md, sections 5.2, 5.3 and 6.

import { formatTermDate } from "./workOrderBillingTermsState";

export type HolidayChange = {
  change_public_id: string;
  change_code: string;
  holiday_date: string;
  holiday_kind_code: string | null;
  working_day_rate_code: string | null;
  description: string | null;
};

export type HolidayList = {
  work_order_public_id: string;
  holiday_list_public_id: string | null;
  list_version: number | null;
  holidays_answer_code: string | null;
  changes: HolidayChange[];
  is_complete: boolean;
  missing_items: string[];
  updated_by_display_name?: string | null;
  updated_at?: string | null;
};

// --- The holidays that apply (GET .../holidays/resulting) ------------------------------------------------------------

export type CalendarEntry = {
  holiday_name: string;
  holiday_kind_code: string;
  applies_to_code: string;
  state_codes: string[];
  state_labels: string[];
};

export type CalendarDay = { holiday_date: string; entries: CalendarEntry[]; line_numbers: number[] };

export type ResultingDay = {
  holiday_date: string;
  day_code: string;
  source_code: string;
  holiday_kind_code: string | null;
  name: string | null;
  working_day_rate_code: string | null;
  note: string | null;
  lines_without_overtime_rate: number[];
};

export type HolidayGroup = {
  state_code: string | null;
  state_label: string | null;
  problem_code: string | null;
  problem_message: string | null;
  line_numbers: number[];
  days: ResultingDay[];
};

export type ChangeNote = { holiday_date: string; change_code: string; note_code: string; message: string };

/**
 * The notes on the changes just saved, to show beside "Holidays saved." as well as under "Holidays that apply" - a user
 * who saves a working day that does nothing is told at the button (the owner's HOL-1 screen check, 3 October 2026; the
 * rule that an action's feedback sits by its button). Only once the holidays that apply have been worked out from the
 * version this save made, so a note shown there is never an earlier version's.
 */
export function notesForSavedVersion(resulting: ResultingHolidays | null, savedVersion: number | null): ChangeNote[] {
  if (!resulting || savedVersion === null || resulting.list_version !== savedVersion) return [];
  return resulting.change_notes;
}

export type ResultingHolidays = {
  work_order_public_id: string;
  holidays_answer_code: string | null;
  list_version: number | null;
  period_from: string | null;
  period_to: string | null;
  period_note_code: string | null;
  period_message: string | null;
  calendar_days: CalendarDay[];
  groups: HolidayGroup[];
  years_not_complete: number[];
  change_notes: ChangeNote[];
};

// --- Codes and words ------------------------------------------------------------------------------------------------

export const CALENDAR_UNCHANGED = "CALENDAR_UNCHANGED";
export const CALENDAR_CHANGED = "CALENDAR_CHANGED";
export const HOLIDAY_ADDED = "HOLIDAY_ADDED";
export const WORKING_DAY = "WORKING_DAY";
export const NORMAL_RATE = "NORMAL_RATE";
export const OVERTIME_RATE = "OVERTIME_RATE";

export const HOLIDAY_ANSWER_OPTIONS = [
  { code: "", label: "Not answered yet" },
  { code: CALENDAR_UNCHANGED, label: "The Work Order follows PBL's calendar unchanged" },
  { code: CALENDAR_CHANGED, label: "The Work Order changes PBL's calendar as listed" },
];

/**
 * The answers the form offers. "Not answered yet" only until an answer is saved: an answer cannot be
 * taken back, so offering it afterwards would only invite a save the form then refuses.
 */
export function answerOptions(list: HolidayList | null): { code: string; label: string }[] {
  return list?.holidays_answer_code == null ? HOLIDAY_ANSWER_OPTIONS : HOLIDAY_ANSWER_OPTIONS.filter((option) => option.code !== "");
}

// Weekly off days are recorded with each line's billing terms, so a holiday added is one of these two kinds.
export const HOLIDAY_KIND_OPTIONS = [
  { code: "NATIONAL", label: "National holiday" },
  { code: "FESTIVAL", label: "Festival holiday" },
];

export function holidayKindLabel(code: string | null | undefined): string {
  return HOLIDAY_KIND_OPTIONS.find((option) => option.code === code)?.label ?? "-";
}

// A calendar holiday the Work Order works (Q4): every hour at the line's own overtime rate, or as a normal day.
export const WORKING_DAY_RATE_OPTIONS = [
  { code: NORMAL_RATE, label: "Working day, normal rate" },
  { code: OVERTIME_RATE, label: "Working day, overtime rate" },
];

/** The choice beside each calendar holiday: "Holiday" (no change), or a working day at a rate. */
export const CALENDAR_CHOICE_OPTIONS = [{ code: "", label: "Holiday" }, ...WORKING_DAY_RATE_OPTIONS];

export function workingDayRateLabel(code: string | null | undefined): string {
  return WORKING_DAY_RATE_OPTIONS.find((option) => option.code === code)?.label ?? "Working day";
}

// --- The form -------------------------------------------------------------------------------------------------------

/** A holiday the Work Order adds. `key` identifies the row on screen only; it is never sent. */
export type AddedRow = { key: string; holiday_date: string; holiday_kind_code: string; description: string };

/** A day the Work Order works: a calendar holiday chosen beside it, or a date typed in for a year not set up yet. */
export type WorkingRow = { key: string; holiday_date: string; rate: string; note: string };

export type HolidayForm = { answer: string; added: AddedRow[]; working: WorkingRow[] };

export function formFromHolidayList(list: HolidayList | null): HolidayForm {
  const changes = list?.changes ?? [];
  return {
    answer: list?.holidays_answer_code ?? "",
    added: changes
      .filter((change) => change.change_code === HOLIDAY_ADDED)
      .map((change) => ({
        key: change.change_public_id,
        holiday_date: change.holiday_date,
        holiday_kind_code: change.holiday_kind_code ?? "",
        description: change.description ?? "",
      })),
    working: changes
      .filter((change) => change.change_code === WORKING_DAY)
      .map((change) => ({ key: change.change_public_id, holiday_date: change.holiday_date, rate: change.working_day_rate_code ?? "", note: change.description ?? "" })),
  };
}

/** A new, empty holiday added. The key is passed in, so this stays a pure function. */
export function addAddedRow(form: HolidayForm, key: string): HolidayForm {
  return { ...form, added: [...form.added, { key, holiday_date: "", holiday_kind_code: "", description: "" }] };
}

export function removeAddedRow(form: HolidayForm, key: string): HolidayForm {
  return { ...form, added: form.added.filter((row) => row.key !== key) };
}

export function updateAddedRow(form: HolidayForm, key: string, change: Partial<Omit<AddedRow, "key">>): HolidayForm {
  return { ...form, added: form.added.map((row) => (row.key === key ? { ...row, ...change } : row)) };
}

/** A new, empty working day typed in by date. */
export function addWorkingRow(form: HolidayForm, key: string): HolidayForm {
  return { ...form, working: [...form.working, { key, holiday_date: "", rate: "", note: "" }] };
}

export function removeWorkingRow(form: HolidayForm, key: string): HolidayForm {
  return { ...form, working: form.working.filter((row) => row.key !== key) };
}

export function updateWorkingRow(form: HolidayForm, key: string, change: Partial<Omit<WorkingRow, "key">>): HolidayForm {
  return { ...form, working: form.working.map((row) => (row.key === key ? { ...row, ...change } : row)) };
}

/** The choice beside a calendar holiday: its working day's rate and note, or "" for a holiday. */
export function calendarChoice(form: HolidayForm, date: string): { rate: string; note: string } {
  const row = form.working.find((item) => item.holiday_date === date);
  return row ? { rate: row.rate, note: row.note } : { rate: "", note: "" };
}

/** Choose "Holiday" (rate "") or a working day at a rate beside a calendar holiday. A new working day takes `key`. */
export function setCalendarChoice(form: HolidayForm, date: string, rate: string, key: string): HolidayForm {
  if (rate === "") return { ...form, working: form.working.filter((row) => row.holiday_date !== date) };
  if (form.working.some((row) => row.holiday_date === date)) {
    return { ...form, working: form.working.map((row) => (row.holiday_date === date ? { ...row, rate } : row)) };
  }
  return { ...form, working: [...form.working, { key, holiday_date: date, rate, note: "" }] };
}

export function setCalendarNote(form: HolidayForm, date: string, note: string): HolidayForm {
  return { ...form, working: form.working.map((row) => (row.holiday_date === date ? { ...row, note } : row)) };
}

/** The working days typed in by date: those not beside a calendar holiday the form lists. */
export function typedWorkingRows(form: HolidayForm, calendarDays: readonly Pick<CalendarDay, "holiday_date">[]): WorkingRow[] {
  const listed = new Set(calendarDays.map((day) => day.holiday_date));
  return form.working.filter((row) => !listed.has(row.holiday_date));
}

/**
 * "Follows PBL's calendar unchanged" cannot be chosen while changes are listed - the server refuses it, and offering
 * it would invite a save that fails. The user removes the changes first.
 */
export function canChooseUnchanged(form: HolidayForm): boolean {
  return form.added.length === 0 && form.working.length === 0;
}

/** Whether the changes part of the form shows: only for "changes PBL's calendar as listed". */
export function showsChanges(form: HolidayForm): boolean {
  return form.answer === CALENDAR_CHANGED;
}

/**
 * What stops the form being sent, in words a user can act on, or null when it may be sent. Only what the
 * screen can already tell; the server checks everything again, the contract dates above all.
 */
export function holidayFormProblem(form: HolidayForm): string | null {
  if (form.answer === "") return "Choose whether the Work Order follows PBL's holiday calendar unchanged, or changes it as listed.";
  if (form.answer === CALENDAR_UNCHANGED) {
    return canChooseUnchanged(form) ? null : "Remove the changes listed, or choose that the Work Order changes PBL's calendar as listed.";
  }
  if (form.added.some((row) => row.holiday_date === "")) return "Enter a date for every holiday added, or remove the empty row.";
  if (form.working.some((row) => row.holiday_date === "")) return "Enter a date for every working day, or remove the empty row.";
  if (form.added.some((row) => row.holiday_kind_code === "")) return "Choose national or festival for every holiday added.";
  const unrated = form.working.find((row) => row.rate === "");
  if (unrated) return `Choose the normal rate or the overtime rate for the working day on ${formatTermDate(unrated.holiday_date)}.`;
  const seen = new Set<string>();
  for (const date of [...form.added, ...form.working].map((row) => row.holiday_date).sort()) {
    if (seen.has(date)) return `${formatTermDate(date)} is listed more than once. A date is either a holiday added or a working day: list it once.`;
    seen.add(date);
  }
  return null;
}

/** The request body. Changes go only with "changes PBL's calendar as listed"; a blank description or note is sent as none. */
export function holidayListPayload(form: HolidayForm, expectedListVersion: number | null): Record<string, unknown> {
  const text = (value: string) => (value.trim() === "" ? null : value.trim());
  return {
    expected_list_version: expectedListVersion,
    holidays_answer_code: form.answer,
    changes:
      form.answer === CALENDAR_CHANGED
        ? [
            ...form.added.map((row) => ({
              change_code: HOLIDAY_ADDED,
              holiday_date: row.holiday_date,
              holiday_kind_code: row.holiday_kind_code,
              description: text(row.description),
            })),
            ...form.working.map((row) => ({
              change_code: WORKING_DAY,
              holiday_date: row.holiday_date,
              working_day_rate_code: row.rate,
              description: text(row.note),
            })),
          ]
        : [],
  };
}

// --- Words ------------------------------------------------------------------------------------------------------------

function plural(count: number, one: string, many: string): string {
  return count === 1 ? `1 ${one}` : `${count} ${many}`;
}

/** One short line for the section's badge. */
export function holidaysStatusText(list: HolidayList | null): string {
  if (!list || list.holidays_answer_code == null) return "Holidays: not answered yet";
  if (list.holidays_answer_code === CALENDAR_UNCHANGED) return "Follows PBL's holiday calendar unchanged";
  if (list.changes.length === 0) return "Changes PBL's calendar: none entered yet";
  const added = list.changes.filter((change) => change.change_code === HOLIDAY_ADDED).length;
  const working = list.changes.length - added;
  const parts = [added ? plural(added, "holiday added", "holidays added") : "", working ? plural(working, "working day", "working days") : ""];
  return `Changes PBL's calendar: ${parts.filter(Boolean).join(", ")}`;
}

/** A change as one line of the read-only view: "26 January 2027 - Holiday added - National holiday - Republic Day",
 *  "22 March 2027 - Working day, overtime rate - Plant runs". */
export function changeText(change: HolidayChange): string {
  const parts =
    change.change_code === HOLIDAY_ADDED
      ? [formatTermDate(change.holiday_date), "Holiday added", holidayKindLabel(change.holiday_kind_code), change.description]
      : [formatTermDate(change.holiday_date), workingDayRateLabel(change.working_day_rate_code), change.description];
  return parts.filter((part): part is string => Boolean(part)).join(" - ");
}

/** A calendar holiday's names on a date, each with where it applies: "Gujarat Day (Gujarat); Maharashtra Day
 *  (Maharashtra)", or "Holi" for all of India. */
export function calendarDayText(day: Pick<CalendarDay, "entries">): string {
  return day.entries
    .map((entry) => (entry.applies_to_code === "ALL_INDIA" ? entry.holiday_name : `${entry.holiday_name} (${entry.state_labels.join(", ")})`))
    .join("; ");
}

export function linesText(numbers: readonly number[]): string {
  if (numbers.length === 1) return `Line ${numbers[0]}`;
  return `Lines ${numbers.slice(0, -1).join(", ")} and ${numbers[numbers.length - 1]}`;
}

/** A group's heading: "Lines 1 and 3 - Gujarat"; a group whose state is not known is headed by what to put right. */
export function groupTitle(group: Pick<HolidayGroup, "line_numbers" | "state_label" | "problem_code">): string {
  if (group.state_label) return `${linesText(group.line_numbers)} - ${group.state_label}`;
  return `${linesText(group.line_numbers)} - ${group.problem_code === "SITE_NOT_RECORDED" ? "no site recorded" : "site state not recognised"}`;
}

/** What a day is and where it came from. */
export function dayWhatText(day: Pick<ResultingDay, "name" | "holiday_kind_code" | "source_code">): string {
  const kind = day.holiday_kind_code ? holidayKindLabel(day.holiday_kind_code).toLowerCase() : "";
  const source = day.source_code === "WORK_ORDER" ? "added by this Work Order" : "PBL's calendar";
  return [day.name, kind ? `${kind}, ${source}` : source].filter(Boolean).join(" - ");
}

/** How a day is charged: a holiday by each line's off-day term (answer 24); a working day at the rate it says (Q4). */
export function dayChargeText(day: Pick<ResultingDay, "day_code" | "working_day_rate_code" | "lines_without_overtime_rate">): string {
  if (day.day_code !== WORKING_DAY) return "Holiday: as each line's off-day term says";
  if (day.working_day_rate_code !== OVERTIME_RATE) return "Working day, normal rate";
  const missing = day.lines_without_overtime_rate;
  if (missing.length === 0) return "Working day, every hour at the line's overtime rate";
  return `Working day, every hour at the line's overtime rate. ${linesText(missing)} ${missing.length === 1 ? "records" : "record"} no overtime rate for this day.`;
}

/** The days shown: "1 December 2026 to 30 November 2027", or what to do first. */
export function periodText(resulting: Pick<ResultingHolidays, "period_from" | "period_to" | "period_message">): string {
  if (!resulting.period_from || !resulting.period_to) return resulting.period_message ?? "";
  const span = `${formatTermDate(resulting.period_from)} to ${formatTermDate(resulting.period_to)}`;
  return resulting.period_message ? `${span}. ${resulting.period_message}` : span;
}

/** "2027", "2027 and 2028", "2027 to 2030": runs of years written as ranges. */
export function yearsText(years: readonly number[]): string {
  const sorted = [...years].sort((a, b) => a - b);
  const runs: string[] = [];
  let start = sorted[0];
  for (let index = 1; index <= sorted.length; index += 1) {
    if (index < sorted.length && sorted[index] === sorted[index - 1] + 1) continue;
    const end = sorted[index - 1];
    runs.push(end === start ? `${start}` : end === start + 1 ? `${start} and ${end}` : `${start} to ${end}`);
    start = sorted[index];
  }
  return runs.length > 1 ? `${runs.slice(0, -1).join(", ")} and ${runs[runs.length - 1]}` : runs[0] ?? "";
}

/** The note for years not complete (Q2): "PBL's holiday calendar for 2027 is not complete yet: only this Work Order's
 *  own changes are sure for 2027." */
export function yearsNotCompleteText(years: readonly number[]): string | null {
  if (years.length === 0) return null;
  const words = yearsText(years);
  return `PBL's holiday calendar for ${words} is not complete yet: the holidays shown for ${words} may change when Admin completes it.`;
}

/**
 * When to read "the holidays that apply" again: whenever what they are worked out from has changed on this page - the
 * contract's dates and extensions, a line's site, a line's billing terms (its overtime rate), or the Work Order's own
 * changes. Each part's version is enough, so a read of the page that changes nothing reads nothing again.
 */
export function resultingRefreshKey(parts: {
  workOrderPublicId: string;
  contractVersion: number | null | undefined;
  extensionCount: number | undefined;
  lineDetailVersions: readonly (number | null | undefined)[];
  billingTermRevisions: readonly number[];
  holidayListVersion: number | null | undefined;
}): string {
  return JSON.stringify([
    parts.workOrderPublicId,
    parts.contractVersion ?? null,
    parts.extensionCount ?? 0,
    parts.lineDetailVersions.map((version) => version ?? null),
    parts.billingTermRevisions,
    parts.holidayListVersion ?? null,
  ]);
}
