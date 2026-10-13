// Pure rules for the allocation screens (8A core), kept out of the components so they can be tested without a
// browser DOM. The backend re-checks every rule and writes every refusal; these word what the screens show and
// build what they send.
//
// The code says assignment (RPA-001's word); the screens say allocation, the word Eligibility's answers use.

import { ANSWER_LABELS, answerTone, formatDay, resultText } from "../equipment/certificatesState";
import type { StatusTone } from "../../components/PageLayout";

// --- What the API returns -------------------------------------------------------------------------------

export type CapabilityBrief = {
  capability_code: string;
  capability_label: string;
  unit_symbol: string | null;
  value: string | null;
  choice_value: string | null;
  is_key: boolean;
};

export type AssetBrief = {
  asset_public_id: string;
  asset_reference: string;
  asset_kind_code: string;
  machine_number: string | null;
  serial_number: string | null;
  class_code: string;
  class_label: string;
  type_code: string | null;
  type_label: string | null;
  model_public_id: string | null;
  model_label: string | null;
  asset_status_code: string;
  asset_version: number;
  quantity: number;
  tracking_code: string;
  key_capability: CapabilityBrief | null;
  capabilities: CapabilityBrief[];
  flag_codes: string[];
};

export type AnswerResult = {
  asset_public_id: string;
  asset_reference: string;
  kind_code: string | null;
  kind_label: string | null;
  outcome_code: string;
  effect_code: string;
  cover_ends_on: string | null;
};

export type Answer = {
  decision_public_id: string | null;
  overall_code: string;
  valid_until: string | null;
  evaluated_on: string;
  site_state_code: string;
  site_state_label: string;
  central_government_site: boolean;
  period_from: string;
  period_to: string | null;
  results: AnswerResult[];
};

export type SiteFacts = {
  site_public_id: string | null;
  site_label: string | null;
  state_text: string | null;
  state_code: string | null;
  state_label: string | null;
  central_government_site: boolean | null;
  problem_code: string | null;
  problem_message: string | null;
};

export type RequirementBrief = {
  requirement_public_id: string;
  requirement_reference: string;
  requirement_status_code: string;
  requirement_version: number;
  units_required: number;
  units_covered: number;
  units_remaining: number;
  required_from: string;
  required_to: string | null;
  planned_end: string | null;
  equipment_class_code: string;
  equipment_class_label: string;
  equipment_type_code: string | null;
  equipment_type_label: string | null;
  capabilities: { capability_code: string; capability_label: string; unit_symbol: string | null; minimum_value: string | null; choice_value: string | null }[];
  work_order_status_code: string;
};

export type AssignmentLink = {
  assignment_public_id: string;
  assignment_reference: string;
  asset_reference: string;
  machine_number: string | null;
  planned_from: string;
  effective_to: string | null;
};

export type Conflict = {
  assignment_public_id: string;
  assignment_reference: string;
  work_order_code: string;
  unit_number: number;
  assignment_status_code: string;
  busy_from: string;
  busy_to: string | null;
};

export type KitLine = {
  kit_line_public_id: string;
  trip_number: number;
  piece: AssetBrief | null;
  piece_public_id: string;
  quantity: number;
  line_status_code: string;
  removed_by_display_name: string | null;
  removed_at: string | null;
  busy_from: string;
  busy_to: string | null;
  fits_machine: boolean;
  decision: Answer | null;
  today: Answer | null;
};

export type Trip = { trip_public_id: string; trip_number: number; goes_on: string; note: string | null; kit: KitLine[] };

export type Assignment = {
  assignment_public_id: string;
  assignment_reference: string;
  assignment_status_code: string;
  requirement: RequirementBrief;
  unit_number: number;
  work_order_public_id: string;
  work_order_code: string;
  work_order_line_public_id: string;
  work_order_line_number: number;
  machine: AssetBrief | null;
  allocated_machine_number: string | null;
  planned_from: string;
  planned_to: string | null;
  ended_on: string | null;
  effective_to: string | null;
  billing_cycle_code: string | null;
  billing_cycle_set_by_display_name: string | null;
  billing_cycle_set_at: string | null;
  decision: Answer | null;
  today: Answer | null;
  compliance_state_code: string | null;
  warnings: string[];
  site: SiteFacts;
  replaces: AssignmentLink | null;
  replaced_by: AssignmentLink | null;
  end_reason_code: string | null;
  end_note: string | null;
  ended_by_display_name: string | null;
  ended_at: string | null;
  trips: Trip[];
  kit_pieces_listed: number;
  notes: string | null;
  assignment_version: number;
  created_by_display_name: string | null;
  created_at: string;
  updated_by_display_name: string | null;
  updated_at: string;
};

export type AssignmentAction = { assignment: Assignment; replaced: Assignment | null; replayed: boolean; events: unknown[] };

export type Candidate = { machine: AssetBrief; available: boolean; conflicts: Conflict[]; answer: Answer | null };

export type Candidates = {
  requirement: RequirementBrief;
  unit_number: number;
  period_from: string;
  period_to: string | null;
  site: SiteFacts;
  unit_conflicts: Conflict[];
  candidates: Candidate[];
  left_out: Record<string, number>;
};

export type KitOption = { piece: AssetBrief; available: boolean; quantity_free: number; conflicts: Conflict[]; answer: Answer | null };

export type KitOptions = {
  assignment_public_id: string;
  // The allocation's version the options were worked out for (8A-FB2-003).
  assignment_version: number;
  trip_number: number;
  window_from: string;
  window_to: string | null;
  machine_has_model: boolean;
  pieces: KitOption[];
};

// --- Who may do what (a usability aid: the server decides) --------------------------------------------------

// RESOURCE_ASSIGNMENT_WRITE: Operations and Admin, as for requirements.
export function canAllocate(roleCodes: readonly string[]): boolean {
  return roleCodes.some((role) => role === "ADMIN" || role === "OPERATIONS_USER");
}

// WORK_ORDER_LINE_BILLING_TERMS_WRITE: who may change a line's billing terms sets a machine's billing cycle.
export function canSetBillingCycle(roleCodes: readonly string[]): boolean {
  return roleCodes.some((role) => ["ADMIN", "SALES_USER", "SALES_MANAGER", "OPERATIONS_USER"].includes(role));
}

// --- Words -------------------------------------------------------------------------------------------------

export const STATUS_HELD = "HELD";

const STATUS_LABELS: Record<string, string> = { HELD: "Held for this Work Order", REPLACED: "Replaced", RELEASED: "Freed" };
const STATUS_TONES: Record<string, StatusTone> = { HELD: "info", REPLACED: "muted", RELEASED: "muted" };

export function statusLabel(code: string): string {
  return STATUS_LABELS[code] ?? code;
}

export function statusTone(code: string): StatusTone {
  return STATUS_TONES[code] ?? "neutral";
}

const COMPLIANCE_LABELS: Record<string, string> = {
  CLEAR: "Can be allocated today",
  WARNING: "Can be allocated today, with a warning",
  BLOCKED: "Cannot be allocated today",
  SITE_UNKNOWN: "The site cannot be judged",
};
const COMPLIANCE_TONES: Record<string, StatusTone> = { CLEAR: "success", WARNING: "warning", BLOCKED: "danger", SITE_UNKNOWN: "warning" };

export function complianceLabel(code: string | null): string {
  return code ? COMPLIANCE_LABELS[code] ?? code : "Not checked: the allocation has ended or its days are over";
}

export function complianceTone(code: string | null): StatusTone {
  return (code && COMPLIANCE_TONES[code]) || "muted";
}

export { ANSWER_LABELS, answerTone };

export function answerLabel(code: string): string {
  return ANSWER_LABELS[code] ?? code;
}

const WARNING_LABELS: Record<string, string> = {
  SITE_CHANGED: "The site's state or central-government answer has changed since the stored answer: check again",
  OUTSIDE_REQUIREMENT: "Its dates are no longer inside the requirement's",
  NO_LONGER_MATCHES: "The machine no longer meets what the requirement asks for",
  UNIT_NOT_REQUIRED: "Its unit is above the number of machines now required: free it",
  OUTSIDE_CONTRACT: "A day of it is outside the contract",
  BILLING_CYCLE_NOT_STATED: "No billing cycle yet",
  KIT_DOES_NOT_FIT: "A listed piece of kit no longer fits the machine's model",
  ANSWER_CHANGED: "Today's answer differs from the stored one: check again",
};

/** The words for a warning. A code the screen does not know yet is shown as it is, never hidden. */
export function warningLabel(code: string): string {
  return WARNING_LABELS[code] ?? code;
}

export const BILLING_CYCLE_OPTIONS = [
  { code: "", label: "Not stated yet" },
  { code: "WEEKLY", label: "Weekly" },
  { code: "MONTHLY", label: "Monthly" },
];

export function billingCycleLabel(code: string | null): string {
  return BILLING_CYCLE_OPTIONS.find((option) => option.code === (code ?? ""))?.label ?? code ?? "Not stated yet";
}

export const REPLACEMENT_REASONS = [
  { code: "BREAKDOWN", label: "Breakdown" },
  { code: "COMPLIANCE", label: "Certificates" },
  { code: "CUSTOMER_REQUEST", label: "Customer's request" },
  { code: "PLANNING", label: "Planning" },
  { code: "OTHER", label: "Other (say what)" },
];

export const RELEASE_REASONS = [
  { code: "NOT_NEEDED", label: "Not needed" },
  { code: "RECORDED_BY_MISTAKE", label: "Recorded by mistake" },
  { code: "MACHINE_UNAVAILABLE", label: "Machine unavailable" },
  { code: "OTHER", label: "Other (say what)" },
];

const END_REASON_LABELS: Record<string, string> = {
  ...Object.fromEntries([...REPLACEMENT_REASONS, ...RELEASE_REASONS].map((reason) => [reason.code, reason.label])),
  OTHER: "Other",
  REQUIREMENT_CANCELLED: "The requirement was cancelled",
};

export function endReasonLabel(code: string | null): string {
  return code ? END_REASON_LABELS[code] ?? code : "-";
}

const LEFT_OUT_LABELS: Record<string, string> = {
  TYPE_UNKNOWN: "type not known (its model is not mapped)",
  RATING_UNKNOWN: "a capability asked for not known",
  BELOW_REQUIREMENT: "below what is asked",
};

/** "Not offered: 2 with type not known, 1 below what is asked" - or empty when none was left out. */
export function leftOutText(leftOut: Record<string, number>): string {
  const parts = Object.entries(leftOut)
    .filter(([, count]) => count > 0)
    .map(([code, count]) => `${count} with ${LEFT_OUT_LABELS[code] ?? code}`);
  return parts.length > 0 ? `Not offered, of this class: ${parts.join("; ")}.` : "";
}

/** "EQ-000123 (MH 12 AB 1234)" - the platform's reference, and the registration where the machine has one. */
export function assetLabel(asset: Pick<AssetBrief, "asset_reference" | "machine_number" | "serial_number"> | null): string {
  if (!asset) return "-";
  const mark = asset.machine_number ?? asset.serial_number;
  return mark ? `${asset.asset_reference} (${mark})` : asset.asset_reference;
}

/** "Crawler crane, ACME CC 250" */
export function machineKindText(asset: AssetBrief | null): string {
  if (!asset) return "-";
  const kind = asset.type_label ? `${asset.type_label} ${asset.class_label.toLowerCase()}` : asset.class_label;
  return asset.model_label ? `${kind}, ${asset.model_label}` : kind;
}

export function capabilityText(capability: CapabilityBrief | null): string {
  if (!capability) return "-";
  if (capability.choice_value) return `${capability.capability_label} ${capability.choice_value}`;
  if (capability.value === null) return "-";
  const value = plain(capability.value);
  return capability.unit_symbol ? `${capability.capability_label} ${value} ${capability.unit_symbol}` : `${capability.capability_label} ${value}`;
}

/** Stored values as the server wrote them ("250.000"), without the trailing zeros a person would not write. */
export function plain(value: string): string {
  return value.includes(".") ? value.replace(/0+$/, "").replace(/\.$/, "") : value;
}

/** "2 crawler cranes, rated capacity at least 200 t" */
export function requirementText(requirement: RequirementBrief): string {
  const kind = requirement.equipment_type_label
    ? `${requirement.equipment_type_label} ${requirement.equipment_class_label.toLowerCase()}`
    : requirement.equipment_class_label;
  const asked = requirement.capabilities
    .map((item) =>
      item.choice_value
        ? `${item.capability_label.toLowerCase()} ${item.choice_value}`
        : `${item.capability_label.toLowerCase()} at least ${plain(item.minimum_value ?? "")}${item.unit_symbol ? ` ${item.unit_symbol}` : ""}`,
    )
    .join(", ");
  return `${requirement.units_required} x ${kind}${asked ? `, ${asked}` : ""}`;
}

/** "10 January 2027 to 31 March 2027", or "from 10 January 2027, with no end date". */
export function daysText(from: string, to: string | null): string {
  return to ? `${formatDay(from)} to ${formatDay(to)}` : `from ${formatDay(from)}, with no end date`;
}

/** An allocation's days as they stand: its planned days, or the days it kept when it ended. */
export function assignmentDaysText(assignment: Pick<Assignment, "planned_from" | "effective_to" | "assignment_status_code">): string {
  if (assignment.effective_to !== null && assignment.effective_to < assignment.planned_from) return "Never went (ended before it started)";
  return daysText(assignment.planned_from, assignment.effective_to);
}

export function siteText(site: SiteFacts): string {
  if (site.problem_message && site.problem_code === "SITE_NOT_RECORDED") return "No site recorded";
  const where = [site.site_label, site.state_label ?? site.state_text].filter(Boolean).join(", ");
  const central = site.central_government_site === true ? "a central-government site" : site.central_government_site === false ? "not a central-government site" : "central-government site not answered";
  return `${where || "-"}; ${central}`;
}

export function conflictText(conflict: Conflict): string {
  return `Allocated to ${conflict.work_order_code} (${conflict.assignment_reference}), ${daysText(conflict.busy_from, conflict.busy_to)}`;
}

/** The results worth reading: every one that stops or warns; all of them when none does. */
export function resultsToShow(answer: Answer): AnswerResult[] {
  const problems = answer.results.filter((result) => result.effect_code !== "NONE");
  return problems.length > 0 ? problems : answer.results;
}

/** One result in words: "Insurance on EQ-000124: runs out on 5 October 2026, during the period - renew it". */
export function answerResultText(result: AnswerResult, assetPublicId: string): string {
  const what = result.kind_label ?? "The asset";
  const where = result.asset_public_id !== assetPublicId ? ` on ${result.asset_reference}` : "";
  return `${what}${where}: ${resultText({ outcome_code: result.outcome_code, cover_ends_on: result.cover_ends_on, mark_public_id: null })}`;
}

// --- Units on a requirement --------------------------------------------------------------------------------

export type UnitRow = { unit: number; allocations: Assignment[]; required: boolean; covered: boolean };

/** One row per unit - 1 to the number required, and any unit above it that still has allocations - each with
 *  its allocations over time, held ones first within their days. A unit is `covered` when the server says its
 *  machines cover every day (8A-R8-002): allocation is offered only on a required unit that is not. */
export function unitRows(unitsRequired: number, assignments: Assignment[], coveredUnits: readonly number[] = []): UnitRow[] {
  const highest = Math.max(unitsRequired, ...assignments.map((item) => item.unit_number), 0);
  const rows: UnitRow[] = [];
  for (let unit = 1; unit <= highest; unit += 1) {
    const allocations = assignments
      .filter((item) => item.unit_number === unit)
      .sort((a, b) => a.planned_from.localeCompare(b.planned_from) || a.assignment_reference.localeCompare(b.assignment_reference));
    if (unit <= unitsRequired || allocations.length > 0) {
      rows.push({ unit, allocations, required: unit <= unitsRequired, covered: coveredUnits.includes(unit) });
    }
  }
  return rows;
}

export const ALLOCATIONS_PAGE_SIZE = 200;

/** Every page of a list until a page comes back short (8A-R9-003): a list of allocations never stops silently at
 * one page, so a Work Order's, requirement's or machine's whole history shows. Each page asks for the rows after
 * the last one already read, in the order they were recorded (8A-FB-004): a row changing, or leaving the filter,
 * between two pages moves no other row, so none is skipped or read twice - as a count of rows to skip would. */
export async function allPages<T>(fetchPage: (after: T | null, limit: number) => Promise<T[]>, limit = ALLOCATIONS_PAGE_SIZE): Promise<T[]> {
  const all: T[] = [];
  for (let after: T | null = null; ; after = all[all.length - 1]) {
    const page = await fetchPage(after, limit);
    all.push(...page);
    if (page.length < limit) return all;
  }
}

/** Allocations as the screens list them: held ones first, then by first day, Work Order, line and unit; the order
 * they were recorded after that. The server returns them in the order they were recorded (8A-FB-004). */
export function sortForDisplay<T extends Pick<Assignment, "assignment_status_code" | "planned_from" | "work_order_code" | "work_order_line_number" | "unit_number">>(
  rows: readonly T[],
): T[] {
  const held = (row: T) => (row.assignment_status_code === STATUS_HELD ? 0 : 1);
  return [...rows].sort(
    (a, b) =>
      held(a) - held(b) ||
      a.planned_from.localeCompare(b.planned_from) ||
      a.work_order_code.localeCompare(b.work_order_code) ||
      a.work_order_line_number - b.work_order_line_number ||
      a.unit_number - b.unit_number,
  );
}

// --- Forms -------------------------------------------------------------------------------------------------

export type AllocateForm = {
  machine_public_id: string;
  billing_cycle_code: string;
  notes: string;
  reason_code: string;
  reason_note: string;
  accept_warnings: boolean;
};

export const EMPTY_ALLOCATE_FORM: AllocateForm = {
  machine_public_id: "",
  billing_cycle_code: "",
  notes: "",
  reason_code: "",
  reason_note: "",
  accept_warnings: false,
};

/** Choosing another machine starts its confirmation afresh: a tick given for one machine's warnings is not one for
 *  another's. */
export function formAfterChoosing(form: AllocateForm, machinePublicId: string): AllocateForm {
  return form.machine_public_id === machinePublicId ? form : { ...form, machine_public_id: machinePublicId, accept_warnings: false };
}

/** What stops the allocation being sent, or null. The server checks everything again. */
/** Whether the machines shown were found for the dates now in the boxes (independent review, 8A-R1-006). After a
 * change, choosing and saving wait for "Find machines for these days", so nothing is saved for dates not shown. */
export function answerIsForDates(answer: Pick<Candidates, "period_from" | "period_to">, dates: { from: string; to: string }): boolean {
  return dates.from === answer.period_from && dates.to === (answer.period_to ?? "");
}

/** Why a requirement's unit cannot be allocated to yet, from its line as read (8A-R1-007): the site, or whether it
 * is a central-government site, not recorded. The server names a state it does not recognise when machines are
 * found. Null when the finder may be opened. */
export function lineSiteProblem(line: { site: unknown; site_central_government?: boolean | null }, lineNumber: number): string | null {
  if (!line.site) return `Record the site on line ${lineNumber}'s details first.`;
  if (line.site_central_government === null || line.site_central_government === undefined) {
    return `Say on line ${lineNumber}'s details whether its site is a central-government site first.`;
  }
  return null;
}

export const WORK_ORDER_CLOSED_TEXT = "This Work Order is closed. Its machines can no longer be allocated or changed.";

/** Whether the requirement's Work Order is closed: the server refuses every allocation write then (8A-R2-001). */
export function workOrderClosed(requirement: Pick<RequirementBrief, "work_order_status_code">): boolean {
  return requirement.work_order_status_code === "CLOSED";
}

export const UNIT_TAKEN_TEXT = "This unit already has a machine on some of these days. Choose other days and find machines again.";

/** Today in India, as YYYY-MM-DD, moved by `offsetDays`: the business date the server decides on. */
export function todayIso(offsetDays = 0): string {
  const today = new Date(new Date().toLocaleString("en-US", { timeZone: "Asia/Kolkata" }));
  today.setDate(today.getDate() + offsetDays);
  return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
}

/** Whether an allocation's first day has come: from then its days stay on the record (owner, 1 October 2026). */
export function hasStarted(plannedFrom: string, today: string): boolean {
  return plannedFrom <= today;
}

/** Why new dates cannot be saved, or null: once the allocation has started, its first day stays and only its last day
 * can change - the server refuses the rest (owner, 1 October 2026; TB-1 finding TB1-306). */
export function datesProblem(from: string, allocation: Pick<Assignment, "assignment_reference" | "planned_from">, today: string): string | null {
  if (from !== allocation.planned_from && hasStarted(allocation.planned_from, today)) {
    return (
      `${allocation.assignment_reference} started on ${formatDay(allocation.planned_from)}, so its days stay on the record: its first ` +
      "day cannot change, only its last day. If it was recorded by mistake, free it as Recorded by mistake and allocate again."
    );
  }
  return null;
}

/** Why a replacement cannot start on a day (8A-R3-003): it replaces the old allocation from one of its own days, and
 * once the old allocation has started, not from its first day. */
export function replaceStartProblem(
  from: string,
  replaced: Pick<Assignment, "assignment_reference" | "planned_from" | "effective_to">,
  today: string,
): string | null {
  if (from === replaced.planned_from && hasStarted(replaced.planned_from, today)) {
    return (
      `${replaced.assignment_reference} started on ${formatDay(replaced.planned_from)}, so its days stay on the record: the replacement ` +
      "must start after its first day. If it was recorded by mistake, free it as Recorded by mistake and allocate again."
    );
  }
  if (from >= replaced.planned_from && (replaced.effective_to === null || from <= replaced.effective_to)) return null;
  return `The replacement must start on a day of ${replaced.assignment_reference}: ${daysText(replaced.planned_from, replaced.effective_to)}.`;
}

type AllocateContext = {
  site: SiteFacts;
  datesShown: boolean;
  workOrderClosed?: boolean;
  // The finder found another allocation on the unit on some of the days (8A-R3-004).
  unitTaken?: boolean;
  // Why the replacement cannot start on the day shown (replaceStartProblem).
  replaceProblem?: string | null;
};

export function allocateProblem(form: AllocateForm, chosen: Candidate | undefined, replacing: boolean, context: AllocateContext): string | null {
  if (context.workOrderClosed) return WORK_ORDER_CLOSED_TEXT;
  // The server refuses every allocation while the site cannot be judged, so the page never offers one (8A-R1-007).
  if (context.site.problem_code) return context.site.problem_message ?? "The site cannot be judged yet.";
  if (!context.datesShown) return "Find machines for these days first: the machines shown are for other dates.";
  if (context.unitTaken) return UNIT_TAKEN_TEXT;
  if (context.replaceProblem) return context.replaceProblem;
  if (!chosen) return "Choose a machine.";
  if (!chosen.available) return "That machine is allocated elsewhere on some of these days. Choose another.";
  if (chosen.answer && (chosen.answer.overall_code === "BLOCKED" || chosen.answer.overall_code === "OVERRIDE_REQUIRED")) {
    return "That machine cannot be allocated. Choose another, or have its certificates put right first.";
  }
  if (!chosen.answer) return "That machine has no answer for the site yet. Find machines for these days again.";
  if (chosen.answer.overall_code === "WARNING" && !form.accept_warnings) return 'Tick "I have seen these warnings" first.';
  if (replacing && !form.reason_code) return "Choose why the machine is being replaced.";
  if (replacing && form.reason_code === "OTHER" && !form.reason_note.trim()) return "Say what the other reason is.";
  return null;
}

type Period = { period_from: string; period_to: string | null };

export function createPayload(requirementPublicId: string, unit: number, period: Period, form: AllocateForm, key: string, mayBill: boolean) {
  return {
    create_request_key: key,
    requirement_public_id: requirementPublicId,
    unit_number: unit,
    machine_public_id: form.machine_public_id,
    planned_from: period.period_from,
    planned_to: period.period_to,
    ...(mayBill && form.billing_cycle_code ? { billing_cycle_code: form.billing_cycle_code } : {}),
    notes: form.notes.trim() || null,
    accept_warnings: form.accept_warnings,
  };
}

/** A replacement keeps the old allocation's billing cycle unless the form says otherwise ("" keeps it). */
export function replacePayload(version: number, period: Period, form: AllocateForm, key: string, mayBill: boolean) {
  return {
    create_request_key: key,
    expected_assignment_version: version,
    machine_public_id: form.machine_public_id,
    replace_from: period.period_from,
    planned_to: period.period_to,
    ...(mayBill && form.billing_cycle_code ? { billing_cycle_code: form.billing_cycle_code } : {}),
    reason_code: form.reason_code,
    note: form.reason_note.trim() || null,
    accept_warnings: form.accept_warnings,
  };
}

/** The finder's query: the period the page shows, empty until the server's first answer gives its defaults. */
export type FinderQuery = { requirement: string; unit: number; from: string; to: string; replacing: string };

export function finderParams(query: FinderQuery): URLSearchParams {
  const params = new URLSearchParams({ requirement_public_id: query.requirement, unit_number: String(query.unit) });
  if (query.from) params.set("period_from", query.from);
  if (query.to) params.set("period_to", query.to);
  if (query.replacing) params.set("replacing_assignment_public_id", query.replacing);
  return params;
}

/** The unit asked for in a page's address: a whole number from 1, else 1. */
export function unitFromSearch(value: string | null): number {
  const unit = Number(value);
  return Number.isInteger(unit) && unit >= 1 ? unit : 1;
}

// --- Kit ---------------------------------------------------------------------------------------------------

/** How many of each piece the form will send, from what the user typed: a piece tracked one by one is 1 when
 *  ticked; a counted set whatever was typed. Pieces not chosen, or chosen with nothing, are left out. */
export function kitPiecesToSend(chosen: Record<string, string>, options: KitOption[]): { piece_public_id: string; quantity: number }[] {
  const pieces: { piece_public_id: string; quantity: number }[] = [];
  for (const option of options) {
    const typed = chosen[option.piece.asset_public_id];
    if (typed === undefined || typed === "") continue;
    const quantity = option.piece.tracking_code === "COUNTED" ? Number(typed) : 1;
    pieces.push({ piece_public_id: option.piece.asset_public_id, quantity });
  }
  return pieces;
}

/** What stops the pieces being sent, or null. */
/** Where a kit action's message goes (8A-R5-002): a listing's beside its own trip's "List these pieces", a removal's
 * beside its own line's "Remove" - never under another trip's or line's controls. */
export function kitFeedbackKey(tripNumber: number): string {
  return `kit:${tripNumber}`;
}

export function removeFeedbackKey(kitLinePublicId: string): string {
  return `remove:${kitLinePublicId}`;
}

/** A form's draft once a fresh copy of the allocation arrives (owner's screen check, 29 September 2026). The page
 * keeps showing the allocation while it reads it again, so the user may be typing meanwhile: the fresh copy
 * replaces a draft only where the recorded value changed - or at first, or on another allocation (`before`
 * undefined). */
export function draftAfterRefresh<T>(draft: T, before: T | undefined, after: T): T {
  return before === undefined || JSON.stringify(before) !== JSON.stringify(after) ? after : draft;
}

/** What each Trip (Own Load) carries after a fresh copy arrives: draftAfterRefresh, trip by trip. */
export function loadDraftsAfterRefresh(
  drafts: Record<number, string>,
  before: readonly Trip[] | undefined,
  after: readonly Trip[],
): Record<number, string> {
  const was = before ? loadDrafts(before) : undefined;
  return Object.fromEntries(
    after.map((trip) => [trip.trip_number, draftAfterRefresh(drafts[trip.trip_number] ?? "", was?.[trip.trip_number], trip.note ?? "")]),
  );
}

/** The choices a kit picker keeps when its options are read again (8A-FB2-003): a piece still selectable, and of a
 * counted set no more than is now free; the rest are dropped, so the picker never keeps what the server would
 * refuse. */
export function reconcileChoices(chosen: Readonly<Record<string, string>>, pieces: readonly KitOption[]): Record<string, string> {
  const kept: Record<string, string> = {};
  for (const option of pieces) {
    const id = option.piece.asset_public_id;
    const value = chosen[id];
    if (!value || !kitPieceSelectable(option)) continue;
    if (option.piece.tracking_code === "COUNTED") {
      const count = Number(value);
      if (!Number.isInteger(count) || count < 1 || count > option.quantity_free) continue;
    }
    kept[id] = value;
  }
  return kept;
}

/** The day the next Trip (Own Load) form offers once a fresh copy of the allocation arrives (8A-FB2-004): the
 * allocation's first day when the form still shows the first day it offered before, or nothing; else the day the
 * user chose. */
export function tripDayAfterRefresh(draft: string, before: string | undefined, after: string): string {
  return draft === "" || draft === before ? after : draft;
}

/** Why a Trip (Own Load) cannot go on this day, or null: the server takes only a day of the allocation's planned
 * days (8A-FB2-004). */
export function tripDayProblem(day: string, from: string, to: string | null): string | null {
  if (!day) return "Choose the day it goes.";
  if (day < from || (to !== null && day > to)) return `A Trip (Own Load) goes on a day of the allocation: ${daysText(from, to)}.`;
  return null;
}

/** Why the machine cannot be freed as the form stands, or null (8A-FB-005): a reason, and for "Other" a note - the
 * server refuses "Other" without one. Once the allocation has started, a last day too, unless it was recorded by
 * mistake (owner, 1 October 2026). */
export function releaseProblem(form: { last_day: string; reason_code: string; note: string }, plannedFrom: string, today: string): string | null {
  if (!form.reason_code) return "Choose why the machine is being freed.";
  if (form.reason_code === "OTHER" && !form.note.trim()) return "Say what the other reason is, in the note.";
  if (!form.last_day && form.reason_code !== "RECORDED_BY_MISTAKE" && hasStarted(plannedFrom, today)) {
    return `It started on ${formatDay(plannedFrom)}: give its last day on the job. Leave the last day empty only when it was recorded by mistake.`;
  }
  return null;
}

/** Where saving what a Trip (Own Load) carries shows its message: beside that trip's own button. */
export function loadFeedbackKey(tripNumber: number): string {
  return `load:${tripNumber}`;
}

/** What each Trip (Own Load) carries, as recorded: the drafts its forms start from. */
export function loadDrafts(trips: readonly Trip[]): Record<number, string> {
  return Object.fromEntries(trips.map((trip) => [trip.trip_number, trip.note ?? ""]));
}

/** Whether a piece may be chosen (8A-R4-004): free over the trip's days, and judged "can be allocated", with a
 * warning or without. A blocked piece, one needing approval, and one not judged - the site cannot be judged - never
 * reach the server. */
export function kitPieceSelectable(option: Pick<KitOption, "available" | "answer">): boolean {
  return option.available && (option.answer?.overall_code === "ELIGIBLE" || option.answer?.overall_code === "WARNING");
}

/** Why the allocation page cannot replace this allocation (8A-R4-002): the finder was opened for another unit or
 * requirement, or it is no longer held. Null when it can. */
export function replacingProblem(
  replacing: Pick<Assignment, "assignment_reference" | "assignment_status_code" | "unit_number"> & { requirement: Pick<RequirementBrief, "requirement_public_id"> },
  asked: { requirement: string; unit: number },
): string | null {
  if (replacing.requirement.requirement_public_id !== asked.requirement || replacing.unit_number !== asked.unit) {
    return `${replacing.assignment_reference} is on unit ${replacing.unit_number} of its requirement: open Replace from its own page.`;
  }
  if (replacing.assignment_status_code !== "HELD") return `${replacing.assignment_reference} is no longer held, so it cannot be replaced.`;
  return null;
}

export function kitProblem(chosen: Record<string, string>, options: KitOption[], acceptWarnings: boolean): string | null {
  const pieces = kitPiecesToSend(chosen, options);
  if (pieces.length === 0) return "Choose at least one piece.";
  for (const piece of pieces) {
    const option = options.find((item) => item.piece.asset_public_id === piece.piece_public_id)!;
    if (!Number.isInteger(piece.quantity) || piece.quantity < 1) return `Say how many of ${option.piece.asset_reference} go, as a whole number.`;
    if (piece.quantity > option.quantity_free) return `Only ${option.quantity_free} of ${option.piece.asset_reference} are free over these days.`;
    if (!option.answer) return `${option.piece.asset_reference} cannot be judged for the site yet.`;
    if (option.answer.overall_code === "BLOCKED" || option.answer.overall_code === "OVERRIDE_REQUIRED") {
      return `${option.piece.asset_reference} cannot go: its certificates are not in order.`;
    }
    if (option.answer?.overall_code === "WARNING" && !acceptWarnings) return 'Tick "I have seen these warnings" first.';
  }
  return null;
}

/** A piece's line in the picker: "EQ-000512 (HB-01), Hook block, ACME CC 250 hook, rated capacity 250 t". */
export function pieceText(piece: AssetBrief): string {
  const kind = piece.type_label ?? piece.class_label;
  const model = piece.model_label ? `, ${piece.model_label}` : "";
  const counted = piece.tracking_code === "COUNTED" ? `, a set of ${piece.quantity}` : "";
  return `${assetLabel(piece)}, ${kind}${model}${counted}`;
}
