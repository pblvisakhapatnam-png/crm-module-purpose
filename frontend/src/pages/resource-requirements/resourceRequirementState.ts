// Pure rules for Resource Requirements (WRR-001), kept out of the components so they can be tested
// without a browser DOM. The backend re-checks every rule and writes every refusal message; these keep
// the form from sending what it can already tell is incomplete, and word what the screens show.
//
// A requirement asks for a number of machines over a period. What kind of machine comes from the
// platform's Equipment Reference: a class, an optional type, and the least value of each capability, in
// the capability's own unit - which the form shows and never sends.

import { billingBasisLabel, decimalDigits, formatTermDate } from "../work-orders/workOrderBillingTermsState";
import { SIGN_IN_FIRST } from "../../components/signInMessages";

// --- What the API returns ---------------------------------------------------------------------------

export type EquipmentClassCapability = {
  capability_code: string;
  capability_label: string;
  unit_code: string | null;
  unit_symbol: string | null;
  whole_numbers_only: boolean;
  value_kind_code: string;
  allowed_values: string[] | null;
  is_key: boolean;
  display_order: number;
  is_active: boolean;
};

export type EquipmentType = { type_code: string; type_label: string; display_order: number; is_active: boolean };

export type EquipmentClass = {
  class_code: string;
  class_label: string;
  display_order: number;
  business_line_codes: string[];
  is_active: boolean;
  types: EquipmentType[];
  capabilities: EquipmentClassCapability[];
};

export type EquipmentStructure = { taxonomy_version: number; classes: EquipmentClass[] };

export type RequirementCapability = {
  capability_code: string;
  capability_label: string;
  unit_code: string | null;
  unit_symbol: string | null;
  value_kind_code: string;
  is_key: boolean;
  minimum_value: string | null;
  choice_value: string | null;
};

export type RequirementItem = {
  item_number: number;
  equipment_class_code: string;
  equipment_class_label: string;
  equipment_type_code: string | null;
  equipment_type_label: string | null;
  equipment_specification: string | null;
  capabilities: RequirementCapability[];
};

export type LineFacts = {
  work_order_status_code: string;
  scope_description: string;
  equipment_service_category: string | null;
  quantity: string;
  uom: string;
  site: { public_id: string; address_line1: string | null; city: string | null; state: string | null } | null;
  line_start_date: string | null;
  line_end_date: string | null;
  contract_start_date: string | null;
  contract_end_basis_code: string | null;
  contract_end_date: string | null;
  contract_gaps: { first_day: string; last_day: string; extension_sequence_no: number }[];
  billing_terms_period_number: number | null;
  billing_uom_code: string | null;
  // Slice 7D Part 5: how many shifts a day the Work Order states; null when it states none, when not recorded, or
  // on an hourly line.
  shifts_per_day: number | null;
  work_order_crew_code: string | null;
  work_order_crew_operators: number | null;
  work_order_crew_helpers: number | null;
  // 8A core: whether the site is a central-government site; null is not answered.
  site_central_government?: boolean | null;
};

export type ResourceRequirement = {
  requirement_public_id: string;
  requirement_reference: string;
  work_order_public_id: string;
  work_order_code: string;
  work_order_line_public_id: string;
  work_order_line_number: number;
  units_required: number;
  required_from: string;
  required_to: string | null;
  crew_operators_required: number;
  crew_helpers_required: number;
  crew_notes: string | null;
  priority_code: string;
  planning_notes: string | null;
  requirement_status_code: string;
  requirement_version: number;
  // 8A core: units whose held machines cover every day, and units required less those.
  units_covered?: number;
  // The units whose machines cover every day (8A-R8-002).
  covered_unit_numbers?: number[];
  units_remaining?: number;
  items: RequirementItem[];
  warnings: string[];
  line: LineFacts;
  cancellation_reason: string | null;
  cancelled_by_display_name?: string | null;
  cancelled_at: string | null;
  created_by_display_name?: string | null;
  created_at: string;
  updated_by_display_name?: string | null;
  updated_at: string;
};

export type RequirementDefaults = {
  work_order_public_id: string;
  work_order_code: string;
  work_order_line_public_id: string;
  work_order_line_number: number;
  line: LineFacts;
  suggested: {
    units_required: number;
    required_from: string | null;
    required_to: string | null;
    crew_operators_required: number | null;
    crew_helpers_required: number | null;
    priority_code: string;
    equipment_class_code: string | null;
    equipment_type_code: string | null;
    equipment_class_matched_term: string | null;
  };
  existing_requirement_count: number;
};

// --- Who may write, and labels ------------------------------------------------------------------------

// RESOURCE_REQUIREMENT_WRITE on the backend, which is authoritative: Operations and Admin (owner, Q6).
export const RESOURCE_REQUIREMENT_WRITE_ROLES = ["ADMIN", "OPERATIONS_USER"];

export function canWriteRequirements(roleCodes: readonly string[]): boolean {
  return roleCodes.some((role) => RESOURCE_REQUIREMENT_WRITE_ROLES.includes(role));
}

export const HIRING = "HIRING";
export const STATUS_OPEN = "OPEN";
export const STATUS_CANCELLED = "CANCELLED";
// 8A core: machines held for some units, or for every unit on every day.
export const STATUS_PARTLY_FULFILLED = "PARTLY_FULFILLED";
export const STATUS_FULFILLED = "FULFILLED";
// The planning list's filter for what still needs machines: open and partly allocated.
export const STATUS_NEEDS_MACHINES = "NEEDS_MACHINES";

/** A requirement that can still be changed, cancelled and allocated to: any but a cancelled one. */
export function isLiveRequirement(code: string | undefined): boolean {
  return code !== undefined && code !== STATUS_CANCELLED;
}

export const PRIORITY_OPTIONS = [
  { code: "NORMAL", label: "Normal" },
  { code: "URGENT", label: "Urgent" },
];

export function priorityLabel(code: string): string {
  return PRIORITY_OPTIONS.find((option) => option.code === code)?.label ?? code;
}

export function statusLabel(code: string): string {
  if (code === STATUS_OPEN) return "Open";
  if (code === STATUS_PARTLY_FULFILLED) return "Partly allocated";
  if (code === STATUS_FULFILLED) return "Allocated";
  if (code === STATUS_CANCELLED) return "Cancelled";
  return code;
}

const WARNING_LABELS: Record<string, string> = {
  SITE_NOT_RECORDED: "The line has no site recorded yet",
  OUTSIDE_CONTRACT: "The dates no longer fit the contract or the line's own dates",
  CREW_DIFFERS_FROM_WORK_ORDER: "The crew differs from the Work Order's",
  KEY_CAPABILITY_NOT_STATED: "The main capability is not stated",
};

/** The words for a warning. A code the screen does not know yet is shown as it is, never hidden. */
export function warningLabel(code: string): string {
  return WARNING_LABELS[code] ?? code;
}

// --- The structure ------------------------------------------------------------------------------------

/** The classes a Work Order requirement may ask for: live, and deployed by Hiring. */
export function hiringClasses(structure: EquipmentStructure | null): EquipmentClass[] {
  if (!structure) return [];
  return structure.classes
    .filter((item) => item.is_active && item.business_line_codes.includes(HIRING))
    .sort((a, b) => a.display_order - b.display_order);
}

export function findClass(structure: EquipmentStructure | null, classCode: string): EquipmentClass | undefined {
  return structure?.classes.find((item) => item.class_code === classCode);
}

/**
 * The types to offer. A type already on the requirement stays offered even once retired, so saving an
 * unrelated change never asks the user to give it up (anything saved with a retired code keeps it).
 */
export function typeOptions(equipmentClass: EquipmentClass | undefined, keptTypeCode = ""): EquipmentType[] {
  if (!equipmentClass) return [];
  return equipmentClass.types
    .filter((item) => item.is_active || item.type_code === keptTypeCode)
    .sort((a, b) => a.display_order - b.display_order);
}

/** The capabilities to ask for, the key one first, then in the structure's order. Kept ones stay offered. */
export function capabilityFields(
  equipmentClass: EquipmentClass | undefined,
  keptCodes: readonly string[] = [],
): EquipmentClassCapability[] {
  if (!equipmentClass) return [];
  return equipmentClass.capabilities
    .filter((item) => item.is_active || keptCodes.includes(item.capability_code))
    .sort((a, b) => Number(b.is_key) - Number(a.is_key) || a.display_order - b.display_order);
}

/** "Rated capacity (t)", or the label alone for a count or a fixed list. */
export function capabilityFieldLabel(capability: EquipmentClassCapability): string {
  return capability.unit_symbol ? `${capability.capability_label} (${capability.unit_symbol})` : capability.capability_label;
}

// --- The form -----------------------------------------------------------------------------------------

export type RequirementForm = {
  units_required: string;
  required_from: string;
  required_to: string;
  crew_operators_required: string;
  crew_helpers_required: string;
  crew_notes: string;
  priority_code: string;
  planning_notes: string;
  equipment_class_code: string;
  // Blank: any type in the class.
  equipment_type_code: string;
  equipment_specification: string;
  // Capability code -> the value as typed (a least value), or the value chosen from a fixed list.
  capability_values: Record<string, string>;
};

const text = (value: string | number | null | undefined): string => (value === null || value === undefined ? "" : String(value));

/** A new requirement's form, filled from what the server suggests for the line. */
export function formFromDefaults(defaults: RequirementDefaults): RequirementForm {
  const suggested = defaults.suggested;
  return {
    units_required: text(suggested.units_required),
    required_from: text(suggested.required_from),
    required_to: text(suggested.required_to),
    crew_operators_required: text(suggested.crew_operators_required),
    crew_helpers_required: text(suggested.crew_helpers_required),
    crew_notes: "",
    priority_code: suggested.priority_code || "NORMAL",
    planning_notes: "",
    equipment_class_code: suggested.equipment_class_code ?? "",
    equipment_type_code: suggested.equipment_type_code ?? "",
    equipment_specification: "",
    capability_values: {},
  };
}

/** Stored values as the server wrote them ("220.000"), without the trailing zeros a person would not type. */
export function plainNumber(value: string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "";
  if (!value.includes(".")) return value;
  return value.replace(/0+$/, "").replace(/\.$/, "");
}

/** A saved requirement's form, for changing it. */
export function formFromRequirement(requirement: ResourceRequirement): RequirementForm {
  const item = requirement.items[0];
  const values: Record<string, string> = {};
  for (const capability of item?.capabilities ?? []) {
    values[capability.capability_code] =
      capability.choice_value !== null ? capability.choice_value : plainNumber(capability.minimum_value);
  }
  return {
    units_required: text(requirement.units_required),
    required_from: requirement.required_from,
    required_to: text(requirement.required_to),
    crew_operators_required: text(requirement.crew_operators_required),
    crew_helpers_required: text(requirement.crew_helpers_required),
    crew_notes: requirement.crew_notes ?? "",
    priority_code: requirement.priority_code,
    planning_notes: requirement.planning_notes ?? "",
    equipment_class_code: item?.equipment_class_code ?? "",
    equipment_type_code: item?.equipment_type_code ?? "",
    equipment_specification: item?.equipment_specification ?? "",
    capability_values: values,
  };
}

/** Choosing another class starts its type and capabilities afresh: they belong to the class. */
export function formAfterClassChange(form: RequirementForm, classCode: string): RequirementForm {
  if (classCode === form.equipment_class_code) return form;
  return { ...form, equipment_class_code: classCode, equipment_type_code: "", capability_values: {} };
}

export function formWithCapabilityValue(form: RequirementForm, capabilityCode: string, value: string): RequirementForm {
  return { ...form, capability_values: { ...form.capability_values, [capabilityCode]: value } };
}

/** The largest whole number the server records: its integer column's own range. */
export const WHOLE_NUMBER_MAX = 2_147_483_647;
// A least value is numeric(12,3): nine digits before the point, three after.
const CAPABILITY_WHOLE_DIGITS = 9;
const CAPABILITY_DECIMAL_PLACES = 3;

function wholeNumberProblem(label: string, value: string, minimum: number): string | null {
  const trimmed = value.trim();
  if (trimmed === "") return `Enter the ${label.toLowerCase()}.`;
  if (!/^\d+$/.test(trimmed)) return `${label} must be a whole number${minimum === 0 ? ", 0 or more" : " of at least 1"}.`;
  const number = Number(trimmed);
  if (number < minimum) return `${label} must be at least ${minimum}.`;
  if (number > WHOLE_NUMBER_MAX) return `${label} is larger than can be recorded.`;
  return null;
}

function capabilityProblem(capability: EquipmentClassCapability, value: string): string | null {
  const trimmed = value.trim();
  if (trimmed === "") return null;
  const label = capability.capability_label;
  if (capability.value_kind_code === "CHOICE") {
    return (capability.allowed_values ?? []).includes(trimmed) ? null : `Choose the ${label.toLowerCase()} from its list.`;
  }
  const number = Number(trimmed);
  const digits = decimalDigits(trimmed);
  if (!Number.isFinite(number) || !digits) return `${label} must be a number.`;
  if (number <= 0) return `${label} must be greater than 0.`;
  if (capability.whole_numbers_only && digits.fraction.length > 0) return `${label} is counted in whole numbers.`;
  if (digits.fraction.length > CAPABILITY_DECIMAL_PLACES) return `${label} can have at most 3 decimal places.`;
  if (digits.whole.length > CAPABILITY_WHOLE_DIGITS) return `${label} is larger than can be recorded.`;
  return null;
}

/**
 * What stops the requirement being sent, in words that name the field, or null. The dates against the
 * contract and the line are the server's to check: it knows the contract as it stands now.
 */
export function requirementFormProblem(form: RequirementForm, structure: EquipmentStructure | null): string | null {
  const units = wholeNumberProblem("Number of machines", form.units_required, 1);
  if (units) return units;
  if (!form.required_from) return "Enter the date the machines are needed from.";
  if (form.required_to && form.required_to < form.required_from) {
    return `The requirement cannot end on ${formatTermDate(form.required_to)}, before it starts on ${formatTermDate(form.required_from)}.`;
  }
  const crew =
    wholeNumberProblem("Operators", form.crew_operators_required, 0) ?? wholeNumberProblem("Helpers", form.crew_helpers_required, 0);
  if (crew) return crew;
  if (!form.equipment_class_code) return "Choose the kind of machine needed.";
  const equipmentClass = findClass(structure, form.equipment_class_code);
  if (!equipmentClass) return "Choose the kind of machine needed.";
  for (const capability of capabilityFields(equipmentClass, Object.keys(form.capability_values))) {
    const problem = capabilityProblem(capability, form.capability_values[capability.capability_code] ?? "");
    if (problem) return problem;
  }
  return null;
}

const orNull = (value: string): string | null => (value.trim() ? value.trim() : null);

/** The fields a create and a change both send. A capability left blank is not sent. */
export function requirementPayload(form: RequirementForm, structure: EquipmentStructure | null): Record<string, unknown> {
  const equipmentClass = findClass(structure, form.equipment_class_code);
  const capabilities = capabilityFields(equipmentClass, Object.keys(form.capability_values))
    .map((capability) => {
      const value = (form.capability_values[capability.capability_code] ?? "").trim();
      if (!value) return null;
      return capability.value_kind_code === "CHOICE"
        ? { capability_code: capability.capability_code, choice_value: value }
        : { capability_code: capability.capability_code, minimum_value: value };
    })
    .filter((entry): entry is { capability_code: string; minimum_value: string } | { capability_code: string; choice_value: string } =>
      Boolean(entry),
    );
  return {
    units_required: Number(form.units_required.trim()),
    required_from: form.required_from,
    required_to: form.required_to || null,
    crew_operators_required: Number(form.crew_operators_required.trim()),
    crew_helpers_required: Number(form.crew_helpers_required.trim()),
    crew_notes: orNull(form.crew_notes),
    priority_code: form.priority_code,
    planning_notes: orNull(form.planning_notes),
    items: [
      {
        equipment_class_code: form.equipment_class_code,
        equipment_type_code: form.equipment_type_code || null,
        equipment_specification: orNull(form.equipment_specification),
        capabilities,
      },
    ],
  };
}

/**
 * A key for one create request, generated once per form. Sending the same request with it again - a double
 * click, a retry after a lost reply - records one requirement, not two (ADR-023); the key with a changed form is
 * refused, so a change after a lost reply is made on the requirement it recorded (TB-1 TB1-102 part b). Built from
 * getRandomValues rather than randomUUID, which a browser offers only on a secure (HTTPS or localhost) page.
 */
export function newRequestKey(random: (bytes: Uint8Array) => Uint8Array = (bytes) => crypto.getRandomValues(bytes)): string {
  const bytes = random(new Uint8Array(16));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

// --- Words for the screens ----------------------------------------------------------------------------

/** Said as the new-requirement form opens what it recorded. A save the server already had from this form - its
 *  reply lost on the way - was recorded once, earlier (TB-1 TB1-102 part b). */
export function requirementRecordedText(reference: string, replayed: boolean): string {
  return replayed ? `Already recorded as ${reference}. Opening it...` : `Recorded as ${reference}. Opening it...`;
}

/** After a reply lost on the way: only the same form, unchanged, is safe to send again. */
export const REQUIREMENT_NETWORK_ERROR =
  "Network error while saving. Save again without changing anything: it will not record the requirement twice.";

/** "Crawler crane", or "Crane" when any type will do. */
export function itemMachineText(item: RequirementItem): string {
  return item.equipment_type_label
    ? `${item.equipment_type_label} ${item.equipment_class_label.toLowerCase()}`
    : item.equipment_class_label;
}

/** "rated capacity at least 220 t", or "axle configuration 6X4" for a fixed list. */
export function capabilityText(capability: RequirementCapability): string {
  if (capability.choice_value !== null) return `${capability.capability_label.toLowerCase()} ${capability.choice_value}`;
  const unit = capability.unit_symbol ? ` ${capability.unit_symbol}` : "";
  return `${capability.capability_label.toLowerCase()} at least ${plainNumber(capability.minimum_value)}${unit}`;
}

/** The requirement in one line: "2 x Crawler crane, rated capacity at least 220 t". The key capability only. */
export function requirementSummary(requirement: Pick<ResourceRequirement, "units_required" | "items">): string {
  const item = requirement.items[0];
  if (!item) return `${requirement.units_required} x (no machine stated)`;
  const key = item.capabilities.find((capability) => capability.is_key);
  return `${requirement.units_required} x ${itemMachineText(item)}${key ? `, ${capabilityText(key)}` : ""}`;
}

/** "From 15 October 2026", or "15 October 2026 to 31 March 2027". Blank end: until the line ends. */
export function requirementDatesText(requirement: Pick<ResourceRequirement, "required_from" | "required_to">): string {
  return requirement.required_to
    ? `${formatTermDate(requirement.required_from)} to ${formatTermDate(requirement.required_to)}`
    : `From ${formatTermDate(requirement.required_from)}, until the line ends`;
}

function people(count: number, one: string, many: string): string {
  return `${count} ${count === 1 ? one : many}`;
}

export function crewText(operators: number, helpers: number): string {
  if (operators === 0 && helpers === 0) return "No crew";
  return `${people(operators, "operator", "operators")}, ${people(helpers, "helper", "helpers")}`;
}

/** What the Work Order's own terms say about crew, for comparison beside the requirement's numbers. */
export function workOrderCrewText(line: LineFacts): string {
  if (line.work_order_crew_code === "NONE") return "Equipment only: no crew";
  if (line.work_order_crew_code === "STATED") {
    // A stated crew with a number still blank is not an answer yet: never shown as zero.
    if (line.work_order_crew_operators == null || line.work_order_crew_helpers == null) {
      return "Crew stated, but a number is not recorded yet";
    }
    const basis = billingBasisLabel(line.billing_uom_code)?.toLowerCase();
    return `${crewText(line.work_order_crew_operators, line.work_order_crew_helpers)}${basis ? ` per ${basis}` : ""}`;
  }
  return "Not recorded yet";
}

export function siteText(line: LineFacts): string {
  if (!line.site) return "No site recorded on the line yet";
  return [line.site.address_line1, line.site.city, line.site.state].filter(Boolean).join(", ");
}

export function contractText(line: LineFacts): string {
  if (!line.contract_start_date && !line.contract_end_date) {
    return line.contract_end_basis_code === "UNTIL_WORK_COMPLETE" ? "Until the work is complete" : "Not recorded yet";
  }
  const start = line.contract_start_date ? formatTermDate(line.contract_start_date) : "start not recorded";
  if (line.contract_end_date) return `${start} to ${formatTermDate(line.contract_end_date)}`;
  return line.contract_end_basis_code === "UNTIL_WORK_COMPLETE" ? `${start}, until the work is complete` : `From ${start}`;
}

export function lineDatesText(line: LineFacts): string {
  if (!line.line_start_date && !line.line_end_date) return "Follows the Work Order";
  const start = line.line_start_date ? formatTermDate(line.line_start_date) : "the contract start";
  const end = line.line_end_date ? formatTermDate(line.line_end_date) : "the contract end";
  return `${start} to ${end}`;
}

/** Where a new requirement for a line is recorded, returning to the page it was started from. */
export function newRequirementHref(workOrderLinePublicId: string, returnTo: string, returnLabel: string): string {
  const params = new URLSearchParams({ work_order_line: workOrderLinePublicId, returnTo, returnLabel });
  return `/resource-requirements/new?${params.toString()}`;
}

/** How many requirements one request asks for; the API's own largest page. */
export const REQUIREMENT_PAGE_SIZE = 200;
// A Work Order with more requirements than this is not a real one; failing loudly beats a partial list.
const REQUIREMENT_PAGE_LIMIT = 50;

/**
 * Every requirement, page by page, until a page comes back short. A screen that says "No requirement
 * recorded for this line" must have read them all: stopping at the first page could say so of a line
 * whose requirements are on the next one (review round 1, F-02).
 */
export async function fetchAllRequirementPages<T>(
  fetchPage: (offset: number, limit: number) => Promise<T[]>,
  pageSize = REQUIREMENT_PAGE_SIZE,
): Promise<T[]> {
  const all: T[] = [];
  for (let page = 0; page < REQUIREMENT_PAGE_LIMIT; page += 1) {
    const entries = await fetchPage(page * pageSize, pageSize);
    all.push(...entries);
    if (entries.length < pageSize) return all;
  }
  throw new Error("Too many requirements to list on one screen.");
}

// --- Answers that arrive out of order, and a date that moves ------------------------------------------

/**
 * Tickets for requests whose answers may come back in any order. Only the answer to the latest request may
 * be applied: an older one arriving last would show results for a filter or a date no longer chosen
 * (review round 2, F-07 and F-10).
 */
export function createLatestOnly(): { begin: () => number; isLatest: (ticket: number) => boolean } {
  let latest = 0;
  return {
    begin: () => {
      latest += 1;
      return latest;
    },
    isLatest: (ticket) => ticket === latest,
  };
}

/** A whole date as a date input gives it, "2026-10-15", that is a real day. */
export function isCompleteIsoDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const [year, month, day] = value.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  return date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day;
}

/** Which crew numbers the user has typed. Each is the user's own once typed; the other still follows. */
export type CrewTouched = { operators: boolean; helpers: boolean };

export const CREW_UNTOUCHED: CrewTouched = { operators: false, helpers: false };

/** The crew numbers typed so far, after an edit of the form. */
export function crewTouchedAfterEdit(touched: CrewTouched, before: RequirementForm, after: RequirementForm): CrewTouched {
  return {
    operators: touched.operators || after.crew_operators_required !== before.crew_operators_required,
    helpers: touched.helpers || after.crew_helpers_required !== before.crew_helpers_required,
  };
}

/**
 * A new requirement's crew after its start date moved: the Work Order's numbers in force on the new date
 * (Q4), each number on its own - a number the user has typed is never overwritten, and the other still
 * follows the date (review round 4, F-15). Where the Work Order's crew on the new date is not answered, an
 * untouched number goes back to empty rather than keep an earlier date's.
 */
export function formAfterLineDefaults(
  form: RequirementForm,
  suggested: Pick<RequirementDefaults["suggested"], "crew_operators_required" | "crew_helpers_required">,
  touched: CrewTouched,
): RequirementForm {
  return {
    ...form,
    crew_operators_required: touched.operators ? form.crew_operators_required : text(suggested.crew_operators_required),
    crew_helpers_required: touched.helpers ? form.crew_helpers_required : text(suggested.crew_helpers_required),
  };
}

// --- Whether the Work Order's facts for the date on the form are in -----------------------------------

/**
 * The Work Order's facts - billing terms and crew in force - for the start date on a form. "current" means
 * the facts shown are that date's (or there is no whole date yet, which the form's own check refuses);
 * "loading" and "failed" mean they are another date's, and saving must wait (review rounds 2 and 3, F-07
 * and F-12). `ticket` identifies the request whose answer is awaited: any other answer is stale.
 */
export type DateFacts = { status: "current" | "loading" | "failed"; ticket: number };

export const DATE_FACTS_CURRENT: DateFacts = { status: "current", ticket: 0 };

/** A new date on the form: its facts are awaited under this ticket, or there is nothing to read yet. */
export function dateFactsAsked(ticket: number, date: string): DateFacts {
  return { status: isCompleteIsoDate(date) ? "loading" : "current", ticket };
}

/** An answer came back. Only the answer to the request awaited counts; any other is ignored. */
export function dateFactsAnswered(facts: DateFacts, ticket: number, succeeded: boolean): DateFacts {
  if (ticket !== facts.ticket || facts.status !== "loading") return facts;
  return { status: succeeded ? "current" : "failed", ticket };
}

/**
 * Whether Save may be pressed at all. While the facts load, and after reading them failed, it may not: the
 * reason is shown from `dateFactsSaveProblem` beside the button, derived from the facts themselves and
 * never copied into a save message, so it disappears the moment a retry succeeds (review round 4, F-17).
 */
export function dateFactsAllowSave(facts: DateFacts): boolean {
  return facts.status === "current";
}

/** Why a save must wait, in words for beside the button, or null when it need not. */
export function dateFactsSaveProblem(facts: DateFacts): string | null {
  if (facts.status === "loading") return "Reading the Work Order for that date. Save when it has finished.";
  if (facts.status === "failed") {
    return "The Work Order could not be read for that date, so the crew and terms shown may be another date's. Read it again before saving.";
  }
  return null;
}

// --- The planning list's requests ----------------------------------------------------------------------

export type PlanningFilters = { statusCode: string; classCode: string };

export type PlanningListUpdate =
  | { kind: "loading"; offset: number }
  | { kind: "rows"; rows: ResourceRequirement[]; offset: number }
  | { kind: "failed"; message: string }
  | { kind: "signed-out" };

/**
 * The planning list's loading, kept out of the component so it can be tested. It holds the filters itself,
 * so every load - a filter change, a page turn, a session change - asks for the filters the controls show
 * (review round 3, F-14). Every load takes a ticket before anything else, even one that finds no session,
 * so an answer still on its way can never be shown after it (rounds 2 and 3, F-10 and F-14).
 */
export function createPlanningListController(deps: {
  getToken: () => string | null;
  fetchRows: (token: string, filters: PlanningFilters, offset: number) => Promise<ResourceRequirement[]>;
  show: (update: PlanningListUpdate) => void;
}) {
  let filters: PlanningFilters = { statusCode: STATUS_NEEDS_MACHINES, classCode: "" };
  const latest = createLatestOnly();

  async function load(offset: number): Promise<void> {
    const ticket = latest.begin();
    const token = deps.getToken();
    if (!token) {
      deps.show({ kind: "signed-out" });
      return;
    }
    deps.show({ kind: "loading", offset });
    try {
      const rows = await deps.fetchRows(token, filters, offset);
      if (latest.isLatest(ticket)) deps.show({ kind: "rows", rows, offset });
    } catch (error) {
      if (latest.isLatest(ticket)) {
        deps.show({ kind: "failed", message: error instanceof Error ? error.message : "The requirements could not be loaded." });
      }
    }
  }

  return {
    filters: (): PlanningFilters => filters,
    setFilters: (next: Partial<PlanningFilters>): Promise<void> => {
      filters = { ...filters, ...next };
      return load(0);
    },
    load,
  };
}

/**
 * What the planning list shows. Rows are shown only as the answer to the request now awaited: the moment a
 * new request starts - a filter change, a page turn, a refresh - the rows of the previous one are no longer
 * shown, so the table never lists one filter's requirements under another's controls, even while an answer
 * is slow or never comes (review round 4, F-16). The page shown is the one asked for, so Refresh after a
 * filter change asks for the first page.
 */
export type PlanningListView = {
  rows: ResourceRequirement[];
  offset: number;
  hasNextPage: boolean;
  loading: boolean;
  error: string;
};

export const INITIAL_PLANNING_LIST_VIEW: PlanningListView = { rows: [], offset: 0, hasNextPage: false, loading: false, error: "" };

export function planningListView(view: PlanningListView, update: PlanningListUpdate, pageSize: number): PlanningListView {
  switch (update.kind) {
    case "loading":
      return { rows: [], offset: update.offset, hasNextPage: false, loading: true, error: "" };
    case "rows":
      return {
        rows: update.rows.slice(0, pageSize),
        offset: update.offset,
        hasNextPage: update.rows.length > pageSize,
        loading: false,
        error: "",
      };
    case "failed":
      return { ...view, rows: [], hasNextPage: false, loading: false, error: update.message };
    case "signed-out":
      return { ...INITIAL_PLANNING_LIST_VIEW, error: SIGN_IN_FIRST };
    default:
      return view;
  }
}

/** Slice 7D Part 5: the shifts a day the Work Order states, as a phrase - none when it states no count (round 3). */
export function shiftsPerDayText(shiftsPerDay: number | null | undefined): string | null {
  if (shiftsPerDay == null) return null;
  return shiftsPerDay === 1 ? "1 shift a day" : `${shiftsPerDay} shifts a day`;
}
