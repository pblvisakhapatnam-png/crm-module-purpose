// Reminder settings (ELG-2, design section 5.6): each kind of reminder's schedule - bands of "from N days before the
// date, every M days" - and its path - steps adding an audience. The form's rules here are the server's, so a
// setting it would refuse is refused beside Save first; the server still decides. Kept apart from the page so they
// are tested without a browser.

import { type QueryUpdate, type QueryView, initialQueryView, queryViewKeeping } from "./certificatesState";

export type AlertBand = { from_days_before: number; every_days: number };

export type AlertStep = {
  step_number: number;
  role_code: string;
  role_label: string;
  starts_code: string;
  from_days_before: number | null;
  channel_codes: string[];
};

export type AlertSettingVersion = {
  setting_public_id: string;
  reminder_kind_code: string;
  version_number: number;
  saved_by: string | null;
  saved_by_display_name: string | null;
  saved_at: string;
  bands: AlertBand[];
  steps: AlertStep[];
};

export type AlertSetting = {
  reminder_kind_code: string;
  reminder_kind_label: string;
  current: AlertSettingVersion;
  earlier: AlertSettingVersion[];
};

export type AlertRole = { role_code: string; role_label: string };

export type AlertSettings = { settings: AlertSetting[]; roles: AlertRole[]; channel_codes: string[] };

export type AlertSettingAction = { setting: AlertSetting; unchanged: boolean };

export const MAX_BANDS = 10;
export const MAX_STEPS = 10;
export const MAX_DAYS = 365;

// --- Words ---------------------------------------------------------------------------------------------------

function days(count: number): string {
  return count === 1 ? "1 day" : `${count} days`;
}

/** A day relative to the date: "60 days before", "on the day", "7 days after". */
export function relativeText(daysBefore: number): string {
  if (daysBefore === 0) return "on the day";
  return daysBefore > 0 ? `${days(daysBefore)} before` : `${days(-daysBefore)} after`;
}

export function bandText(band: AlertBand): string {
  const start = band.from_days_before === 0 ? "From the day itself" : `From ${relativeText(band.from_days_before)} the date`;
  return `${start}, every ${band.every_days === 1 ? "day" : days(band.every_days)}`;
}

export function stepText(step: Pick<AlertStep, "starts_code" | "from_days_before">): string {
  if (step.starts_code !== "DAYS_BEFORE" || step.from_days_before === null) return "from the first reminder";
  return step.from_days_before === 0 ? "from the day itself" : `from ${relativeText(step.from_days_before)} the date`;
}

function listText(values: number[], unit: (last: number) => string): string {
  const numbers = values.map(String);
  const joined = numbers.length > 1 ? `${numbers.slice(0, -1).join(", ")} and ${numbers[numbers.length - 1]}` : numbers[0];
  return `${joined} ${unit(values[values.length - 1])}`;
}

/** The reminder days a schedule gives, in words: "Reminders 60, 30, 15, 8, 7, 6, 5, 4, 3, 2 and 1 day before; on
 *  the day, and every day after that." The same reckoning as the server's (reminders.py). */
export function reminderDaysText(bands: AlertBand[]): string {
  const ordered = [...bands].sort((a, b) => b.from_days_before - a.from_days_before);
  if (ordered.length === 0) return "No reminders.";
  const before: number[] = [];
  const after: number[] = [];
  let onTheDay = false;
  for (let index = 0; index < ordered.length - 1; index += 1) {
    const band = ordered[index];
    const floor = ordered[index + 1].from_days_before;
    if (band.every_days < 1) continue;
    for (let day = band.from_days_before; day > floor; day -= band.every_days) {
      if (day > 0) before.push(day);
      else if (day === 0) onTheDay = true;
      else after.push(-day);
    }
  }
  const parts: string[] = [];
  if (before.length) parts.push(listText(before, (last) => (last === 1 ? "day before" : "days before")));
  if (onTheDay) parts.push("on the day");
  if (after.length) parts.push(listText(after, (last) => (last === 1 ? "day after" : "days after")));
  const last = ordered[ordered.length - 1];
  const every = last.every_days === 1 ? "day" : days(last.every_days);
  parts.push(`${relativeText(last.from_days_before)}, and every ${every} after that`);
  return `Reminders ${parts.join("; ")}.`;
}

// --- The form ----------------------------------------------------------------------------------------------------

export type Direction = "before" | "after";
export type BandRow = { days: string; when: Direction; every: string };
export type StepStart = "FIRST_REMINDER" | "BEFORE" | "AFTER";
export type StepRow = { roleCode: string; starts: StepStart; days: string };
export type SettingForm = { bands: BandRow[]; steps: StepRow[] };

export const EMPTY_BAND_ROW: BandRow = { days: "0", when: "after", every: "1" };

export function formFromVersion(version: Pick<AlertSettingVersion, "bands" | "steps">): SettingForm {
  return {
    bands: version.bands.map((band) => ({
      days: String(Math.abs(band.from_days_before)),
      when: band.from_days_before > 0 ? "before" : "after",
      every: String(band.every_days),
    })),
    steps: version.steps.map((step) => ({
      roleCode: step.role_code,
      starts: step.starts_code !== "DAYS_BEFORE" || step.from_days_before === null ? "FIRST_REMINDER" : step.from_days_before > 0 ? "BEFORE" : "AFTER",
      days: step.from_days_before === null ? "" : String(Math.abs(step.from_days_before)),
    })),
  };
}

function wholeNumber(value: string): number | null {
  const trimmed = value.trim();
  if (!/^\d{1,4}$/.test(trimmed)) return null;
  return Number(trimmed);
}

function signed(daysValue: number, when: Direction): number {
  return when === "before" ? daysValue : -daysValue;
}

type Parsed = { bands: AlertBand[]; steps: { role_code: string; starts_code: string; from_days_before: number | null }[] };

function parse(form: SettingForm): Parsed | string {
  const bands: AlertBand[] = [];
  for (const row of form.bands) {
    const daysValue = wholeNumber(row.days);
    const every = wholeNumber(row.every);
    if (daysValue === null || every === null) return "Give each band its days as whole numbers.";
    bands.push({ from_days_before: signed(daysValue, row.when), every_days: every });
  }
  const steps: Parsed["steps"] = [];
  for (const row of form.steps) {
    if (row.starts === "FIRST_REMINDER") {
      steps.push({ role_code: row.roleCode, starts_code: "FIRST_REMINDER", from_days_before: null });
      continue;
    }
    const daysValue = wholeNumber(row.days);
    if (daysValue === null) return "Give the days for a step that starts some days before or after the date.";
    steps.push({ role_code: row.roleCode, starts_code: "DAYS_BEFORE", from_days_before: signed(daysValue, row.starts === "BEFORE" ? "before" : "after") });
  }
  return { bands, steps };
}

/** Why the form cannot be saved, in the server's words (reminders.py, setting_problem), or null. */
export function settingFormProblem(form: SettingForm, roleCodes: readonly string[]): string | null {
  const parsed = parse(form);
  if (typeof parsed === "string") return parsed;
  const { bands, steps } = parsed;
  if (bands.length < 1 || bands.length > MAX_BANDS) return `Give at least one band of reminders, and no more than ${MAX_BANDS}.`;
  for (const band of bands) {
    if (Math.abs(band.from_days_before) > MAX_DAYS) return `A band must start between ${MAX_DAYS} days before and ${MAX_DAYS} days after the date.`;
    if (band.every_days < 1 || band.every_days > MAX_DAYS) return `A band must repeat every 1 to ${MAX_DAYS} days.`;
  }
  const starts = bands.map((band) => band.from_days_before);
  if (new Set(starts).size !== starts.length) return "Two bands start on the same day. Give each band its own start.";
  if (Math.min(...starts) > 0) {
    return "The last band must start on the reminder's date - the day a certificate runs out, or 1 January for a holiday calendar year - or after it, so that what is past its date is never left without reminders.";
  }
  if (steps.length < 1 || steps.length > MAX_STEPS) return `Give at least one step on the path, and no more than ${MAX_STEPS}.`;
  const roles = steps.map((step) => step.role_code);
  if (roles.some((role) => !roleCodes.includes(role))) return "Choose each step's role from the list.";
  if (new Set(roles).size !== roles.length) return "A role may be on one step only.";
  if (steps[0].starts_code !== "FIRST_REMINDER") return "The first step must start at the first reminder, so that the first reminder reaches someone.";
  const firstBand = Math.max(...starts);
  for (const step of steps) {
    if (step.from_days_before === null) continue;
    if (step.from_days_before < -MAX_DAYS) return `A step must start no more than ${MAX_DAYS} days after the date.`;
    if (step.from_days_before > firstBand) return "A step cannot start before the first reminder.";
  }
  return null;
}

/** The body Save sends: the screen is the only channel for now (NTF-001 not built). */
export function settingPayload(form: SettingForm, expectedVersion: number): Record<string, unknown> {
  const parsed = parse(form);
  if (typeof parsed === "string") throw new Error(parsed);
  return {
    expected_version: expectedVersion,
    bands: parsed.bands,
    steps: parsed.steps.map((step) => ({ ...step, channel_codes: ["SCREEN"] })),
  };
}

/** The bands a form would save, for its preview; rows not yet whole numbers are left out. */
export function formBands(form: SettingForm): AlertBand[] {
  return form.bands.flatMap((row) => {
    const daysValue = wholeNumber(row.days);
    const every = wholeNumber(row.every);
    return daysValue === null || every === null || every < 1 ? [] : [{ from_days_before: signed(daysValue, row.when), every_days: every }];
  });
}

export function sameForm(a: SettingForm, b: SettingForm): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

// --- What the page shows ------------------------------------------------------------------------------------------

/** The settings, as the answer to the read now awaited, and the forms made from them. */
export type SettingsPage = { view: QueryView<AlertSettings>; forms: Record<string, SettingForm> };

export function initialSettingsPage(): SettingsPage {
  return { view: initialQueryView<AlertSettings>(), forms: {} };
}

/**
 * The page after one update of a read (`createQueryController`, which shows only the latest read's answer). A read
 * starting - the page opened, a session change - clears the settings and every unsaved form at once, so one session's
 * settings and edits are never shown under another's controls (independent review, ELG2-R4-002). `keepShown` keeps
 * them while the same session reads again after a save refused as stale, so the page does not empty under the
 * message beside Save. An answer replaces the forms with the settings in use.
 */
export function settingsPageAfter(page: SettingsPage, update: QueryUpdate<AlertSettings>, keepShown = false): SettingsPage {
  const view = queryViewKeeping(page.view, update, () => keepShown);
  if (update.kind === "answer" && view.answer) {
    return { view, forms: Object.fromEntries(view.answer.settings.map((item) => [item.reminder_kind_code, formFromVersion(item.current)])) };
  }
  return { view, forms: view.answer ? page.forms : {} };
}

/** The page after a setting is saved: that setting as now in use, and its form made from it; the others as they were. */
export function settingsPageSaved(page: SettingsPage, saved: AlertSetting): SettingsPage {
  const answer = page.view.answer;
  if (!answer) return page;
  const settings = answer.settings.map((item) => (item.reminder_kind_code === saved.reminder_kind_code ? saved : item));
  return {
    view: { ...page.view, answer: { ...answer, settings } },
    forms: { ...page.forms, [saved.reminder_kind_code]: formFromVersion(saved.current) },
  };
}
