// Pure rules for the Work Order line billing-terms section (Slice 7D Part 1), kept out of the
// components so they can be tested without a browser DOM - the frontend has no component-test
// capability yet. The backend re-checks every rule; these keep the form from offering or sending a
// term that does not apply to the chosen billing basis.

import { amountProblem, decimalDigits } from "../../components/amounts";

export type BillingTermPeriod = {
  term_public_id: string;
  period_number: number;
  effective_from: string | null;
  effective_to: string | null;
  term_revision: number;
  currency_code: string;
  billing_uom_code: string | null;
  contracted_hours_per_billing_unit: string | null;
  contracted_working_days_per_month: string | null;
  derived_hours_per_working_day: string | null;
  normal_rate_amount: string | null;
  weekly_off_day_codes: string[] | null;
  off_day_work_treatment_code: string | null;
  holiday_rate_method_code: string | null;
  holiday_rate_amount: string | null;
  holiday_rate_percent: string | null;
  overtime_rate_method_code: string | null;
  overtime_rate_amount: string | null;
  overtime_rate_percent: string | null;
  month_overtime_hours_basis_code: string | null;
  month_overtime_counting_code: string | null;
  breakdown_treatment_code: string | null;
  breakdown_rate_method_code: string | null;
  breakdown_rate_amount: string | null;
  breakdown_rate_percent: string | null;
  breakdown_offset_by_same_day_overtime: boolean;
  customer_idle_treatment_code: string | null;
  standby_rate_method_code: string | null;
  standby_rate_amount: string | null;
  standby_rate_percent: string | null;
  minimum_guarantee_code: string | null;
  minimum_billing_units_per_month: string | null;
  part_month_basis_code: string | null;
  // Part 5. The shift pattern belongs to the period; it took the place of Part 2's night shift. Where Part 2 had
  // recorded the night shift as "not in the Work Order", the migration kept that answer here (read only).
  legacy_night_shift_not_in_work_order?: boolean;
  shift_pattern_code: string | null;
  shift_1_hours: string | null;
  shift_2_hours: string | null;
  shift_3_hours: string | null;
  shift_rate_code: string | null;
  shift_2_rate_method_code: string | null;
  shift_2_rate_amount: string | null;
  shift_2_rate_percent: string | null;
  shift_2_working_days_per_month: string | null;
  shift_3_rate_method_code: string | null;
  shift_3_rate_amount: string | null;
  shift_3_rate_percent: string | null;
  shift_3_working_days_per_month: string | null;
  overtime_counted_per_code: string | null;
  // Part 2. Fuel belongs to the period; mobilisation and demobilisation are the line's and are held by
  // period 1 only (owner decision 8).
  mobilisation_charge_code: string | null;
  mobilisation_charge_amount: string | null;
  mobilisation_credit_after_months: number | null;
  demobilisation_charge_code: string | null;
  demobilisation_charge_amount: string | null;
  demobilisation_waived_after_months: number | null;
  fuel_treatment_code: string | null;
  fuel_charge_method_code: string | null;
  fuel_rate_per_litre_amount: string | null;
  fuel_litres_per_working_hour: string | null;
  fuel_travel_allowance_code: string | null;
  fuel_litres_per_travel_hour: string | null;
  // Part 4. Extra kilometres and crew belong to each period and apply to every billing basis.
  extra_km_allowance_code: string | null;
  extra_km_included_km: string | null;
  extra_km_rate_amount: string | null;
  crew_code: string | null;
  crew_operators_per_unit: number | null;
  crew_helpers_per_unit: number | null;
  extra_crew_charge_code: string | null;
  extra_crew_operator_rate_amount: string | null;
  extra_crew_helper_rate_amount: string | null;
  // Part 5. The crew's food, accommodation and travel: upkeep_<item>_<role>_<field> (see UPKEEP_CELLS).
  [upkeepColumn: UpkeepColumn]: string | null;
  term_notes: string | null;
  is_complete: boolean;
  missing_items: string[];
  updated_by_display_name?: string | null;
  updated_at?: string | null;
};

export type LineBillingTerms = {
  work_order_line_public_id: string;
  line_number: number;
  quoted_uom: string;
  quoted_rate_amount: string | null;
  current_period_number: number | null;
  periods: BillingTermPeriod[];
  terms_complete: boolean;
  line_missing_items: string[];
};

export const WEEKDAYS = [
  { code: "MON", label: "Mon" },
  { code: "TUE", label: "Tue" },
  { code: "WED", label: "Wed" },
  { code: "THU", label: "Thu" },
  { code: "FRI", label: "Fri" },
  { code: "SAT", label: "Sat" },
  { code: "SUN", label: "Sun" },
];

export const BILLING_BASIS_OPTIONS = [
  { code: "HOUR", label: "Hour" },
  { code: "SHIFT", label: "Shift" },
  { code: "DAY", label: "Day" },
  { code: "MONTH", label: "Month" },
];

export function billingBasisLabel(code: string | null | undefined): string | null {
  return BILLING_BASIS_OPTIONS.find((option) => option.code === code)?.label ?? null;
}

const MISSING_TERM_LABELS: Record<string, string> = {
  NO_TERMS: "no terms yet",
  BILLING_BASIS: "billing basis",
  CONTRACTED_HOURS: "contracted hours",
  CONTRACTED_WORKING_DAYS: "working days per month",
  NORMAL_RATE: "Work Order rate",
  WEEKLY_OFF_DAYS: "weekly off days",
  OFF_DAY_WORK: "off-day work",
  OVERTIME: "overtime",
  MONTH_OVERTIME_METHOD: "how overtime is counted",
  BREAKDOWN: "breakdown",
  IDLE_TIME: "idle time",
  MINIMUM_GUARANTEE: "minimum guarantee",
  PART_MONTH: "part month",
  SHIFTS: "shifts",
  MOBILISATION: "mobilisation",
  DEMOBILISATION: "demobilisation",
  FUEL: "fuel",
  EXTRA_KILOMETRES: "extra kilometres",
  CREW: "crew",
  CREW_UPKEEP: "crew food, accommodation and travel",
};

/** Every item a period can report missing, NO_TERMS included. */
export const MISSING_TERM_ITEMS: readonly string[] = Object.keys(MISSING_TERM_LABELS);

export function missingTermsText(entry: LineBillingTerms | undefined): string {
  if (!entry) return "Terms not loaded";
  if (entry.terms_complete) return "Terms complete";
  return `Terms missing: ${entry.line_missing_items.map((item) => MISSING_TERM_LABELS[item] ?? item).join(", ")}`;
}

/** Which groups of terms apply to a billing basis (WBT-001: hourly billing uses actual hours only). */
export function visibleTermGroups(basis: string) {
  const timeBased = ["SHIFT", "DAY", "MONTH"].includes(basis);
  const isMonth = basis === "MONTH";
  return {
    rate: basis !== "",
    contractedHours: timeBased,
    workingDays: isMonth,
    offDays: timeBased,
    overtime: timeBased,
    monthOvertime: isMonth,
    breakdown: timeBased,
    minimumGuarantee: ["HOUR", "SHIFT", "DAY"].includes(basis),
    partMonth: isMonth,
    // Part 5: shifts, as Part 2's night shift was, are not for an hourly line: it bills the hours it
    // worked, whenever they were worked. Fuel applies to every basis (owner decision 10).
    shifts: timeBased,
    shiftWorkingDays: isMonth,
    fuel: basis !== "",
    // Part 4: extra kilometres and crew apply to every basis; the crew are counted per billing unit.
    extraKm: basis !== "",
    crew: basis !== "",
  };
}

/**
 * Whether this period shows the mobilisation and demobilisation terms. They are recorded once for the
 * line, in its first period, and a later period neither copies nor changes them (owner decision 8).
 */
export function showsLineOnceTerms(periodNumber: number): boolean {
  return periodNumber === 1;
}

// Slice 7D.1: the form is laid out as cards, one per group of terms, gathered into three chapters in the
// order a Work Order reads - the rate, then working time, then the charges on top. Each card says
// whether its saved answers are complete, so a reader can find the gaps without reading every field.

export type TermGroupKey =
  | "basis"
  | "offDays"
  | "overtime"
  | "breakdown"
  | "idle"
  | "shifts"
  | "fuel"
  | "extraKm"
  | "crew"
  | "upkeep"
  | "lineOnce";

/** The missing items each group answers. Every item except NO_TERMS belongs to exactly one group. */
export const TERM_GROUP_MISSING_ITEMS: Record<TermGroupKey, readonly string[]> = {
  basis: ["BILLING_BASIS", "CONTRACTED_HOURS", "CONTRACTED_WORKING_DAYS", "NORMAL_RATE"],
  offDays: ["WEEKLY_OFF_DAYS", "OFF_DAY_WORK"],
  overtime: ["OVERTIME", "MONTH_OVERTIME_METHOD"],
  breakdown: ["BREAKDOWN"],
  idle: ["IDLE_TIME", "MINIMUM_GUARANTEE", "PART_MONTH"],
  shifts: ["SHIFTS"],
  fuel: ["FUEL"],
  extraKm: ["EXTRA_KILOMETRES"],
  crew: ["CREW"],
  upkeep: ["CREW_UPKEEP"],
  lineOnce: ["MOBILISATION", "DEMOBILISATION"],
};

export type TermChapterKey = "rate" | "workingTime" | "extraCharges";

export type TermChapter = {
  key: TermChapterKey;
  title: string;
  description: string;
  /** One of the app's shared tones, so the chapters read as part of the same page. */
  tone: "blue" | "teal" | "amber";
  groups: readonly TermGroupKey[];
};

export const TERM_CHAPTERS: readonly TermChapter[] = [
  { key: "rate", title: "The rate", description: "What the customer pays", tone: "blue", groups: ["basis"] },
  {
    key: "workingTime",
    title: "Working time",
    description: "How working, lost and idle hours are treated",
    tone: "teal",
    // Part 5: the shifts are working time - one rate for every shift is no extra charge.
    groups: ["offDays", "shifts", "overtime", "breakdown", "idle"],
  },
  {
    key: "extraCharges",
    title: "Extra charges",
    description: "Charges on top of the rate",
    tone: "amber",
    groups: ["fuel", "extraKm", "crew", "upkeep", "lineOnce"],
  },
];

/** A period's basis and Work Order rate as one short line, such as "Month - INR 100000.00". */
export function periodSummary(period: { billing_uom_code: string | null; normal_rate_amount: string | null } | undefined): string {
  if (!period) return "";
  return [billingBasisLabel(period.billing_uom_code), period.normal_rate_amount ? `INR ${period.normal_rate_amount}` : null]
    .filter((fact): fact is string => Boolean(fact))
    .join(" - ");
}

/**
 * Whether a period is shown open (Slice 7D.1). Until the user opens, closes or edits it (`userOpen`
 * null), the latest period is open - a change goes into it, and a new period copies it - and an earlier
 * period is open only while it still has missing items, so a line with several dated periods does not
 * stack every full form on top of the next. After that the user's choice holds.
 */
export function periodOpen(userOpen: boolean | null, period: { missing_items: readonly string[] }, isLatest: boolean): boolean {
  return userOpen ?? (isLatest || period.missing_items.length > 0);
}

/**
 * The groups a period shows for a billing basis, in form order. Mirrors the per-field rules above. The
 * crew's upkeep is shown once the Work Order states its crew (Part 5, assumption A4).
 */
export function visibleTermGroupKeys(basis: string, periodNumber: number, crewCode = ""): TermGroupKey[] {
  const groups = visibleTermGroups(basis);
  const shown: Record<TermGroupKey, boolean> = {
    basis: true,
    offDays: groups.offDays,
    shifts: groups.shifts,
    overtime: groups.overtime,
    breakdown: groups.breakdown,
    idle: groups.rate,
    fuel: groups.fuel,
    extraKm: groups.extraKm,
    crew: groups.crew,
    upkeep: groups.crew && crewCode === CREW_STATED,
    lineOnce: groups.fuel && showsLineOnceTerms(periodNumber),
  };
  return TERM_CHAPTERS.flatMap((chapter) => chapter.groups).filter((key) => shown[key]);
}

/** The chapters that have something to show, each carrying only its visible groups. */
export function visibleTermChapters(basis: string, periodNumber: number, crewCode = ""): TermChapter[] {
  const shown = new Set(visibleTermGroupKeys(basis, periodNumber, crewCode));
  return TERM_CHAPTERS.map((chapter) => ({ ...chapter, groups: chapter.groups.filter((key) => shown.has(key)) })).filter(
    (chapter) => chapter.groups.length > 0,
  );
}

/**
 * A group's tag: "missing" while any item it answers is reported missing, otherwise "answered". The
 * report describes the period as last saved, so no tag is shown while the form's billing basis differs
 * from the saved one - the groups on screen then belong to a basis the report never assessed, and
 * "Answered" over empty fields would be untrue.
 */
export function termGroupStatus(
  group: TermGroupKey,
  period: { billing_uom_code: string | null; missing_items: readonly string[] },
  formBasis: string,
): "answered" | "missing" | null {
  if ((period.billing_uom_code ?? "") !== formBasis) return null;
  return TERM_GROUP_MISSING_ITEMS[group].some((item) => period.missing_items.includes(item)) ? "missing" : "answered";
}

/** A date-only value ("2027-03-01") as "1 March 2027", without any time-zone shift. */
export function formatTermDate(isoDate: string): string {
  const [year, month, day] = isoDate.split("-").map(Number);
  return new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" }).format(
    new Date(Date.UTC(year, month - 1, day)),
  );
}

/**
 * Whether the read-only view shows the two monthly overtime rows. Both are shown whenever overtime is
 * charged on a monthly line, each with "-" when not chosen, so a one-sided incomplete choice is still
 * visible (review round 3).
 */
export function showsMonthOvertimeRows(period: { billing_uom_code: string | null; overtime_rate_method_code: string | null }): boolean {
  return period.billing_uom_code === "MONTH" && ["RATE_PER_HOUR", "PERCENT_OF_NORMAL"].includes(period.overtime_rate_method_code ?? "");
}

/**
 * "From contract start" for period 1, otherwise the date the period starts, and its end if known.
 *
 * Once the Work Order's contract start date is recorded, period 1 stops saying "From contract start"
 * and shows that date instead (Slice 7D Part 3, owner decision 17). Until then it cannot: the date is
 * genuinely not known, and naming a date that has not been recorded would be a guess.
 */
export function periodLabel(
  period: { period_number: number; effective_from: string | null; effective_to?: string | null },
  contractStartDate?: string | null,
): string {
  const startsWithContract = period.period_number === 1 || !period.effective_from;
  const start = startsWithContract
    ? contractStartDate
      ? `From ${formatTermDate(contractStartDate)}`
      : "From contract start"
    : `From ${formatTermDate(period.effective_from as string)}`;
  return period.effective_to ? `${start} to ${formatTermDate(period.effective_to)}` : start;
}

// A rate is one choice of how it is given plus the value that choice asks for.
export type RateForm = { method: string; value: string };

export type TermsForm = {
  effective_from: string;
  billing_uom_code: string;
  contracted_hours_per_billing_unit: string;
  contracted_working_days_per_month: string;
  normal_rate_amount: string;
  // Unticked means the off days are not recorded yet; ticked with no day chosen is a 7-day week.
  off_days_recorded: boolean;
  weekly_off_day_codes: string[];
  off_day_work_treatment_code: string;
  holiday_rate: RateForm;
  overtime_rate: RateForm;
  month_overtime_hours_basis_code: string;
  month_overtime_counting_code: string;
  breakdown_treatment_code: string;
  breakdown_rate: RateForm;
  breakdown_offset_by_same_day_overtime: boolean;
  customer_idle_treatment_code: string;
  standby_rate: RateForm;
  minimum_guarantee_code: string;
  minimum_billing_units_per_month: string;
  part_month_basis_code: string;
  // Part 5: the shift pattern. A later shift's rate may also be per shift, one more choice than the others.
  shift_pattern_code: string;
  shift_1_hours: string;
  shift_2_hours: string;
  shift_3_hours: string;
  shift_rate_code: string;
  shift_2_rate: RateForm;
  shift_2_working_days_per_month: string;
  shift_3_rate: RateForm;
  shift_3_working_days_per_month: string;
  overtime_counted_per_code: string;
  mobilisation_charge_code: string;
  mobilisation_charge_amount: string;
  mobilisation_credit_after_months: string;
  demobilisation_charge_code: string;
  demobilisation_charge_amount: string;
  demobilisation_waived_after_months: string;
  fuel_treatment_code: string;
  fuel_charge_method_code: string;
  fuel_rate_per_litre_amount: string;
  fuel_litres_per_working_hour: string;
  fuel_travel_allowance_code: string;
  fuel_litres_per_travel_hour: string;
  extra_km_allowance_code: string;
  extra_km_included_km: string;
  extra_km_rate_amount: string;
  crew_code: string;
  crew_operators_per_unit: string;
  crew_helpers_per_unit: string;
  extra_crew_charge_code: string;
  extra_crew_operator_rate_amount: string;
  extra_crew_helper_rate_amount: string;
  // Part 5: one entry per upkeep cell, keyed "<item>_<role>" (UPKEEP_CELLS).
  upkeep: Record<string, UpkeepCellForm>;
  term_notes: string;
};

// Part 5 (owner's answers of 9 October 2026). The shift pattern: "not in the Work Order" states no shifts; one,
// two or three shifts each state their hours in a day; two or three are charged at one rate for every shift or
// each later shift at its own rate - per shift, per hour or a percentage of the Work Order rate, as Part 2's
// night shift was ("% of normal", owner decision 7).
export const SHIFT_PATTERNS_SEVERAL = ["TWO_SHIFTS", "THREE_SHIFTS"];
export const SHIFT_RATE_PER_SHIFT = "PER_SHIFT";
export const SHIFT_RATE_METHOD_PER_SHIFT = "RATE_PER_SHIFT";
/** The later-shift rate methods whose value is an amount rather than a percentage. */
export const SHIFT_RATE_AMOUNT_METHODS = [SHIFT_RATE_METHOD_PER_SHIFT, "RATE_PER_HOUR"];
/**
 * The kept Part 2 answer, as the screen shows it beside the shift question (review round 4): the migration asked for
 * the shift pattern again because "night shift not in the Work Order" does not say how many shifts there are.
 */
export function legacyNightShiftNote(period: Pick<BillingTermPeriod, "legacy_night_shift_not_in_work_order"> | undefined): string | null {
  return period?.legacy_night_shift_not_in_work_order
    ? "Recorded before 10 October 2026: the night shift was not in the Work Order. That does not say how many shifts the Work Order states, so choose them from the Work Order."
    : null;
}

/** How many shifts a day a pattern states: none for "not in the Work Order" or no answer (review round 2). */
export function shiftsPerDay(pattern: string | null | undefined): number {
  return pattern === "THREE_SHIFTS" ? 3 : pattern === "TWO_SHIFTS" ? 2 : pattern === "ONE_SHIFT" ? 1 : 0;
}

// The crew's food, accommodation and travel, for operators and helpers separately, once the Work Order
// states its crew. Each is not in the Work Order, provided by the customer, or provided at a cost that the
// customer deducts from PBL's invoice or bills PBL for. Every cost states its basis, so none is assumed (review
// round 1, 7D5-R1-003): food and accommodation per person per day or per month; travel to and from the job per
// person per trip or per trip; daily travel per person per day or per day. Mirrors WORK_ORDER_LINE_UPKEEP_CELLS.
export const UPKEEP_AT_COST = "PROVIDED_AT_COST";
export type UpkeepCellForm = { code: string; amount: string; unit: string; recovery: string };
type Choice = { code: string; label: string };
export type UpkeepItem = { key: string; label: string; units: readonly Choice[] };
export type UpkeepRole = { key: string; label: string; countField: "crew_operators_per_unit" | "crew_helpers_per_unit" };
const PER_PERSON_PER_DAY = { code: "PER_PERSON_PER_DAY", label: "per person per day" };
const PER_PERSON_PER_MONTH = { code: "PER_PERSON_PER_MONTH", label: "per person per month" };
export const UPKEEP_ITEMS: readonly UpkeepItem[] = [
  { key: "food", label: "Food", units: [PER_PERSON_PER_DAY, PER_PERSON_PER_MONTH] },
  { key: "accommodation", label: "Accommodation", units: [PER_PERSON_PER_DAY, PER_PERSON_PER_MONTH] },
  {
    key: "job_travel",
    label: "Travel to and from the job",
    units: [
      { code: "PER_PERSON_PER_TRIP", label: "per person per trip" },
      { code: "PER_TRIP", label: "per trip, whatever the number of people" },
    ],
  },
  {
    key: "daily_travel",
    label: "Daily travel to site",
    units: [PER_PERSON_PER_DAY, { code: "PER_DAY", label: "per day, whatever the number of people" }],
  },
];
export const UPKEEP_ROLES: readonly UpkeepRole[] = [
  { key: "operator", label: "Operators", countField: "crew_operators_per_unit" },
  { key: "helper", label: "Helpers", countField: "crew_helpers_per_unit" },
];
export type UpkeepColumn = `upkeep_${string}`;
export type UpkeepCell = { key: string; item: UpkeepItem; role: UpkeepRole; column: (field: "code" | "amount" | "unit_code" | "recovery_code") => UpkeepColumn };
export const UPKEEP_CELLS: readonly UpkeepCell[] = UPKEEP_ITEMS.flatMap((item) =>
  UPKEEP_ROLES.map((role) => ({
    key: `${item.key}_${role.key}`,
    item,
    role,
    column: (field: "code" | "amount" | "unit_code" | "recovery_code"): UpkeepColumn => `upkeep_${item.key}_${role.key}_${field}`,
  })),
);
export const MOBILISATION_CHARGED_CODES = ["CHARGED", "CHARGED_CREDITED_AFTER_MONTHS"];
export const DEMOBILISATION_CHARGED_CODES = ["CHARGED", "CHARGED_WAIVED_AFTER_MONTHS"];
export const FUEL_PBL_CHARGED = "PBL_SUPPLIED_CHARGED";
export const FUEL_CUSTOMER_SUPPLIED = "CUSTOMER_SUPPLIED";
export const FUEL_AGREED_RATE_PER_LITRE = "AGREED_RATE_PER_LITRE";
export const FUEL_TRAVEL_LITRES_PER_HOUR = "LITRES_PER_TRAVEL_HOUR";
// Part 4 (owner answers 22 and 23, decision 28).
export const EXTRA_KM_INCLUDED_CODES = ["KM_PER_DAY", "KM_PER_MONTH"];
export const CREW_STATED = "STATED";
export const EXTRA_CREW_RATE_PER_PERSON = "RATE_PER_PERSON";

const text = (value: string | number | null | undefined): string => (value == null ? "" : String(value));

function rateFromPeriod(method: string | null, amount: string | null, percent: string | null): RateForm {
  return { method: text(method), value: method === "PERCENT_OF_NORMAL" ? text(percent) : text(amount) };
}

export function formFromPeriod(period: BillingTermPeriod | undefined): TermsForm {
  return {
    effective_from: text(period?.effective_from),
    billing_uom_code: text(period?.billing_uom_code),
    contracted_hours_per_billing_unit: text(period?.contracted_hours_per_billing_unit),
    contracted_working_days_per_month: text(period?.contracted_working_days_per_month),
    normal_rate_amount: text(period?.normal_rate_amount),
    off_days_recorded: period?.weekly_off_day_codes != null,
    weekly_off_day_codes: period?.weekly_off_day_codes ?? [],
    off_day_work_treatment_code: text(period?.off_day_work_treatment_code),
    holiday_rate: rateFromPeriod(period?.holiday_rate_method_code ?? null, period?.holiday_rate_amount ?? null, period?.holiday_rate_percent ?? null),
    overtime_rate: rateFromPeriod(period?.overtime_rate_method_code ?? null, period?.overtime_rate_amount ?? null, period?.overtime_rate_percent ?? null),
    month_overtime_hours_basis_code: text(period?.month_overtime_hours_basis_code),
    month_overtime_counting_code: text(period?.month_overtime_counting_code),
    breakdown_treatment_code: text(period?.breakdown_treatment_code),
    breakdown_rate: rateFromPeriod(period?.breakdown_rate_method_code ?? null, period?.breakdown_rate_amount ?? null, period?.breakdown_rate_percent ?? null),
    breakdown_offset_by_same_day_overtime: period?.breakdown_offset_by_same_day_overtime ?? false,
    customer_idle_treatment_code: text(period?.customer_idle_treatment_code),
    standby_rate: rateFromPeriod(period?.standby_rate_method_code ?? null, period?.standby_rate_amount ?? null, period?.standby_rate_percent ?? null),
    minimum_guarantee_code: text(period?.minimum_guarantee_code),
    minimum_billing_units_per_month: text(period?.minimum_billing_units_per_month),
    part_month_basis_code: text(period?.part_month_basis_code),
    shift_pattern_code: text(period?.shift_pattern_code),
    shift_1_hours: text(period?.shift_1_hours),
    shift_2_hours: text(period?.shift_2_hours),
    shift_3_hours: text(period?.shift_3_hours),
    shift_rate_code: text(period?.shift_rate_code),
    shift_2_rate: rateFromPeriod(period?.shift_2_rate_method_code ?? null, period?.shift_2_rate_amount ?? null, period?.shift_2_rate_percent ?? null),
    shift_2_working_days_per_month: text(period?.shift_2_working_days_per_month),
    shift_3_rate: rateFromPeriod(period?.shift_3_rate_method_code ?? null, period?.shift_3_rate_amount ?? null, period?.shift_3_rate_percent ?? null),
    shift_3_working_days_per_month: text(period?.shift_3_working_days_per_month),
    overtime_counted_per_code: text(period?.overtime_counted_per_code),
    mobilisation_charge_code: text(period?.mobilisation_charge_code),
    mobilisation_charge_amount: text(period?.mobilisation_charge_amount),
    mobilisation_credit_after_months: text(period?.mobilisation_credit_after_months),
    demobilisation_charge_code: text(period?.demobilisation_charge_code),
    demobilisation_charge_amount: text(period?.demobilisation_charge_amount),
    demobilisation_waived_after_months: text(period?.demobilisation_waived_after_months),
    fuel_treatment_code: text(period?.fuel_treatment_code),
    fuel_charge_method_code: text(period?.fuel_charge_method_code),
    fuel_rate_per_litre_amount: text(period?.fuel_rate_per_litre_amount),
    fuel_litres_per_working_hour: text(period?.fuel_litres_per_working_hour),
    fuel_travel_allowance_code: text(period?.fuel_travel_allowance_code),
    fuel_litres_per_travel_hour: text(period?.fuel_litres_per_travel_hour),
    extra_km_allowance_code: text(period?.extra_km_allowance_code),
    extra_km_included_km: text(period?.extra_km_included_km),
    extra_km_rate_amount: text(period?.extra_km_rate_amount),
    crew_code: text(period?.crew_code),
    crew_operators_per_unit: text(period?.crew_operators_per_unit),
    crew_helpers_per_unit: text(period?.crew_helpers_per_unit),
    extra_crew_charge_code: text(period?.extra_crew_charge_code),
    extra_crew_operator_rate_amount: text(period?.extra_crew_operator_rate_amount),
    extra_crew_helper_rate_amount: text(period?.extra_crew_helper_rate_amount),
    upkeep: Object.fromEntries(
      UPKEEP_CELLS.map((cell) => [
        cell.key,
        {
          code: text(period?.[cell.column("code")]),
          amount: text(period?.[cell.column("amount")]),
          unit: text(period?.[cell.column("unit_code")]),
          recovery: text(period?.[cell.column("recovery_code")]),
        },
      ]),
    ),
    term_notes: text(period?.term_notes),
  };
}

/** Whether a role's upkeep is asked: the crew is stated and the Work Order does not state 0 of them (A4, A5). */
export function upkeepRoleApplies(form: Pick<TermsForm, "billing_uom_code" | "crew_code" | "crew_operators_per_unit" | "crew_helpers_per_unit">, role: UpkeepRole): boolean {
  if (!visibleTermGroups(form.billing_uom_code).crew || form.crew_code !== CREW_STATED) return false;
  const count = form[role.countField].trim();
  return !(/^\d+$/.test(count) && Number(count) === 0);
}

/** The upkeep choices, units and recoveries, as the form offers them and the read-only view shows them. */
export const UPKEEP_CHOICES = [
  { code: "NONE", label: "Not in the Work Order" },
  { code: "PROVIDED", label: "Provided by the customer" },
  { code: UPKEEP_AT_COST, label: "Provided by the customer at a cost" },
];
export const UPKEEP_RECOVERIES = [
  { code: "DEDUCTED_FROM_INVOICE", label: "Deducted from PBL's invoice" },
  { code: "BILLED_SEPARATELY", label: "Billed to PBL separately by the customer" },
];

/** A saved period's crew numbers in the form's shape, so the same rules decide what it shows. */
export function crewOfPeriod(period: BillingTermPeriod): Pick<TermsForm, "billing_uom_code" | "crew_code" | "crew_operators_per_unit" | "crew_helpers_per_unit"> {
  return {
    billing_uom_code: text(period.billing_uom_code),
    crew_code: text(period.crew_code),
    crew_operators_per_unit: text(period.crew_operators_per_unit),
    crew_helpers_per_unit: text(period.crew_helpers_per_unit),
  };
}

/** One saved upkeep answer as a line of text, such as "INR 150.00 per person per day; deducted from PBL's invoice". */
export function upkeepAnswerText(cell: UpkeepCell, period: BillingTermPeriod): string {
  const code = period[cell.column("code")];
  if (code !== UPKEEP_AT_COST) return UPKEEP_CHOICES.find((choice) => choice.code === code)?.label ?? "-";
  const amount = period[cell.column("amount")];
  const unit = cell.item.units.find((choice) => choice.code === period[cell.column("unit_code")])?.label ?? "-";
  const recovery = UPKEEP_RECOVERIES.find((choice) => choice.code === period[cell.column("recovery_code")])?.label ?? "-";
  return `${amount ? `INR ${amount}` : "-"} ${unit}; ${recovery.charAt(0).toLowerCase()}${recovery.slice(1)}`;
}

/** "Same as for operators": the helpers' answers become a copy of the operators', item by item. */
export function upkeepWithHelpersAsOperators(upkeep: Record<string, UpkeepCellForm>): Record<string, UpkeepCellForm> {
  const next = { ...upkeep };
  for (const item of UPKEEP_ITEMS) {
    next[`${item.key}_helper`] = { ...upkeep[`${item.key}_operator`] };
  }
  return next;
}

/**
 * Whether "Overtime is counted per shift or for the whole day" is asked (Part 5, A12): wherever overtime is
 * charged on two or three shifts - a monthly line counted over the whole month included (review round 1,
 * 7D5-R1-001).
 */
export function asksOvertimeCountedPer(form: Pick<TermsForm, "billing_uom_code" | "overtime_rate" | "shift_pattern_code">): boolean {
  const groups = visibleTermGroups(form.billing_uom_code);
  return groups.overtime && CHARGED.includes(form.overtime_rate.method) && SHIFT_PATTERNS_SEVERAL.includes(form.shift_pattern_code);
}

const orNull = (value: string): string | null => (value.trim().length > 0 ? value.trim() : null);

/** The largest number of people the database can record: its integer column's own range. */
export const CREW_COUNT_MAX = 2_147_483_647;

// Digits allowed before the decimal point, mirroring the server's limits: kilometres are numeric(9,2), and
// every rate numeric(18,2). Both allow 2 decimal places; the server ignores leading and trailing zeros.
const KM_WHOLE_DIGITS = 7;
const RATE_WHOLE_DIGITS = 16;
// Part 5: a shift's hours are numeric(4,2), a percentage numeric(7,2), working days numeric(5,2).
const SHIFT_HOURS_WHOLE_DIGITS = 2;
const PERCENT_WHOLE_DIGITS = 5;
const DAYS_WHOLE_DIGITS = 3;

// Kept here for the pages and tests that import them from this module; they live in components/amounts.ts.
export { amountProblem, decimalDigits };

/**
 * What stops a period's terms being sent, in words that name the field, or null. It covers every Part 4
 * number that would be sent: the server refuses a malformed number with a message that reaches the screen
 * only as "Check the values entered" (review round 1, finding F-02, for the crew numbers; round 2, finding
 * F-06, for the four amounts). A field that would not be sent is not checked.
 */
export function termsFormProblem(form: TermsForm): string | null {
  const groups = visibleTermGroups(form.billing_uom_code);
  const unit = billingBasisLabel(form.billing_uom_code)?.toLowerCase() ?? "billing unit";
  const shiftProblem = shiftsFormProblem(form);
  if (shiftProblem) return shiftProblem;
  const upkeepProblem = upkeepFormProblem(form);
  if (upkeepProblem) return upkeepProblem;
  if (groups.extraKm && EXTRA_KM_INCLUDED_CODES.includes(form.extra_km_allowance_code)) {
    const perWhat = form.extra_km_allowance_code === "KM_PER_MONTH" ? "month" : "day";
    const problem =
      amountProblem(`Kilometres included per ${perWhat}`, form.extra_km_included_km, KM_WHOLE_DIGITS) ??
      amountProblem("Rate per extra kilometre", form.extra_km_rate_amount, RATE_WHOLE_DIGITS);
    if (problem) return problem;
  }
  if (!groups.crew || form.crew_code !== CREW_STATED) return null;
  const counts: [string, string][] = [
    [`Operators per ${unit}`, form.crew_operators_per_unit],
    [`Helpers per ${unit}`, form.crew_helpers_per_unit],
  ];
  for (const [label, value] of counts) {
    const trimmed = value.trim();
    if (trimmed === "") continue;
    if (!/^\d+$/.test(trimmed)) return `${label} must be a whole number, 0 or more.`;
    if (Number(trimmed) > CREW_COUNT_MAX) return `${label} is larger than can be recorded.`;
  }
  if (form.extra_crew_charge_code === EXTRA_CREW_RATE_PER_PERSON) {
    return (
      amountProblem(`Each extra operator, per ${unit}`, form.extra_crew_operator_rate_amount, RATE_WHOLE_DIGITS) ??
      amountProblem(`Each extra helper, per ${unit}`, form.extra_crew_helper_rate_amount, RATE_WHOLE_DIGITS)
    );
  }
  return null;
}

/** Part 5: each shift number that would be sent, held to the server's limits, and the day's 24 hours. */
function shiftsFormProblem(form: TermsForm): string | null {
  const shifts = visibleTermGroups(form.billing_uom_code).shifts ? shiftsPerDay(form.shift_pattern_code) : 0;
  if (shifts === 0) return null;
  let total = 0;
  for (let shift = 1; shift <= shifts; shift += 1) {
    const value = form[`shift_${shift}_hours` as "shift_1_hours"];
    const problem = amountProblem(`Shift ${shift} hours`, value, SHIFT_HOURS_WHOLE_DIGITS);
    if (problem) return problem;
    total += value.trim() === "" ? 0 : Number(value);
  }
  if (total > 24) return `The shifts add up to ${Number(total.toFixed(2))} hours, more than the 24 hours in a day.`;
  if (shifts < 2 || form.shift_rate_code !== SHIFT_RATE_PER_SHIFT) return null;
  for (let shift = 2; shift <= shifts; shift += 1) {
    const rate = form[`shift_${shift}_rate` as "shift_2_rate"];
    const problem =
      rate.method === "PERCENT_OF_NORMAL"
        ? amountProblem(`Shift ${shift}'s percentage`, rate.value, PERCENT_WHOLE_DIGITS)
        : rate.method
          ? amountProblem(`Shift ${shift}'s rate`, rate.value, RATE_WHOLE_DIGITS)
          : null;
    if (problem) return problem;
    if (form.billing_uom_code === "MONTH") {
      const days = amountProblem(`Shift ${shift}'s working days per month`, form[`shift_${shift}_working_days_per_month` as "shift_2_working_days_per_month"], DAYS_WHOLE_DIGITS);
      if (days) return days;
    }
  }
  return null;
}

/** Part 5: each upkeep cost that would be sent, held to the server's limits. */
function upkeepFormProblem(form: TermsForm): string | null {
  for (const cell of UPKEEP_CELLS) {
    const answer = form.upkeep[cell.key];
    if (!upkeepRoleApplies(form, cell.role) || answer?.code !== UPKEEP_AT_COST) continue;
    const problem = amountProblem(`${cell.item.label} for ${cell.role.label.toLowerCase()}`, answer.amount, RATE_WHOLE_DIGITS);
    if (problem) return problem;
  }
  return null;
}

/**
 * A count of people as the request sends it: a whole number, or null when not entered or not applicable.
 * Anything that is not a whole number is sent as typed rather than quietly rounded; termsFormProblem
 * stops such a value being sent at all, so this is only the backstop behind it.
 */
export function wholeNumberOrNull(applies: boolean, value: string): number | string | null {
  if (!applies) return null;
  const trimmed = value.trim();
  if (trimmed === "") return null;
  return /^\d+$/.test(trimmed) ? Number(trimmed) : trimmed;
}
const CHARGED = ["RATE_PER_HOUR", "PERCENT_OF_NORMAL"];

function ratePayload(prefix: string, rate: RateForm, applies: boolean): Record<string, string | null> {
  const method = applies ? orNull(rate.method) : null;
  return {
    [`${prefix}_method_code`]: method,
    [`${prefix}_amount`]: method === "RATE_PER_HOUR" ? orNull(rate.value) : null,
    [`${prefix}_percent`]: method === "PERCENT_OF_NORMAL" ? orNull(rate.value) : null,
  };
}

/** A later shift's rate: an amount for a rate per shift or per hour, a percentage otherwise. */
function laterShiftRatePayload(shift: number, rate: RateForm, applies: boolean): Record<string, string | null> {
  const method = applies ? orNull(rate.method) : null;
  return {
    [`shift_${shift}_rate_method_code`]: method,
    [`shift_${shift}_rate_amount`]: method !== null && SHIFT_RATE_AMOUNT_METHODS.includes(method) ? orNull(rate.value) : null,
    [`shift_${shift}_rate_percent`]: method === "PERCENT_OF_NORMAL" ? orNull(rate.value) : null,
  };
}

/** Every upkeep cell's columns, each sent only where its role applies and its choice asks for it. */
function upkeepPayload(form: TermsForm): Record<string, string | null> {
  const payload: Record<string, string | null> = {};
  for (const cell of UPKEEP_CELLS) {
    const applies = upkeepRoleApplies(form, cell.role);
    const answer = form.upkeep[cell.key] ?? { code: "", amount: "", unit: "", recovery: "" };
    const atCost = applies && answer.code === UPKEEP_AT_COST;
    payload[cell.column("code")] = applies ? orNull(answer.code) : null;
    payload[cell.column("amount")] = atCost ? orNull(answer.amount) : null;
    payload[cell.column("unit_code")] = atCost ? orNull(answer.unit) : null;
    payload[cell.column("recovery_code")] = atCost ? orNull(answer.recovery) : null;
  }
  return payload;
}

/**
 * The request's term fields. A term that does not apply to the chosen basis, to this period, or whose
 * parent choice does not ask for it, is sent empty - a value left in a hidden field is never sent.
 */
export function termsPayloadFromForm(form: TermsForm, periodNumber: number): Record<string, unknown> {
  const groups = visibleTermGroups(form.billing_uom_code);
  const lineOnce = showsLineOnceTerms(periodNumber);
  const shiftCount = groups.shifts ? shiftsPerDay(form.shift_pattern_code) : 0;
  const severalShifts = shiftCount >= 2;
  const threeShifts = shiftCount === 3;
  const ratePerShift = severalShifts && form.shift_rate_code === SHIFT_RATE_PER_SHIFT;
  const basisChosen = form.billing_uom_code !== "";
  const fuelApplies = groups.fuel;
  const kmIncluded = groups.extraKm && EXTRA_KM_INCLUDED_CODES.includes(form.extra_km_allowance_code);
  const crewStated = groups.crew && form.crew_code === CREW_STATED;
  const extraCrewCharged = crewStated && form.extra_crew_charge_code === EXTRA_CREW_RATE_PER_PERSON;
  const overtimeCharged = groups.overtime && CHARGED.includes(form.overtime_rate.method);
  const breakdownDeducts = groups.breakdown && ["REDUCE_BILLED_HOURS", "DEDUCT_AT_BREAKDOWN_RATE"].includes(form.breakdown_treatment_code);
  const when = (applies: boolean, value: string) => (applies ? orNull(value) : null);
  return {
    effective_from: orNull(form.effective_from),
    billing_uom_code: orNull(form.billing_uom_code),
    contracted_hours_per_billing_unit: when(groups.contractedHours, form.contracted_hours_per_billing_unit),
    contracted_working_days_per_month: when(groups.workingDays, form.contracted_working_days_per_month),
    normal_rate_amount: when(groups.rate, form.normal_rate_amount),
    weekly_off_day_codes: groups.offDays && form.off_days_recorded ? WEEKDAYS.map((day) => day.code).filter((code) => form.weekly_off_day_codes.includes(code)) : null,
    off_day_work_treatment_code: when(groups.offDays, form.off_day_work_treatment_code),
    ...ratePayload("holiday_rate", form.holiday_rate, groups.offDays && form.off_day_work_treatment_code === "HOLIDAY_RATE"),
    ...ratePayload("overtime_rate", form.overtime_rate, groups.overtime),
    month_overtime_hours_basis_code: when(groups.monthOvertime && overtimeCharged, form.month_overtime_hours_basis_code),
    month_overtime_counting_code: when(groups.monthOvertime && overtimeCharged, form.month_overtime_counting_code),
    breakdown_treatment_code: when(groups.breakdown, form.breakdown_treatment_code),
    ...ratePayload("breakdown_rate", form.breakdown_rate, groups.breakdown && form.breakdown_treatment_code === "DEDUCT_AT_BREAKDOWN_RATE"),
    breakdown_offset_by_same_day_overtime: breakdownDeducts && overtimeCharged && form.breakdown_offset_by_same_day_overtime,
    // Idle time is a term like the others: nothing is sent before a basis is chosen (review round 1).
    customer_idle_treatment_code: when(groups.rate, form.customer_idle_treatment_code),
    ...ratePayload("standby_rate", form.standby_rate, groups.rate && form.customer_idle_treatment_code === "STANDBY_RATE"),
    minimum_guarantee_code: when(groups.minimumGuarantee, form.minimum_guarantee_code),
    minimum_billing_units_per_month: when(groups.minimumGuarantee && form.minimum_guarantee_code === "UNITS_PER_MONTH", form.minimum_billing_units_per_month),
    part_month_basis_code: when(groups.partMonth, form.part_month_basis_code),
    shift_pattern_code: when(groups.shifts, form.shift_pattern_code),
    shift_1_hours: when(shiftCount >= 1, form.shift_1_hours),
    shift_2_hours: when(severalShifts, form.shift_2_hours),
    shift_3_hours: when(threeShifts, form.shift_3_hours),
    shift_rate_code: when(severalShifts, form.shift_rate_code),
    ...laterShiftRatePayload(2, form.shift_2_rate, ratePerShift),
    shift_2_working_days_per_month: when(ratePerShift && groups.shiftWorkingDays, form.shift_2_working_days_per_month),
    ...laterShiftRatePayload(3, form.shift_3_rate, ratePerShift && threeShifts),
    shift_3_working_days_per_month: when(ratePerShift && threeShifts && groups.shiftWorkingDays, form.shift_3_working_days_per_month),
    overtime_counted_per_code: when(asksOvertimeCountedPer(form), form.overtime_counted_per_code),
    mobilisation_charge_code: when(lineOnce && basisChosen, form.mobilisation_charge_code),
    mobilisation_charge_amount: when(
      lineOnce && basisChosen && MOBILISATION_CHARGED_CODES.includes(form.mobilisation_charge_code),
      form.mobilisation_charge_amount,
    ),
    mobilisation_credit_after_months: when(
      lineOnce && basisChosen && form.mobilisation_charge_code === "CHARGED_CREDITED_AFTER_MONTHS",
      form.mobilisation_credit_after_months,
    ),
    demobilisation_charge_code: when(lineOnce && basisChosen, form.demobilisation_charge_code),
    demobilisation_charge_amount: when(
      lineOnce && basisChosen && DEMOBILISATION_CHARGED_CODES.includes(form.demobilisation_charge_code),
      form.demobilisation_charge_amount,
    ),
    demobilisation_waived_after_months: when(
      lineOnce && basisChosen && form.demobilisation_charge_code === "CHARGED_WAIVED_AFTER_MONTHS",
      form.demobilisation_waived_after_months,
    ),
    fuel_treatment_code: when(fuelApplies, form.fuel_treatment_code),
    fuel_charge_method_code: when(fuelApplies && form.fuel_treatment_code === FUEL_PBL_CHARGED, form.fuel_charge_method_code),
    fuel_rate_per_litre_amount: when(
      fuelApplies && form.fuel_treatment_code === FUEL_PBL_CHARGED && form.fuel_charge_method_code === FUEL_AGREED_RATE_PER_LITRE,
      form.fuel_rate_per_litre_amount,
    ),
    fuel_litres_per_working_hour: when(fuelApplies && form.fuel_treatment_code === FUEL_CUSTOMER_SUPPLIED, form.fuel_litres_per_working_hour),
    fuel_travel_allowance_code: when(fuelApplies && form.fuel_treatment_code === FUEL_CUSTOMER_SUPPLIED, form.fuel_travel_allowance_code),
    fuel_litres_per_travel_hour: when(
      fuelApplies && form.fuel_treatment_code === FUEL_CUSTOMER_SUPPLIED && form.fuel_travel_allowance_code === FUEL_TRAVEL_LITRES_PER_HOUR,
      form.fuel_litres_per_travel_hour,
    ),
    extra_km_allowance_code: when(groups.extraKm, form.extra_km_allowance_code),
    extra_km_included_km: when(kmIncluded, form.extra_km_included_km),
    extra_km_rate_amount: when(kmIncluded, form.extra_km_rate_amount),
    crew_code: when(groups.crew, form.crew_code),
    // Whole numbers of people. Zero is a real answer ("no helpers"), so it is sent as zero, never dropped.
    crew_operators_per_unit: wholeNumberOrNull(crewStated, form.crew_operators_per_unit),
    crew_helpers_per_unit: wholeNumberOrNull(crewStated, form.crew_helpers_per_unit),
    extra_crew_charge_code: when(crewStated, form.extra_crew_charge_code),
    extra_crew_operator_rate_amount: when(extraCrewCharged, form.extra_crew_operator_rate_amount),
    extra_crew_helper_rate_amount: when(extraCrewCharged, form.extra_crew_helper_rate_amount),
    ...upkeepPayload(form),
    term_notes: orNull(form.term_notes),
  };
}

/**
 * Starting values for "Add a later period": the latest period's terms, with no start date yet, and
 * without mobilisation or demobilisation - those belong to the line's first period alone, so a later
 * period neither copies nor sends them (owner decision 8).
 */
export function formForNewPeriod(latest: BillingTermPeriod | undefined): TermsForm {
  return {
    ...formFromPeriod(latest),
    effective_from: "",
    mobilisation_charge_code: "",
    mobilisation_charge_amount: "",
    mobilisation_credit_after_months: "",
    demobilisation_charge_code: "",
    demobilisation_charge_amount: "",
    demobilisation_waived_after_months: "",
  };
}

/**
 * The form after the billing basis changes. When a basis is first chosen on a period with no rate
 * entered, the Work Order rate is pre-filled from the quoted rate on the offer - a starting value the
 * user checks and saves, not a link: later edits are independent of the quote.
 */
export function formAfterBasisChange(form: TermsForm, nextBasis: string, quotedRate: string | null): TermsForm {
  const firstChoice = form.billing_uom_code === "" && nextBasis !== "";
  const prefill = firstChoice && form.normal_rate_amount.trim() === "" && quotedRate != null && quotedRate !== "";
  return { ...form, billing_uom_code: nextBasis, normal_rate_amount: prefill ? String(quotedRate) : form.normal_rate_amount };
}

/** The writer id for a line's Start and Add controls; a period form uses its period's public id. */
export const ADD_PERIOD_WRITER = "add-period";

/**
 * Whether a control's message is stale. A message belongs to the latest write on its line: once another
 * control on the same line starts a write, earlier messages are cleared, so an old error cannot sit
 * beside later successful saves (owner screen check, 14 September 2026).
 */
export function feedbackIsStale(lastWriter: string | null, ownWriter: string): boolean {
  return lastWriter !== null && lastWriter !== ownWriter;
}

/**
 * One write at a time for a line. Every write returns the whole line, so two writes in flight could
 * answer out of order and an older answer would overwrite a newer one (review round 2). A second write
 * is refused until the first has finished; the synchronous flag also stops a double click that lands
 * before the page has re-rendered its buttons as disabled.
 */
export function createLineWriteGuard(): { tryBegin: () => boolean; end: () => void } {
  let inFlight = false;
  return {
    tryBegin: () => {
      if (inFlight) return false;
      inFlight = true;
      return true;
    },
    end: () => {
      inFlight = false;
    },
  };
}
