// Pure rules for the Work Order contract period and for "Apply these terms to other lines"
// (Slice 7D Part 3), kept out of the components so they can be tested without a browser DOM - the
// frontend has no component-test capability yet.
//
// The backend re-checks every rule and owns every refusal message. What lives here is what the
// screen has to decide for itself: which lines start ticked, what the button says it will do, and
// which ticked lines need the confirmation owner decision 20b asks for.

import { formatTermDate, type LineBillingTerms } from "./workOrderBillingTermsState";

export type ContractExtension = {
  extension_public_id: string;
  extension_sequence_no: number;
  previous_end_basis_code: string | null;
  previous_end_date: string | null;
  new_end_date: string;
  /** The day the extension starts; null where there was no fixed end for it to follow. */
  extension_start_date: string | null;
  customer_reference: string | null;
  received_date: string;
  extension_notes: string | null;
  created_by: string | null;
  created_by_display_name: string | null;
  created_at: string;
};

/** Days no contract runs on, before an extension that starts later than the day after (owner,
 * 22 September 2026). Both days inclusive. */
export type ContractGap = {
  first_day: string;
  last_day: string;
  extension_sequence_no: number;
};

export type ContractPeriod = {
  work_order_public_id: string;
  period_public_id: string | null;
  period_version: number | null;
  contract_start_date: string | null;
  contract_end_basis_code: string | null;
  contract_end_date: string | null;
  contract_notes: string | null;
  contract_state_code: string;
  contract_state_label: string;
  days_until_start: number | null;
  days_until_end: number | null;
  needs_firm_end_date: boolean;
  is_complete: boolean;
  missing_items: string[];
  extensions: ContractExtension[];
  gaps: ContractGap[];
  updated_by: string | null;
  updated_by_display_name: string | null;
  updated_at: string | null;
};

export const CONTRACT_END_FIXED_DATE = "FIXED_DATE";
export const CONTRACT_END_UNTIL_WORK_COMPLETE = "UNTIL_WORK_COMPLETE";

/** How the end date is answered. Blank is deliberately a separate choice from "until the work is
 * complete": one is an answer and the other is not (owner decision 14). */
export const CONTRACT_END_OPTIONS = [
  { code: "", label: "Not recorded yet" },
  { code: CONTRACT_END_FIXED_DATE, label: "On a fixed date" },
  { code: CONTRACT_END_UNTIL_WORK_COMPLETE, label: "Until the work is complete" },
];

const MISSING_CONTRACT_LABELS: Record<string, string> = {
  CONTRACT_START: "contract start date",
  CONTRACT_END: "contract end date",
};

export function missingContractDatesText(period: ContractPeriod | null): string {
  if (!period) return "Contract dates not loaded";
  if (period.is_complete) return "Contract dates recorded";
  return `Missing: ${period.missing_items.map((item) => MISSING_CONTRACT_LABELS[item] ?? item).join(", ")}`;
}

/** The form's shape. Kept as strings because that is what the date and select controls hold. */
export type ContractPeriodForm = {
  contract_start_date: string;
  contract_end_basis_code: string;
  contract_end_date: string;
  contract_notes: string;
};

export function formFromContractPeriod(period: ContractPeriod | null): ContractPeriodForm {
  return {
    contract_start_date: period?.contract_start_date ?? "",
    contract_end_basis_code: period?.contract_end_basis_code ?? "",
    contract_end_date: period?.contract_end_date ?? "",
    contract_notes: period?.contract_notes ?? "",
  };
}

/** Choosing "until the work is complete" clears any date already typed, because that answer carries
 * none and the backend refuses a request holding both. */
export function formAfterEndBasisChange(form: ContractPeriodForm, nextBasis: string): ContractPeriodForm {
  if (nextBasis === CONTRACT_END_FIXED_DATE) return { ...form, contract_end_basis_code: nextBasis };
  return { ...form, contract_end_basis_code: nextBasis, contract_end_date: "" };
}

export function contractPeriodPayload(form: ContractPeriodForm, expectedPeriodVersion: number | null) {
  return {
    expected_period_version: expectedPeriodVersion,
    contract_start_date: form.contract_start_date || null,
    contract_end_basis_code: form.contract_end_basis_code || null,
    contract_end_date: form.contract_end_basis_code === CONTRACT_END_FIXED_DATE ? form.contract_end_date || null : null,
    contract_notes: form.contract_notes.trim() ? form.contract_notes : null,
  };
}

/**
 * Once an extension exists, the end date changes only through extensions (owner, 22 September 2026):
 * the form shows it read-only, and the server refuses a save that changes it. Before this, a form
 * save could silently undo every extension recorded so far.
 */
export function endDateLockedByExtensions(period: ContractPeriod | null): boolean {
  return (period?.extensions.length ?? 0) > 0;
}

/** The only extension that can be removed. The server lists them oldest first. */
export function latestExtension(period: ContractPeriod | null): ContractExtension | null {
  if (!period || period.extensions.length === 0) return null;
  return period.extensions[period.extensions.length - 1];
}

/** What the end goes back to if this extension is removed. */
export function restoredEndText(extension: ContractExtension): string {
  if (extension.previous_end_date) return formatTermDate(extension.previous_end_date);
  if (extension.previous_end_basis_code === CONTRACT_END_UNTIL_WORK_COMPLETE) return "until the work is complete";
  return "not recorded";
}

export function removeExtensionConfirmationText(extension: ContractExtension): string {
  return (
    `Remove extension ${extension.extension_sequence_no} (${extensionSummary(extension)})? ` +
    `The contract end date goes back to ${restoredEndText(extension)}. ` +
    "The removal is kept in the Work Order's audit log."
  );
}

/** The next calendar day, as a date input holds it. */
export function dayAfter(isoDate: string): string {
  const [year, month, day] = isoDate.split("-").map(Number);
  const next = new Date(Date.UTC(year, month - 1, day + 1));
  return next.toISOString().slice(0, 10);
}

function dayBefore(isoDate: string): string {
  const [year, month, day] = isoDate.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day - 1)).toISOString().slice(0, 10);
}

/**
 * An extension normally starts the day after the fixed end it follows (owner, 22 September 2026), so
 * the form offers that. Where the end is open-ended or not recorded there is no end to follow and no
 * start date to ask for: the form hides the field and sends none.
 */
export function defaultExtensionStart(period: ContractPeriod | null): string {
  if (!period || period.contract_end_basis_code !== CONTRACT_END_FIXED_DATE || !period.contract_end_date) return "";
  return dayAfter(period.contract_end_date);
}

/** The days a start later than the day after would leave outside the contract, or null. */
export function gapBeforeStart(period: ContractPeriod | null, startDate: string): { first: string; last: string } | null {
  const normal = defaultExtensionStart(period);
  if (!normal || !/^\d{4}-\d{2}-\d{2}$/.test(startDate) || startDate <= normal) return null;
  return { first: normal, last: dayBefore(startDate) };
}

/** The question asked before recording a later start (owner: it needs confirmation, else it can be recorded). */
export function gapConfirmationText(period: ContractPeriod, startDate: string): string {
  const gap = gapBeforeStart(period, startDate);
  if (!gap) return "";
  return (
    `This extension starts on ${formatTermDate(startDate)}, not on ${formatTermDate(gap.first)}, the day after the ` +
    `contract ends. The days from ${formatTermDate(gap.first)} to ${formatTermDate(gap.last)} will be outside the ` +
    "contract: no log sheet or bill may fall on them. Record it anyway?"
  );
}

/** One gap, as the history lists it. */
export function gapText(gap: ContractGap): string {
  const days = gap.first_day === gap.last_day
    ? formatTermDate(gap.first_day)
    : `${formatTermDate(gap.first_day)} to ${formatTermDate(gap.last_day)}`;
  return `No contract runs on ${days}, before extension ${gap.extension_sequence_no}.`;
}

/** Today's date in India, as the date inputs hold it. */
export function indiaToday(now: Date = new Date()): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata", year: "numeric", month: "2-digit", day: "2-digit" }).format(now);
}

/** How long ago an order may be dated before the screen asks the user to check it (owner, 22 September 2026). */
export const EXTENSION_ORDER_WARNING_DAYS = 15;

function daysBetween(fromIso: string, toIso: string): number {
  const [fy, fm, fd] = fromIso.split("-").map(Number);
  const [ty, tm, td] = toIso.split("-").map(Number);
  return Math.round((Date.UTC(ty, tm - 1, td) - Date.UTC(fy, fm - 1, fd)) / 86_400_000);
}

/**
 * A warning, never a refusal. The owner: extensions usually arrive before the contract ends, so an
 * order dated more than 15 days before today is worth a second look - but any date is accepted except
 * one before the contract starts, which the server refuses.
 */
export function extensionOrderDateWarning(receivedDate: string, today: string): string | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(receivedDate)) return null;
  if (daysBetween(receivedDate, today) <= EXTENSION_ORDER_WARNING_DAYS) return null;
  return (
    `This order is dated ${formatTermDate(receivedDate)}, more than ${EXTENSION_ORDER_WARNING_DAYS} days ago. ` +
    "Check the date before recording it. It can still be recorded."
  );
}

/** What one extension reads as in the history, naming both ends of the move - and its start, when
 * it does not run straight on from the end it follows. */
export function extensionSummary(extension: ContractExtension): string {
  const to = formatTermDate(extension.new_end_date);
  if (extension.previous_end_date) {
    const move = `${formatTermDate(extension.previous_end_date)} to ${to}`;
    const start = extension.extension_start_date;
    if (start && start !== dayAfter(extension.previous_end_date)) return `${move}, starting ${formatTermDate(start)}`;
    return move;
  }
  if (extension.previous_end_basis_code === CONTRACT_END_UNTIL_WORK_COMPLETE) {
    return `Until the work is complete, to ${to}`;
  }
  return `No end date recorded, to ${to}`;
}

/**
 * What a line's own dates read as. Both blank is the normal case - the line follows the Work Order -
 * and says so rather than showing two dashes, because "nothing recorded" and "follows the Work Order"
 * are the same thing here and only the second is informative (owner decision 13).
 */
export function lineDatesText(detail: { line_start_date?: string | null; line_end_date?: string | null } | undefined): string {
  const start = detail?.line_start_date;
  const end = detail?.line_end_date;
  if (!start && !end) return "The same dates as the Work Order";
  if (start && end) return `${formatTermDate(start)} to ${formatTermDate(end)}`;
  if (start) return `From ${formatTermDate(start)}, to the Work Order's end date`;
  return `From the Work Order's start date, to ${formatTermDate(end as string)}`;
}

// --- "Apply these terms to other lines" (owner decision 20) --------------------------------------

export type CopyTargetRow = {
  public_id: string;
  line_number: number;
  scope_description: string;
  /** Lines that already have terms are listed and left unticked, and show what they already hold. */
  hasTerms: boolean;
  existingSummary: string;
};

const BASIS_LABELS: Record<string, string> = { HOUR: "Hour", SHIFT: "Shift", DAY: "Day", MONTH: "Month" };

/** A line's own basis and rate, so a line that plainly differs is easy to leave alone (20a). */
export function existingTermsSummary(entry: LineBillingTerms | undefined): string {
  if (!entry || entry.periods.length === 0) return "No terms yet";
  const current = entry.periods.find((period) => period.period_number === entry.current_period_number) ?? entry.periods[0];
  const basis = BASIS_LABELS[current.billing_uom_code ?? ""] ?? null;
  const rate = current.normal_rate_amount ? `INR ${current.normal_rate_amount}` : "no rate";
  if (!basis) return `${rate}, billing basis not chosen`;
  return `${rate} per ${basis.toLowerCase()}`;
}

/** Every OTHER line, in line order. The source is the line already open, so it is not in its own
 * list (owner's own answer to why the list is of other lines). */
export function copyTargetRows(
  lines: { public_id: string; line_number: number; scope_description: string }[],
  terms: LineBillingTerms[],
  sourceLinePublicId: string,
): CopyTargetRow[] {
  return lines
    .filter((line) => line.public_id !== sourceLinePublicId)
    .map((line) => {
      const entry = terms.find((item) => item.work_order_line_public_id === line.public_id);
      return {
        public_id: line.public_id,
        line_number: line.line_number,
        scope_description: line.scope_description,
        hasTerms: (entry?.periods.length ?? 0) > 0,
        existingSummary: existingTermsSummary(entry),
      };
    });
}

/** Lines with no terms yet are ticked to begin with, because they are what this is for; lines that
 * already have terms are listed and left unticked (owner decision 20a). */
export function initialCopySelection(rows: CopyTargetRow[]): string[] {
  return rows.filter((row) => !row.hasTerms).map((row) => row.public_id);
}

export function toggleCopySelection(selected: string[], publicId: string): string[] {
  return selected.includes(publicId) ? selected.filter((item) => item !== publicId) : [...selected, publicId];
}

/** The button says how many lines it will change (owner decision 20b). */
export function copyButtonLabel(selectedCount: number): string {
  if (selectedCount === 0) return "Choose at least one line";
  if (selectedCount === 1) return "Apply these terms to 1 line";
  return `Apply these terms to ${selectedCount} lines`;
}

/** The ticked lines that already have terms - the only case where something recorded is replaced. */
export function rowsNeedingConfirmation(rows: CopyTargetRow[], selected: string[]): CopyTargetRow[] {
  return rows.filter((row) => row.hasTerms && selected.includes(row.public_id));
}

function nameLines(rows: { line_number: number }[]): string {
  const names = rows.map((row) => `line ${row.line_number}`);
  if (names.length <= 1) return names.join("");
  return `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`;
}

/** The confirmation names the lines whose terms would be replaced (owner decision 20b). */
export function confirmationText(rows: CopyTargetRow[]): string {
  if (rows.length === 0) return "";
  const subject = rows.length === 1 ? "already has billing terms" : "already have billing terms";
  return (
    `${nameLines(rows)} ${subject}, and applying these terms will replace them. ` +
    "Every period will be replaced, not added to. Do you want to continue?"
  );
}

export type CopyResult = {
  work_order_line_public_id: string;
  line_number: number;
  outcome: string;
  periods_copied: number;
  replaced_period_count: number;
  message: string | null;
};

/** The result, line by line - including any line that could not be written (owner decision 20b). */
export function copyResultText(results: CopyResult[]): string {
  const copied = results.filter((result) => result.outcome === "COPIED");
  const replaced = results.filter((result) => result.outcome === "REPLACED");
  const failed = results.filter((result) => result.outcome === "FAILED");
  const parts: string[] = [];
  if (copied.length) parts.push(`Terms copied to ${nameLines(copied)}.`);
  if (replaced.length) parts.push(`Terms replaced on ${nameLines(replaced)}.`);
  if (failed.length) parts.push(`Could not be written: ${nameLines(failed)}.`);
  return parts.join(" ");
}

export function copyHadFailures(results: CopyResult[]): boolean {
  return results.some((result) => result.outcome === "FAILED");
}
