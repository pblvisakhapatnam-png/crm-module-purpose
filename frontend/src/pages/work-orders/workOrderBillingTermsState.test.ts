import { describe, expect, it } from "vitest";

import {
  type BillingTermPeriod,
  type LineBillingTerms,
  ADD_PERIOD_WRITER,
  MISSING_TERM_ITEMS,
  TERM_CHAPTERS,
  TERM_GROUP_MISSING_ITEMS,
  type TermGroupKey,
  createLineWriteGuard,
  feedbackIsStale,
  formAfterBasisChange,
  formForNewPeriod,
  formFromPeriod,
  missingTermsText,
  periodLabel,
  periodOpen,
  periodSummary,
  showsLineOnceTerms,
  showsMonthOvertimeRows,
  termGroupStatus,
  termsPayloadFromForm,
  visibleTermChapters,
  visibleTermGroupKeys,
  visibleTermGroups,
  wholeNumberOrNull,
  CREW_COUNT_MAX,
  amountProblem,
  decimalDigits,
  termsFormProblem,
  UPKEEP_CELLS,
  asksOvertimeCountedPer,
  shiftsPerDay,
  legacyNightShiftNote,
  crewOfPeriod,
  upkeepAnswerText,
  upkeepRoleApplies,
  upkeepWithHelpersAsOperators,
  UPKEEP_ROLES,
} from "./workOrderBillingTermsState";

const shiftPeriod: BillingTermPeriod = {
  term_public_id: "t1",
  period_number: 1,
  effective_from: null,
  effective_to: null,
  term_revision: 1,
  currency_code: "INR",
  billing_uom_code: "SHIFT",
  contracted_hours_per_billing_unit: "8.00",
  contracted_working_days_per_month: null,
  derived_hours_per_working_day: null,
  normal_rate_amount: "12000.00",
  weekly_off_day_codes: ["SUN"],
  off_day_work_treatment_code: "HOLIDAY_RATE",
  holiday_rate_method_code: "PERCENT_OF_NORMAL",
  holiday_rate_amount: null,
  holiday_rate_percent: "150.00",
  overtime_rate_method_code: "RATE_PER_HOUR",
  overtime_rate_amount: "1800.00",
  overtime_rate_percent: null,
  month_overtime_hours_basis_code: null,
  month_overtime_counting_code: null,
  breakdown_treatment_code: "DEDUCT_AT_BREAKDOWN_RATE",
  breakdown_rate_method_code: "RATE_PER_HOUR",
  breakdown_rate_amount: "300.00",
  breakdown_rate_percent: null,
  breakdown_offset_by_same_day_overtime: true,
  customer_idle_treatment_code: "AS_WORKING_HOURS",
  standby_rate_method_code: null,
  standby_rate_amount: null,
  standby_rate_percent: null,
  minimum_guarantee_code: "UNITS_PER_MONTH",
  minimum_billing_units_per_month: "25.00",
  part_month_basis_code: null,
  shift_pattern_code: null,
  shift_1_hours: null,
  shift_2_hours: null,
  shift_3_hours: null,
  shift_rate_code: null,
  shift_2_rate_method_code: null,
  shift_2_rate_amount: null,
  shift_2_rate_percent: null,
  shift_2_working_days_per_month: null,
  shift_3_rate_method_code: null,
  shift_3_rate_amount: null,
  shift_3_rate_percent: null,
  shift_3_working_days_per_month: null,
  overtime_counted_per_code: null,
  mobilisation_charge_code: null,
  mobilisation_charge_amount: null,
  mobilisation_credit_after_months: null,
  demobilisation_charge_code: null,
  demobilisation_charge_amount: null,
  demobilisation_waived_after_months: null,
  fuel_treatment_code: null,
  fuel_charge_method_code: null,
  fuel_rate_per_litre_amount: null,
  fuel_litres_per_working_hour: null,
  fuel_travel_allowance_code: null,
  fuel_litres_per_travel_hour: null,
  extra_km_allowance_code: null,
  extra_km_included_km: null,
  extra_km_rate_amount: null,
  crew_code: null,
  crew_operators_per_unit: null,
  crew_helpers_per_unit: null,
  extra_crew_charge_code: null,
  extra_crew_operator_rate_amount: null,
  extra_crew_helper_rate_amount: null,
  term_notes: null,
  is_complete: true,
  missing_items: [],
};

describe("visibleTermGroups", () => {
  it("shows an hourly line only its rate, idle time and minimum guarantee", () => {
    expect(visibleTermGroups("HOUR")).toEqual({
      rate: true, contractedHours: false, workingDays: false, offDays: false, overtime: false,
      monthOvertime: false, breakdown: false, minimumGuarantee: true, partMonth: false,
      // An hourly line has no shift pattern (Part 5), and fuel applies to every basis (Part 2, decision 10).
      shifts: false, shiftWorkingDays: false, fuel: true,
      // Extra kilometres and crew apply to every basis too (Part 4, answers 22 and 23).
      extraKm: true, crew: true,
    });
  });

  it("shows month-only terms on a monthly line and no minimum guarantee", () => {
    const month = visibleTermGroups("MONTH");
    expect(month.workingDays && month.monthOvertime && month.partMonth).toBe(true);
    expect(month.minimumGuarantee).toBe(false);
  });

  it("shows nothing but the basis before a basis is chosen", () => {
    expect(Object.values(visibleTermGroups("")).some(Boolean)).toBe(false);
  });
});

describe("termsPayloadFromForm", () => {
  it("round-trips a saved period's terms unchanged", () => {
    const payload = termsPayloadFromForm(formFromPeriod(shiftPeriod), 1);
    expect(payload).toMatchObject({
      billing_uom_code: "SHIFT",
      contracted_hours_per_billing_unit: "8.00",
      weekly_off_day_codes: ["SUN"],
      holiday_rate_method_code: "PERCENT_OF_NORMAL",
      holiday_rate_percent: "150.00",
      holiday_rate_amount: null,
      overtime_rate_amount: "1800.00",
      breakdown_rate_amount: "300.00",
      breakdown_offset_by_same_day_overtime: true,
      minimum_billing_units_per_month: "25.00",
    });
  });

  it("never sends a term hidden by switching to hour billing", () => {
    const form = { ...formFromPeriod(shiftPeriod), billing_uom_code: "HOUR" };
    const payload = termsPayloadFromForm(form, 1);
    for (const key of [
      "contracted_hours_per_billing_unit", "weekly_off_day_codes", "off_day_work_treatment_code", "holiday_rate_method_code",
      "overtime_rate_method_code", "overtime_rate_amount", "breakdown_treatment_code", "breakdown_rate_amount",
    ]) {
      expect(payload[key], key).toBeNull();
    }
    expect(payload.breakdown_offset_by_same_day_overtime).toBe(false);
    expect(payload.normal_rate_amount).toBe("12000.00");
  });

  it("sends no term at all, idle time included, once the basis is set back to not chosen", () => {
    const form = { ...formFromPeriod(shiftPeriod), billing_uom_code: "", customer_idle_treatment_code: "STANDBY_RATE", standby_rate: { method: "RATE_PER_HOUR", value: "500" } };
    const payload = termsPayloadFromForm(form, 1);
    const sent = Object.entries(payload).filter(([key, value]) => key !== "breakdown_offset_by_same_day_overtime" && value !== null);
    expect(sent).toEqual([]);
    expect(payload.breakdown_offset_by_same_day_overtime).toBe(false);
  });

  it("sends a rate's value as an amount or a percentage according to its method", () => {
    const form = formFromPeriod(shiftPeriod);
    form.overtime_rate = { method: "PERCENT_OF_NORMAL", value: "125" };
    const payload = termsPayloadFromForm(form, 1);
    expect(payload.overtime_rate_percent).toBe("125");
    expect(payload.overtime_rate_amount).toBeNull();
  });

  it("drops a dependent value once its parent choice no longer asks for it", () => {
    const form = { ...formFromPeriod(shiftPeriod), off_day_work_treatment_code: "OVERTIME_RATE", breakdown_treatment_code: "NONE", minimum_guarantee_code: "NONE" };
    const payload = termsPayloadFromForm(form, 1);
    expect(payload.holiday_rate_method_code).toBeNull();
    expect(payload.breakdown_rate_method_code).toBeNull();
    expect(payload.breakdown_offset_by_same_day_overtime).toBe(false);
    expect(payload.minimum_billing_units_per_month).toBeNull();
  });

  it("tells not-recorded off days apart from a 7-day week", () => {
    const notRecorded = termsPayloadFromForm({ ...formFromPeriod(shiftPeriod), off_days_recorded: false }, 1);
    const sevenDayWeek = termsPayloadFromForm({ ...formFromPeriod(shiftPeriod), weekly_off_day_codes: [] }, 1);
    expect(notRecorded.weekly_off_day_codes).toBeNull();
    expect(sevenDayWeek.weekly_off_day_codes).toEqual([]);
  });

  it("sends off days in week order whatever order they were ticked in", () => {
    const payload = termsPayloadFromForm({ ...formFromPeriod(shiftPeriod), weekly_off_day_codes: ["SUN", "SAT"] }, 1);
    expect(payload.weekly_off_day_codes).toEqual(["SAT", "SUN"]);
  });

  it("counts monthly overtime only when overtime is charged on a monthly line", () => {
    const monthly = { ...formFromPeriod(shiftPeriod), billing_uom_code: "MONTH", month_overtime_hours_basis_code: "ENGINE_HOURS", month_overtime_counting_code: "WHOLE_MONTH" };
    expect(termsPayloadFromForm(monthly, 1).month_overtime_hours_basis_code).toBe("ENGINE_HOURS");
    monthly.overtime_rate = { method: "NONE", value: "" };
    expect(termsPayloadFromForm(monthly, 1).month_overtime_hours_basis_code).toBeNull();
  });
});

describe("Part 2 terms", () => {
  it("sends mobilisation and demobilisation from the first period only", () => {
    const form = {
      ...formFromPeriod(shiftPeriod),
      mobilisation_charge_code: "CHARGED_CREDITED_AFTER_MONTHS",
      mobilisation_charge_amount: "150000",
      mobilisation_credit_after_months: "12",
      demobilisation_charge_code: "CHARGED",
      demobilisation_charge_amount: "120000",
    };
    const first = termsPayloadFromForm(form, 1);
    expect(first).toMatchObject({
      mobilisation_charge_code: "CHARGED_CREDITED_AFTER_MONTHS",
      mobilisation_charge_amount: "150000",
      mobilisation_credit_after_months: "12",
      demobilisation_charge_code: "CHARGED",
      demobilisation_charge_amount: "120000",
    });
    const later = termsPayloadFromForm(form, 2);
    for (const key of ["mobilisation_charge_code", "mobilisation_charge_amount", "mobilisation_credit_after_months", "demobilisation_charge_code", "demobilisation_charge_amount"]) {
      expect(later[key], key).toBeNull();
    }
  });

  it("drops a mobilisation charge and its months once the choice no longer asks for them", () => {
    const form = {
      ...formFromPeriod(shiftPeriod),
      mobilisation_charge_code: "NONE",
      mobilisation_charge_amount: "150000",
      mobilisation_credit_after_months: "12",
      demobilisation_charge_code: "CHARGED",
      demobilisation_charge_amount: "120000",
      demobilisation_waived_after_months: "12",
    };
    const payload = termsPayloadFromForm(form, 1);
    expect(payload.mobilisation_charge_amount).toBeNull();
    expect(payload.mobilisation_credit_after_months).toBeNull();
    // Charged without a waiver keeps the charge and drops the months.
    expect(payload.demobilisation_charge_amount).toBe("120000");
    expect(payload.demobilisation_waived_after_months).toBeNull();
  });

  it("sends each fuel value only where its own choice asks for it", () => {
    const base = formFromPeriod(shiftPeriod);
    const pblCharged = termsPayloadFromForm(
      { ...base, fuel_treatment_code: "PBL_SUPPLIED_CHARGED", fuel_charge_method_code: "AGREED_RATE_PER_LITRE", fuel_rate_per_litre_amount: "95.50", fuel_litres_per_working_hour: "12" },
      1,
    );
    expect(pblCharged).toMatchObject({ fuel_charge_method_code: "AGREED_RATE_PER_LITRE", fuel_rate_per_litre_amount: "95.50" });
    expect(pblCharged.fuel_litres_per_working_hour).toBeNull();

    const actualCost = termsPayloadFromForm({ ...base, fuel_treatment_code: "PBL_SUPPLIED_CHARGED", fuel_charge_method_code: "ACTUAL_COST", fuel_rate_per_litre_amount: "95.50" }, 1);
    expect(actualCost.fuel_rate_per_litre_amount).toBeNull();

    const customer = termsPayloadFromForm(
      { ...base, fuel_treatment_code: "CUSTOMER_SUPPLIED", fuel_litres_per_working_hour: "12", fuel_travel_allowance_code: "LITRES_PER_TRAVEL_HOUR", fuel_litres_per_travel_hour: "8", fuel_charge_method_code: "ACTUAL_COST" },
      1,
    );
    expect(customer).toMatchObject({ fuel_litres_per_working_hour: "12", fuel_travel_allowance_code: "LITRES_PER_TRAVEL_HOUR", fuel_litres_per_travel_hour: "8" });
    expect(customer.fuel_charge_method_code).toBeNull();

    const noTravel = termsPayloadFromForm({ ...base, fuel_treatment_code: "CUSTOMER_SUPPLIED", fuel_litres_per_working_hour: "12", fuel_travel_allowance_code: "NONE", fuel_litres_per_travel_hour: "8" }, 1);
    expect(noTravel.fuel_litres_per_travel_hour).toBeNull();
  });

  it("sends no fuel or mobilisation term before a basis is chosen", () => {
    const form = {
      ...formFromPeriod(shiftPeriod),
      billing_uom_code: "",
      fuel_treatment_code: "CUSTOMER_SUPPLIED",
      fuel_litres_per_working_hour: "12",
      mobilisation_charge_code: "CHARGED",
      mobilisation_charge_amount: "150000",
      shift_pattern_code: "TWO_SHIFTS",
    };
    const payload = termsPayloadFromForm(form, 1);
    for (const key of ["fuel_treatment_code", "fuel_litres_per_working_hour", "mobilisation_charge_code", "mobilisation_charge_amount", "shift_pattern_code"]) {
      expect(payload[key], key).toBeNull();
    }
  });

  it("names the new missing items in plain words", () => {
    const entry = {
      work_order_line_public_id: "l1", line_number: 1, quoted_uom: "Month", quoted_rate_amount: null,
      current_period_number: 1, periods: [], terms_complete: false,
      line_missing_items: ["SHIFTS", "MOBILISATION", "DEMOBILISATION", "FUEL", "CREW_UPKEEP"],
    } as LineBillingTerms;
    expect(missingTermsText(entry)).toBe(
      "Terms missing: shifts, mobilisation, demobilisation, fuel, crew food, accommodation and travel",
    );
  });
});

describe("formForNewPeriod", () => {
  it("starts from the latest period's terms with no start date", () => {
    const form = formForNewPeriod({ ...shiftPeriod, period_number: 2, effective_from: "2027-03-01" });
    expect(form.effective_from).toBe("");
    expect(form.normal_rate_amount).toBe("12000.00");
  });

  it("copies the shifts, the crew's upkeep and fuel, never mobilisation or demobilisation", () => {
    const latest: BillingTermPeriod = {
      ...shiftPeriod,
      shift_pattern_code: "TWO_SHIFTS",
      shift_1_hours: "12.00",
      shift_2_hours: "8.00",
      shift_rate_code: "PER_SHIFT",
      shift_2_rate_method_code: "RATE_PER_SHIFT",
      shift_2_rate_amount: "9000.00",
      crew_code: "STATED",
      crew_operators_per_unit: 1,
      crew_helpers_per_unit: 1,
      upkeep_food_operator_code: "PROVIDED",
      fuel_treatment_code: "CUSTOMER_SUPPLIED",
      fuel_litres_per_working_hour: "12.00",
      fuel_travel_allowance_code: "NONE",
      mobilisation_charge_code: "CHARGED",
      mobilisation_charge_amount: "150000.00",
      demobilisation_charge_code: "CHARGED_WAIVED_AFTER_MONTHS",
      demobilisation_charge_amount: "120000.00",
      demobilisation_waived_after_months: 12,
    };
    const form = formForNewPeriod(latest);
    expect(form.shift_2_rate).toEqual({ method: "RATE_PER_SHIFT", value: "9000.00" });
    expect(form.shift_1_hours).toBe("12.00");
    expect(form.upkeep.food_operator.code).toBe("PROVIDED");
    expect(form.fuel_litres_per_working_hour).toBe("12.00");
    expect(form.mobilisation_charge_code).toBe("");
    expect(form.mobilisation_charge_amount).toBe("");
    expect(form.demobilisation_charge_code).toBe("");
    expect(form.demobilisation_waived_after_months).toBe("");
    // And the request built from it carries none of them, whichever period it is for.
    expect(termsPayloadFromForm(form, 2).mobilisation_charge_code).toBeNull();
  });
});

describe("formAfterBasisChange", () => {
  it("pre-fills the Work Order rate from the quoted rate when a basis is first chosen on an empty period", () => {
    const form = formAfterBasisChange(formFromPeriod(undefined), "MONTH", "250000.00");
    expect(form.billing_uom_code).toBe("MONTH");
    expect(form.normal_rate_amount).toBe("250000.00");
  });

  it("never overwrites a rate already entered, or a period that already had a basis", () => {
    const typed = formAfterBasisChange({ ...formFromPeriod(undefined), normal_rate_amount: "9000" }, "DAY", "250000.00");
    expect(typed.normal_rate_amount).toBe("9000");
    const changingBasis = formAfterBasisChange({ ...formFromPeriod(shiftPeriod), normal_rate_amount: "" }, "DAY", "250000.00");
    expect(changingBasis.normal_rate_amount).toBe("");
  });

  it("leaves the rate empty when the offer has no quoted rate", () => {
    expect(formAfterBasisChange(formFromPeriod(undefined), "HOUR", null).normal_rate_amount).toBe("");
  });

  it("a later period copies the latest saved Work Order rate, not the quoted rate", () => {
    const later = formAfterBasisChange(formForNewPeriod({ ...shiftPeriod, normal_rate_amount: "13000.00" }), "SHIFT", "250000.00");
    expect(later.normal_rate_amount).toBe("13000.00");
  });
});

describe("showsMonthOvertimeRows", () => {
  it("shows both monthly overtime rows whenever overtime is charged on a monthly line, whatever is chosen", () => {
    const month = { billing_uom_code: "MONTH", overtime_rate_method_code: "PERCENT_OF_NORMAL" };
    // Only counting chosen, only hours basis chosen, neither chosen: each is still shown, with "-" for the gap.
    expect(showsMonthOvertimeRows({ ...month, month_overtime_hours_basis_code: null, month_overtime_counting_code: "WHOLE_MONTH" } as never)).toBe(true);
    expect(showsMonthOvertimeRows({ ...month, month_overtime_hours_basis_code: "ENGINE_HOURS", month_overtime_counting_code: null } as never)).toBe(true);
    expect(showsMonthOvertimeRows(month)).toBe(true);
  });

  it("hides them when overtime is not charged or the line is not monthly", () => {
    expect(showsMonthOvertimeRows({ billing_uom_code: "MONTH", overtime_rate_method_code: "NONE" })).toBe(false);
    expect(showsMonthOvertimeRows({ billing_uom_code: "MONTH", overtime_rate_method_code: null })).toBe(false);
    expect(showsMonthOvertimeRows({ billing_uom_code: "SHIFT", overtime_rate_method_code: "RATE_PER_HOUR" })).toBe(false);
  });
});

describe("showsLineOnceTerms", () => {
  it("shows mobilisation and demobilisation on the first period only", () => {
    expect(showsLineOnceTerms(1)).toBe(true);
    expect(showsLineOnceTerms(2)).toBe(false);
  });
});

describe("feedbackIsStale", () => {
  it("keeps a control's message until another control on the line starts a write", () => {
    expect(feedbackIsStale(null, ADD_PERIOD_WRITER)).toBe(false);
    expect(feedbackIsStale(ADD_PERIOD_WRITER, ADD_PERIOD_WRITER)).toBe(false);
    expect(feedbackIsStale("term-1", "term-1")).toBe(false);
  });

  it("clears the Add message once a period is saved, and a period's message once another period is saved", () => {
    expect(feedbackIsStale("term-1", ADD_PERIOD_WRITER)).toBe(true);
    expect(feedbackIsStale("term-2", "term-1")).toBe(true);
    expect(feedbackIsStale(ADD_PERIOD_WRITER, "term-1")).toBe(true);
  });
});

describe("createLineWriteGuard", () => {
  it("refuses a second write while one is in flight, and allows the next once it ends", () => {
    const guard = createLineWriteGuard();
    expect(guard.tryBegin()).toBe(true);
    expect(guard.tryBegin()).toBe(false);
    guard.end();
    expect(guard.tryBegin()).toBe(true);
  });
});

describe("periodLabel", () => {
  it("names period 1 by the contract start and later periods by their date", () => {
    expect(periodLabel({ period_number: 1, effective_from: null })).toBe("From contract start");
    expect(periodLabel({ period_number: 2, effective_from: "2027-03-01" })).toBe("From 1 March 2027");
    expect(periodLabel({ period_number: 1, effective_from: null, effective_to: "2027-02-28" })).toBe("From contract start to 28 February 2027");
  });
});

describe("missingTermsText", () => {
  const entry = (overrides: Partial<LineBillingTerms>): LineBillingTerms => ({
    work_order_line_public_id: "l1", line_number: 1, quoted_uom: "Month", quoted_rate_amount: null,
    current_period_number: null, periods: [], terms_complete: false, line_missing_items: ["NO_TERMS"], ...overrides,
  });

  it("reads plainly for no terms, missing terms and complete terms", () => {
    expect(missingTermsText(entry({}))).toBe("Terms missing: no terms yet");
    expect(missingTermsText(entry({ line_missing_items: ["NORMAL_RATE", "OVERTIME"] }))).toBe("Terms missing: Work Order rate, overtime");
    expect(missingTermsText(entry({ terms_complete: true, line_missing_items: [] }))).toBe("Terms complete");
    expect(missingTermsText(undefined)).toBe("Terms not loaded");
  });
});

// Slice 7D.1: the form's cards and chapters.
describe("term groups and chapters", () => {
  it("gives every reportable missing item to exactly one group, so no gap can go unflagged", () => {
    const owners = (item: string) =>
      (Object.keys(TERM_GROUP_MISSING_ITEMS) as TermGroupKey[]).filter((group) => TERM_GROUP_MISSING_ITEMS[group].includes(item));
    for (const item of MISSING_TERM_ITEMS.filter((code) => code !== "NO_TERMS")) {
      expect(owners(item), item).toHaveLength(1);
    }
    // And nothing the backend never reports is claimed by a group.
    for (const item of Object.values(TERM_GROUP_MISSING_ITEMS).flat()) {
      expect(MISSING_TERM_ITEMS).toContain(item);
    }
  });

  it("puts every group in exactly one chapter", () => {
    const placed = TERM_CHAPTERS.flatMap((chapter) => chapter.groups);
    expect([...placed].sort()).toEqual((Object.keys(TERM_GROUP_MISSING_ITEMS) as TermGroupKey[]).sort());
    expect(new Set(placed).size).toBe(placed.length);
  });

  it("shows only the groups a basis has, in form order", () => {
    expect(visibleTermGroupKeys("", 1)).toEqual(["basis"]);
    expect(visibleTermGroupKeys("HOUR", 1)).toEqual(["basis", "idle", "fuel", "extraKm", "crew", "lineOnce"]);
    expect(visibleTermGroupKeys("MONTH", 1)).toEqual([
      "basis", "offDays", "shifts", "overtime", "breakdown", "idle", "fuel", "extraKm", "crew", "lineOnce",
    ]);
    // Mobilisation and demobilisation belong to the first period only.
    expect(visibleTermGroupKeys("MONTH", 2)).toEqual([
      "basis", "offDays", "shifts", "overtime", "breakdown", "idle", "fuel", "extraKm", "crew",
    ]);
    // The crew's upkeep once the Work Order states its crew (Part 5, A4).
    expect(visibleTermGroupKeys("HOUR", 1, "STATED")).toEqual(["basis", "idle", "fuel", "extraKm", "crew", "upkeep", "lineOnce"]);
    expect(visibleTermGroupKeys("HOUR", 1, "NONE")).not.toContain("upkeep");
  });

  it("drops a chapter with nothing to show, and keeps only the visible groups of the rest", () => {
    expect(visibleTermChapters("", 1).map((chapter) => chapter.key)).toEqual(["rate"]);
    const hourly = visibleTermChapters("HOUR", 2);
    expect(hourly.map((chapter) => [chapter.key, chapter.groups])).toEqual([
      ["rate", ["basis"]],
      ["workingTime", ["idle"]],
      ["extraCharges", ["fuel", "extraKm", "crew"]],
    ]);
  });

  it("tags a group missing while any item it answers is missing, and answered otherwise", () => {
    const saved = { billing_uom_code: "MONTH", missing_items: ["MONTH_OVERTIME_METHOD", "FUEL"] };
    expect(termGroupStatus("overtime", saved, "MONTH")).toBe("missing");
    expect(termGroupStatus("fuel", saved, "MONTH")).toBe("missing");
    expect(termGroupStatus("basis", saved, "MONTH")).toBe("answered");
    expect(termGroupStatus("lineOnce", saved, "MONTH")).toBe("answered");
  });

  it("opens the latest period and any period with gaps, and closes a complete earlier period", () => {
    const complete = { missing_items: [] };
    const gaps = { missing_items: ["FUEL"] };
    expect(periodOpen(null, complete, true)).toBe(true);
    expect(periodOpen(null, gaps, true)).toBe(true);
    expect(periodOpen(null, complete, false)).toBe(false);
    expect(periodOpen(null, gaps, false)).toBe(true);
  });

  it("keeps a period as the user left it, so saving an earlier period to complete does not close it", () => {
    expect(periodOpen(true, { missing_items: [] }, false)).toBe(true);
    expect(periodOpen(false, { missing_items: ["FUEL"] }, true)).toBe(false);
  });

  it("summarises a period by its basis and rate, leaving out what is not recorded", () => {
    expect(periodSummary({ billing_uom_code: "MONTH", normal_rate_amount: "100000.00" })).toBe("Month - INR 100000.00");
    expect(periodSummary({ billing_uom_code: "SHIFT", normal_rate_amount: null })).toBe("Shift");
    expect(periodSummary({ billing_uom_code: null, normal_rate_amount: null })).toBe("");
    expect(periodSummary(undefined)).toBe("");
  });

  it("shows no tag while the form's basis differs from the saved one, since the report describes the saved basis", () => {
    const saved = { billing_uom_code: "MONTH", missing_items: [] };
    expect(termGroupStatus("idle", saved, "HOUR")).toBeNull();
    expect(termGroupStatus("basis", { billing_uom_code: null, missing_items: ["BILLING_BASIS"] }, "")).toBe("missing");
    expect(termGroupStatus("basis", { billing_uom_code: null, missing_items: ["BILLING_BASIS"] }, "SHIFT")).toBeNull();
  });
});

describe("Part 4 terms", () => {
  const stated = {
    ...formFromPeriod(shiftPeriod),
    extra_km_allowance_code: "KM_PER_DAY",
    extra_km_included_km: "100.00",
    extra_km_rate_amount: "45.00",
    crew_code: "STATED",
    crew_operators_per_unit: "2",
    crew_helpers_per_unit: "0",
    extra_crew_charge_code: "RATE_PER_PERSON",
    extra_crew_operator_rate_amount: "1800.00",
    extra_crew_helper_rate_amount: "900.00",
  };

  it("sends the kilometres and the rate only while an allowance is chosen", () => {
    expect(termsPayloadFromForm(stated, 1)).toMatchObject({
      extra_km_allowance_code: "KM_PER_DAY",
      extra_km_included_km: "100.00",
      extra_km_rate_amount: "45.00",
    });
    const none = termsPayloadFromForm({ ...stated, extra_km_allowance_code: "NONE" }, 1);
    expect(none).toMatchObject({ extra_km_allowance_code: "NONE", extra_km_included_km: null, extra_km_rate_amount: null });
  });

  it("sends the crew numbers as whole numbers, keeping zero as a real answer", () => {
    const payload = termsPayloadFromForm(stated, 1);
    expect(payload.crew_operators_per_unit).toBe(2);
    expect(payload.crew_helpers_per_unit).toBe(0);
  });

  it("drops the numbers and every extra-crew value once the Work Order has no crew", () => {
    const payload = termsPayloadFromForm({ ...stated, crew_code: "NONE" }, 1);
    for (const key of [
      "crew_operators_per_unit", "crew_helpers_per_unit", "extra_crew_charge_code",
      "extra_crew_operator_rate_amount", "extra_crew_helper_rate_amount",
    ]) {
      expect(payload[key], key).toBeNull();
    }
    expect(payload.crew_code).toBe("NONE");
  });

  it("sends the extra-crew rates only while extra crew is charged per person", () => {
    const payload = termsPayloadFromForm({ ...stated, extra_crew_charge_code: "NONE" }, 1);
    expect(payload).toMatchObject({ extra_crew_charge_code: "NONE", extra_crew_operator_rate_amount: null, extra_crew_helper_rate_amount: null });
  });

  it("sends both terms on an hourly line, and neither before a basis is chosen", () => {
    const hourly = termsPayloadFromForm({ ...stated, billing_uom_code: "HOUR" }, 1);
    expect(hourly).toMatchObject({ extra_km_allowance_code: "KM_PER_DAY", crew_code: "STATED", crew_operators_per_unit: 2 });
    const noBasis = termsPayloadFromForm({ ...stated, billing_uom_code: "" }, 1);
    for (const key of ["extra_km_allowance_code", "extra_km_included_km", "crew_code", "crew_operators_per_unit", "extra_crew_charge_code"]) {
      expect(noBasis[key], key).toBeNull();
    }
  });

  it("carries both terms into a later period, because they belong to each period", () => {
    const saved = {
      ...shiftPeriod,
      extra_km_allowance_code: "KM_PER_MONTH",
      extra_km_included_km: "3000.00",
      extra_km_rate_amount: "40.00",
      crew_code: "STATED",
      crew_operators_per_unit: 3,
      crew_helpers_per_unit: 3,
      extra_crew_charge_code: "NONE",
    };
    const form = formForNewPeriod(saved);
    expect(form).toMatchObject({
      extra_km_allowance_code: "KM_PER_MONTH",
      extra_km_included_km: "3000.00",
      crew_code: "STATED",
      crew_operators_per_unit: "3",
      crew_helpers_per_unit: "3",
      extra_crew_charge_code: "NONE",
    });
  });

  it("stops a malformed crew number before it is sent, naming the field in the line's own unit", () => {
    // Review round 1, finding F-02: the server's refusal of such a number reaches the screen only as a
    // generic message, so the form names the field and the rule itself.
    expect(termsFormProblem(stated)).toBeNull();
    expect(termsFormProblem({ ...stated, crew_operators_per_unit: "1.5" })).toBe("Operators per shift must be a whole number, 0 or more.");
    expect(termsFormProblem({ ...stated, crew_helpers_per_unit: "-1" })).toBe("Helpers per shift must be a whole number, 0 or more.");
    expect(termsFormProblem({ ...stated, billing_uom_code: "DAY", crew_helpers_per_unit: "two" })).toBe(
      "Helpers per day must be a whole number, 0 or more.",
    );
    expect(termsFormProblem({ ...stated, crew_operators_per_unit: "2147483648" })).toBe("Operators per shift is larger than can be recorded.");
    expect(termsFormProblem({ ...stated, crew_operators_per_unit: String(CREW_COUNT_MAX) })).toBeNull();
    // Not entered yet is reported missing by the server, not refused here.
    expect(termsFormProblem({ ...stated, crew_operators_per_unit: "", crew_helpers_per_unit: "  " })).toBeNull();
  });

  it("refuses an amount exactly where the server would, and lets through what it accepts", () => {
    // Review round 2, finding F-06. The cases mirror the server's own answers, probed on the running
    // backend: numeric(9,2) for kilometres, numeric(18,2) for rates, leading and trailing zeros ignored.
    const km = (value: string) => amountProblem("Kilometres included per day", value, 7);
    expect(km("")).toBeNull();
    expect(km("0")).toBe("Kilometres included per day must be greater than 0.");
    expect(km("-1")).toBe("Kilometres included per day must be greater than 0.");
    expect(km("1.234")).toBe("Kilometres included per day can have at most 2 decimal places.");
    expect(km("10000000")).toBe("Kilometres included per day is larger than can be recorded.");
    expect(km("10000000.00")).toBe("Kilometres included per day is larger than can be recorded.");
    for (const accepted of ["9999999.99", "1.500", "0.5", ".5", "0000012.50", "12.", "1e3"]) {
      expect(km(accepted), accepted).toBeNull();
    }
    const rate = (value: string) => amountProblem("Rate per extra kilometre", value, 16);
    expect(rate("9999999999999999.99")).toBeNull();
    expect(rate("10000000000000000")).toBe("Rate per extra kilometre is larger than can be recorded.");
  });

  it("holds exponent forms to the same limits as plain ones, as the server does", () => {
    // Review round 3, finding F-07: a browser number field accepts exponent notation, and the server reads
    // it as the plain number. Every case below is the server's own answer, probed on the running backend.
    const km = (value: string) => amountProblem("Kilometres included per day", value, 7);
    for (const accepted of ["1e3", "1E3", "9.99e6", "9.9999999e6", "1.5e1", "1.00e2", "+5", "1e-2"]) {
      expect(km(accepted), accepted).toBeNull();
    }
    expect(km("1e-3")).toBe("Kilometres included per day can have at most 2 decimal places.");
    expect(km("1.5e-2")).toBe("Kilometres included per day can have at most 2 decimal places.");
    expect(km("1e7")).toBe("Kilometres included per day is larger than can be recorded.");
    const rate = (value: string) => amountProblem("Rate per extra kilometre", value, 16);
    expect(rate("9.99e15")).toBeNull();
    expect(rate("1e15")).toBeNull();
    expect(rate("1e16")).toBe("Rate per extra kilometre is larger than can be recorded.");
    expect(km("0x10")).toBe("Kilometres included per day must be a number.");
  });

  it("writes an exponent form out before counting its digits", () => {
    expect(decimalDigits("1e3")).toEqual({ whole: "1000", fraction: "" });
    expect(decimalDigits("1.5e-2")).toEqual({ whole: "", fraction: "015" });
    expect(decimalDigits("0000012.50")).toEqual({ whole: "12", fraction: "5" });
    expect(decimalDigits(".5")).toEqual({ whole: "", fraction: "5" });
    expect(decimalDigits("12.")).toEqual({ whole: "12", fraction: "" });
    expect(decimalDigits("abc")).toBeNull();
    expect(decimalDigits(".")).toBeNull();
  });

  it("refuses an exponent-form amount through the form check, naming the field", () => {
    expect(termsFormProblem({ ...stated, extra_km_included_km: "1e-3" })).toBe(
      "Kilometres included per day can have at most 2 decimal places.",
    );
    expect(termsFormProblem({ ...stated, extra_km_included_km: "1e7" })).toBe("Kilometres included per day is larger than can be recorded.");
    expect(termsFormProblem({ ...stated, extra_km_rate_amount: "1e16" })).toBe("Rate per extra kilometre is larger than can be recorded.");
    expect(termsFormProblem({ ...stated, extra_crew_helper_rate_amount: "1e16" })).toBe(
      "Each extra helper, per shift is larger than can be recorded.",
    );
    expect(termsFormProblem({ ...stated, extra_km_included_km: "1e3", extra_crew_operator_rate_amount: "9.99e15" })).toBeNull();
  });

  it("checks each Part 4 amount that would be sent, naming it in the line's own unit", () => {
    expect(termsFormProblem({ ...stated, extra_km_included_km: "0" })).toBe("Kilometres included per day must be greater than 0.");
    expect(termsFormProblem({ ...stated, extra_km_allowance_code: "KM_PER_MONTH", extra_km_included_km: "1.234" })).toBe(
      "Kilometres included per month can have at most 2 decimal places.",
    );
    expect(termsFormProblem({ ...stated, extra_km_rate_amount: "-5" })).toBe("Rate per extra kilometre must be greater than 0.");
    expect(termsFormProblem({ ...stated, extra_crew_operator_rate_amount: "0" })).toBe("Each extra operator, per shift must be greater than 0.");
    expect(termsFormProblem({ ...stated, billing_uom_code: "DAY", extra_crew_helper_rate_amount: "12.345" })).toBe(
      "Each extra helper, per day can have at most 2 decimal places.",
    );
  });

  it("does not check an amount that would not be sent", () => {
    expect(termsFormProblem({ ...stated, extra_km_allowance_code: "NONE", extra_km_included_km: "0" })).toBeNull();
    expect(termsFormProblem({ ...stated, extra_crew_charge_code: "NONE", extra_crew_operator_rate_amount: "0" })).toBeNull();
    expect(termsFormProblem({ ...stated, crew_code: "NONE", extra_crew_helper_rate_amount: "0" })).toBeNull();
  });

  it("ignores the crew numbers when they would not be sent", () => {
    expect(termsFormProblem({ ...stated, crew_code: "NONE", crew_operators_per_unit: "1.5" })).toBeNull();
    expect(termsFormProblem({ ...stated, billing_uom_code: "", crew_operators_per_unit: "1.5" })).toBeNull();
  });

  it("reads a count typed as a whole number, and passes anything else through unrounded as a backstop", () => {
    expect(wholeNumberOrNull(true, "")).toBeNull();
    expect(wholeNumberOrNull(true, "  ")).toBeNull();
    expect(wholeNumberOrNull(true, "3")).toBe(3);
    expect(wholeNumberOrNull(true, "0")).toBe(0);
    expect(wholeNumberOrNull(true, "1.5")).toBe("1.5");
    expect(wholeNumberOrNull(false, "3")).toBeNull();
  });

  it("names the two new missing items in plain words, and tags their cards", () => {
    const entry: LineBillingTerms = {
      work_order_line_public_id: "l1",
      line_number: 1,
      quoted_uom: "Shift",
      quoted_rate_amount: null,
      current_period_number: 1,
      periods: [],
      terms_complete: false,
      line_missing_items: ["EXTRA_KILOMETRES", "CREW"],
    };
    expect(missingTermsText(entry)).toBe("Terms missing: extra kilometres, crew");
    const saved = { billing_uom_code: "SHIFT", missing_items: ["CREW"] };
    expect(termGroupStatus("crew", saved, "SHIFT")).toBe("missing");
    expect(termGroupStatus("extraKm", saved, "SHIFT")).toBe("answered");
  });
});

describe("Part 5: shifts", () => {
  const twoShifts = {
    ...formFromPeriod(shiftPeriod),
    shift_pattern_code: "TWO_SHIFTS",
    shift_1_hours: "12",
    shift_2_hours: "8",
    shift_3_hours: "4",
    shift_rate_code: "PER_SHIFT",
    shift_2_rate: { method: "RATE_PER_SHIFT", value: "9000" },
    shift_2_working_days_per_month: "26",
    shift_3_rate: { method: "RATE_PER_HOUR", value: "700" },
    overtime_counted_per_code: "PER_SHIFT",
  };

  it("sends each shift's hours, the rate choice and the later shift's rate for two shifts, and no third shift", () => {
    const payload = termsPayloadFromForm(twoShifts, 1);
    expect(payload).toMatchObject({
      shift_pattern_code: "TWO_SHIFTS",
      shift_1_hours: "12",
      shift_2_hours: "8",
      shift_rate_code: "PER_SHIFT",
      shift_2_rate_method_code: "RATE_PER_SHIFT",
      shift_2_rate_amount: "9000",
      shift_2_rate_percent: null,
      overtime_counted_per_code: "PER_SHIFT",
    });
    for (const key of ["shift_3_hours", "shift_3_rate_method_code", "shift_3_rate_amount", "shift_2_working_days_per_month"]) {
      expect(payload[key], key).toBeNull();
    }
  });

  it("sends a third shift and the working days only where they apply", () => {
    const monthly = termsPayloadFromForm(
      { ...twoShifts, billing_uom_code: "MONTH", shift_pattern_code: "THREE_SHIFTS", shift_3_working_days_per_month: "24", month_overtime_counting_code: "DAY_BY_DAY" },
      1,
    );
    expect(monthly).toMatchObject({
      shift_3_hours: "4",
      shift_3_rate_method_code: "RATE_PER_HOUR",
      shift_3_rate_amount: "700",
      shift_2_working_days_per_month: "26",
      shift_3_working_days_per_month: "24",
    });
  });

  it("sends no later shift's own rate with one rate for every shift, and nothing but the answer with one shift", () => {
    const sameRate = termsPayloadFromForm({ ...twoShifts, shift_rate_code: "SAME_FOR_ALL_SHIFTS" }, 1);
    expect(sameRate.shift_2_rate_method_code).toBeNull();
    expect(sameRate.shift_2_rate_amount).toBeNull();
    expect(sameRate.shift_1_hours).toBe("12");
    const oneShift = termsPayloadFromForm({ ...twoShifts, shift_pattern_code: "NONE" }, 1);
    expect(oneShift.shift_pattern_code).toBe("NONE");
    for (const key of ["shift_1_hours", "shift_2_hours", "shift_rate_code", "shift_2_rate_method_code", "overtime_counted_per_code"]) {
      expect(oneShift[key], key).toBeNull();
    }
  });

  it("sends one stated shift's hours and nothing a second shift brings; 'not in the Work Order' states none", () => {
    const one = termsPayloadFromForm({ ...twoShifts, shift_pattern_code: "ONE_SHIFT" }, 1);
    expect(one).toMatchObject({ shift_pattern_code: "ONE_SHIFT", shift_1_hours: "12" });
    for (const key of ["shift_2_hours", "shift_3_hours", "shift_rate_code", "shift_2_rate_method_code", "overtime_counted_per_code"]) {
      expect(one[key], key).toBeNull();
    }
    expect(asksOvertimeCountedPer({ ...twoShifts, shift_pattern_code: "ONE_SHIFT" })).toBe(false);
    expect([shiftsPerDay("NONE"), shiftsPerDay(""), shiftsPerDay(null), shiftsPerDay("ONE_SHIFT"), shiftsPerDay("THREE_SHIFTS")]).toEqual([0, 0, 0, 1, 3]);
    expect(termsFormProblem({ ...twoShifts, shift_pattern_code: "ONE_SHIFT", shift_1_hours: "25" })).toBe(
      "The shifts add up to 25 hours, more than the 24 hours in a day.",
    );
  });

  it("sends no shift term on an hourly line", () => {
    const hourly = termsPayloadFromForm({ ...twoShifts, billing_uom_code: "HOUR" }, 1);
    for (const key of ["shift_pattern_code", "shift_1_hours", "shift_rate_code", "shift_2_rate_method_code", "overtime_counted_per_code"]) {
      expect(hourly[key], key).toBeNull();
    }
  });

  it("asks per shift or per day wherever overtime is charged on several shifts", () => {
    expect(asksOvertimeCountedPer(twoShifts)).toBe(true);
    expect(asksOvertimeCountedPer({ ...twoShifts, overtime_rate: { method: "NONE", value: "" } })).toBe(false);
    expect(asksOvertimeCountedPer({ ...twoShifts, shift_pattern_code: "NONE" })).toBe(false);
    // A monthly line counted over the whole month is asked too (review round 1, 7D5-R1-001).
    const wholeMonth = { ...twoShifts, billing_uom_code: "MONTH", month_overtime_counting_code: "WHOLE_MONTH" };
    const dayByDay = { ...wholeMonth, month_overtime_counting_code: "DAY_BY_DAY" };
    expect(asksOvertimeCountedPer(wholeMonth)).toBe(true);
    expect(asksOvertimeCountedPer(dayByDay)).toBe(true);
    expect(termsPayloadFromForm(wholeMonth, 1).overtime_counted_per_code).toBe("PER_SHIFT");
  });

  it("names the field when a shift number cannot be sent, and refuses more than 24 hours in a day", () => {
    expect(termsFormProblem({ ...twoShifts, shift_1_hours: "0" })).toBe("Shift 1 hours must be greater than 0.");
    expect(termsFormProblem({ ...twoShifts, shift_2_hours: "100" })).toBe("Shift 2 hours is larger than can be recorded.");
    expect(termsFormProblem({ ...twoShifts, shift_1_hours: "16", shift_2_hours: "8.5" })).toBe(
      "The shifts add up to 24.5 hours, more than the 24 hours in a day.",
    );
    expect(termsFormProblem({ ...twoShifts, shift_1_hours: "16", shift_2_hours: "8" })).toBeNull();
    expect(termsFormProblem({ ...twoShifts, shift_2_rate: { method: "PERCENT_OF_NORMAL", value: "-5" } })).toBe(
      "Shift 2's percentage must be greater than 0.",
    );
    // A hidden third shift is not checked.
    expect(termsFormProblem({ ...twoShifts, shift_3_hours: "-1" })).toBeNull();
  });
});

describe("Part 5: the crew's food, accommodation and travel", () => {
  const crew = {
    ...formFromPeriod(shiftPeriod),
    crew_code: "STATED",
    crew_operators_per_unit: "1",
    crew_helpers_per_unit: "2",
  };
  const withFood = {
    ...crew,
    upkeep: {
      ...crew.upkeep,
      food_operator: { code: "PROVIDED_AT_COST", amount: "150", unit: "PER_PERSON_PER_DAY", recovery: "DEDUCTED_FROM_INVOICE" },
      food_helper: { code: "PROVIDED", amount: "99", unit: "PER_PERSON_PER_MONTH", recovery: "BILLED_SEPARATELY" },
      job_travel_operator: { code: "PROVIDED_AT_COST", amount: "2500", unit: "PER_TRIP", recovery: "BILLED_SEPARATELY" },
    },
  };

  it("has eight cells, four items for operators and for helpers, each cost stating its own basis", () => {
    expect(UPKEEP_CELLS.map((cell) => cell.key)).toEqual([
      "food_operator", "food_helper", "accommodation_operator", "accommodation_helper",
      "job_travel_operator", "job_travel_helper", "daily_travel_operator", "daily_travel_helper",
    ]);
    // The same codes the server accepts for each item (WORK_ORDER_LINE_UPKEEP_ITEMS).
    expect(Object.fromEntries(UPKEEP_CELLS.filter((cell) => cell.role.key === "operator").map((cell) => [cell.item.key, cell.item.units.map((unit) => unit.code)]))).toEqual({
      food: ["PER_PERSON_PER_DAY", "PER_PERSON_PER_MONTH"],
      accommodation: ["PER_PERSON_PER_DAY", "PER_PERSON_PER_MONTH"],
      job_travel: ["PER_PERSON_PER_TRIP", "PER_TRIP"],
      daily_travel: ["PER_PERSON_PER_DAY", "PER_DAY"],
    });
  });

  it("sends a cost's amount, basis and recovery only at a cost", () => {
    const payload = termsPayloadFromForm(withFood, 1);
    expect(payload).toMatchObject({
      upkeep_food_operator_code: "PROVIDED_AT_COST",
      upkeep_food_operator_amount: "150",
      upkeep_food_operator_unit_code: "PER_PERSON_PER_DAY",
      upkeep_food_operator_recovery_code: "DEDUCTED_FROM_INVOICE",
      upkeep_food_helper_code: "PROVIDED",
      upkeep_food_helper_amount: null,
      upkeep_food_helper_unit_code: null,
      upkeep_food_helper_recovery_code: null,
      upkeep_job_travel_operator_amount: "2500",
      upkeep_job_travel_operator_unit_code: "PER_TRIP",
      upkeep_job_travel_operator_recovery_code: "BILLED_SEPARATELY",
    });
  });

  it("sends no upkeep for equipment only, and none for a role the Work Order states 0 of", () => {
    const equipmentOnly = termsPayloadFromForm({ ...withFood, crew_code: "NONE" }, 1);
    expect(UPKEEP_CELLS.every((cell) => equipmentOnly[cell.column("code")] === null)).toBe(true);
    const noHelpers = { ...withFood, crew_helpers_per_unit: "0" };
    expect(upkeepRoleApplies(noHelpers, UPKEEP_ROLES[1])).toBe(false);
    expect(upkeepRoleApplies(noHelpers, UPKEEP_ROLES[0])).toBe(true);
    const payload = termsPayloadFromForm(noHelpers, 1);
    expect(payload.upkeep_food_helper_code).toBeNull();
    expect(payload.upkeep_food_operator_code).toBe("PROVIDED_AT_COST");
    // A count not yet entered still asks: the Work Order may state some.
    expect(upkeepRoleApplies({ ...withFood, crew_helpers_per_unit: "" }, UPKEEP_ROLES[1])).toBe(true);
  });

  it("copies the operators' answers to the helpers on request, leaving the operators as they were", () => {
    const copied = upkeepWithHelpersAsOperators(withFood.upkeep);
    expect(copied.food_helper).toEqual(withFood.upkeep.food_operator);
    expect(copied.job_travel_helper).toEqual(withFood.upkeep.job_travel_operator);
    expect(copied.food_operator).toEqual(withFood.upkeep.food_operator);
    copied.food_helper.amount = "1";
    expect(withFood.upkeep.food_operator.amount).toBe("150");
  });

  it("names the field when a cost cannot be sent", () => {
    const bad = { ...withFood, upkeep: { ...withFood.upkeep, accommodation_helper: { code: "PROVIDED_AT_COST", amount: "0", unit: "", recovery: "" } } };
    expect(termsFormProblem(bad)).toBe("Accommodation for helpers must be greater than 0.");
  });

  it("reads a saved answer as one line, and the round trip keeps it", () => {
    const saved: BillingTermPeriod = {
      ...shiftPeriod,
      crew_code: "STATED",
      crew_operators_per_unit: 1,
      crew_helpers_per_unit: 0,
      upkeep_accommodation_operator_code: "PROVIDED_AT_COST",
      upkeep_accommodation_operator_amount: "150.00",
      upkeep_accommodation_operator_unit_code: "PER_PERSON_PER_DAY",
      upkeep_accommodation_operator_recovery_code: "DEDUCTED_FROM_INVOICE",
      upkeep_job_travel_operator_code: "PROVIDED_AT_COST",
      upkeep_job_travel_operator_amount: "2500.00",
      upkeep_job_travel_operator_unit_code: "PER_TRIP",
      upkeep_job_travel_operator_recovery_code: "BILLED_SEPARATELY",
      upkeep_food_operator_code: "PROVIDED",
    };
    const cell = (key: string) => UPKEEP_CELLS.find((each) => each.key === key)!;
    expect(upkeepAnswerText(cell("accommodation_operator"), saved)).toBe("INR 150.00 per person per day; deducted from PBL's invoice");
    expect(upkeepAnswerText(cell("job_travel_operator"), saved)).toBe(
      "INR 2500.00 per trip, whatever the number of people; billed to PBL separately by the customer",
    );
    expect(upkeepAnswerText(cell("food_operator"), saved)).toBe("Provided by the customer");
    expect(upkeepAnswerText(cell("daily_travel_operator"), saved)).toBe("-");
    expect(upkeepRoleApplies(crewOfPeriod(saved), UPKEEP_ROLES[1])).toBe(false);
    expect(termsPayloadFromForm(formFromPeriod(saved), 1)).toMatchObject({
      upkeep_accommodation_operator_amount: "150.00",
      upkeep_job_travel_operator_recovery_code: "BILLED_SEPARATELY",
    });
  });
});

describe("Part 5: a kept Part 2 night-shift answer", () => {
  it("is shown beside the shift question only where the migration kept it, and is never sent", () => {
    expect(legacyNightShiftNote({ legacy_night_shift_not_in_work_order: true })).toContain("night shift was not in the Work Order");
    expect(legacyNightShiftNote({ legacy_night_shift_not_in_work_order: false })).toBeNull();
    expect(legacyNightShiftNote({})).toBeNull();
    expect(legacyNightShiftNote(undefined)).toBeNull();
    const payload = termsPayloadFromForm(formFromPeriod({ ...shiftPeriod, legacy_night_shift_not_in_work_order: true }), 1);
    expect("legacy_night_shift_not_in_work_order" in payload).toBe(false);
  });
});
