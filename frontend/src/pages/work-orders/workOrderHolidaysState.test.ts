import { describe, expect, it } from "vitest";

import {
  type HolidayForm,
  type HolidayList,
  CALENDAR_CHOICE_OPTIONS,
  HOLIDAY_ANSWER_OPTIONS,
  HOLIDAY_KIND_OPTIONS,
  addAddedRow,
  addWorkingRow,
  answerOptions,
  calendarChoice,
  calendarDayText,
  canChooseUnchanged,
  changeText,
  dayChargeText,
  dayWhatText,
  formFromHolidayList,
  groupTitle,
  holidayFormProblem,
  holidayKindLabel,
  holidayListPayload,
  holidaysStatusText,
  linesText,
  notesForSavedVersion,
  periodText,
  removeAddedRow,
  removeWorkingRow,
  resultingRefreshKey,
  setCalendarChoice,
  setCalendarNote,
  showsChanges,
  typedWorkingRows,
  updateAddedRow,
  updateWorkingRow,
  yearsNotCompleteText,
  yearsText,
} from "./workOrderHolidaysState";

// Slice 7D Part 4, and since HOL-1 the Work Order's changes to PBL's holiday calendar: a holiday added, or a calendar
// holiday made a working day at the normal or the overtime rate (Q4). docs/agent/slices/hol-1-holiday-calendar.md.

const changed: HolidayList = {
  work_order_public_id: "wo1",
  holiday_list_public_id: "hl1",
  list_version: 2,
  holidays_answer_code: "CALENDAR_CHANGED",
  changes: [
    { change_public_id: "h1", change_code: "HOLIDAY_ADDED", holiday_date: "2027-01-26", holiday_kind_code: "NATIONAL", working_day_rate_code: null, description: "Republic Day" },
    { change_public_id: "h2", change_code: "WORKING_DAY", holiday_date: "2027-03-22", holiday_kind_code: null, working_day_rate_code: "OVERTIME_RATE", description: "Plant runs" },
    { change_public_id: "h3", change_code: "WORKING_DAY", holiday_date: "2027-11-01", holiday_kind_code: null, working_day_rate_code: "NORMAL_RATE", description: null },
  ],
  is_complete: true,
  missing_items: [],
};

const notAnswered: HolidayList = {
  ...changed,
  holiday_list_public_id: null,
  list_version: null,
  holidays_answer_code: null,
  changes: [],
  is_complete: false,
  missing_items: ["HOLIDAYS"],
};

const empty = (answer: string): HolidayForm => ({ answer, added: [], working: [] });

describe("the answer (decision 29, reworded by HOL-1)", () => {
  it("offers 'not answered yet' only until an answer is saved", () => {
    expect(answerOptions(notAnswered)).toEqual(HOLIDAY_ANSWER_OPTIONS);
    expect(answerOptions(changed).map((option) => option.code)).toEqual(["CALENDAR_UNCHANGED", "CALENDAR_CHANGED"]);
    expect(answerOptions(null)).toEqual(HOLIDAY_ANSWER_OPTIONS);
  });

  it("words the two answers as following, or changing, PBL's calendar", () => {
    expect(HOLIDAY_ANSWER_OPTIONS.map((option) => option.label)).toEqual([
      "Not answered yet",
      "The Work Order follows PBL's calendar unchanged",
      "The Work Order changes PBL's calendar as listed",
    ]);
  });

  it("shows the changes only for 'changes PBL's calendar as listed'", () => {
    expect(showsChanges(empty("CALENDAR_CHANGED"))).toBe(true);
    expect(showsChanges(empty("CALENDAR_UNCHANGED"))).toBe(false);
    expect(showsChanges(empty(""))).toBe(false);
  });

  it("allows 'follows unchanged' only with no change listed", () => {
    expect(canChooseUnchanged(empty("CALENDAR_CHANGED"))).toBe(true);
    expect(canChooseUnchanged(formFromHolidayList(changed))).toBe(false);
    expect(canChooseUnchanged({ ...empty("CALENDAR_CHANGED"), working: [{ key: "w", holiday_date: "2027-03-22", rate: "NORMAL_RATE", note: "" }] })).toBe(false);
  });
});

describe("the form", () => {
  it("is made from the list, its holidays added apart from its working days", () => {
    const form = formFromHolidayList(changed);
    expect(form.answer).toBe("CALENDAR_CHANGED");
    expect(form.added).toEqual([{ key: "h1", holiday_date: "2027-01-26", holiday_kind_code: "NATIONAL", description: "Republic Day" }]);
    expect(form.working).toEqual([
      { key: "h2", holiday_date: "2027-03-22", rate: "OVERTIME_RATE", note: "Plant runs" },
      { key: "h3", holiday_date: "2027-11-01", rate: "NORMAL_RATE", note: "" },
    ]);
    expect(formFromHolidayList(null)).toEqual(empty(""));
  });

  it("adds, edits and removes holidays added and working days typed in", () => {
    let form = addAddedRow(empty("CALENDAR_CHANGED"), "a1");
    form = updateAddedRow(form, "a1", { holiday_date: "2027-08-29", holiday_kind_code: "FESTIVAL" });
    form = addWorkingRow(form, "w1");
    form = updateWorkingRow(form, "w1", { holiday_date: "2027-08-15", rate: "NORMAL_RATE" });
    expect(form.added).toEqual([{ key: "a1", holiday_date: "2027-08-29", holiday_kind_code: "FESTIVAL", description: "" }]);
    expect(form.working).toEqual([{ key: "w1", holiday_date: "2027-08-15", rate: "NORMAL_RATE", note: "" }]);
    expect(removeWorkingRow(removeAddedRow(form, "a1"), "w1")).toEqual(empty("CALENDAR_CHANGED"));
  });

  it("chooses beside a calendar holiday: a working day at a rate, its note, or back to a holiday", () => {
    let form = setCalendarChoice(empty("CALENDAR_CHANGED"), "2027-03-22", "OVERTIME_RATE", "k1");
    expect(calendarChoice(form, "2027-03-22")).toEqual({ rate: "OVERTIME_RATE", note: "" });
    form = setCalendarNote(form, "2027-03-22", "Plant runs");
    form = setCalendarChoice(form, "2027-03-22", "NORMAL_RATE", "k2");
    // The same row, its rate changed and its note kept.
    expect(form.working).toEqual([{ key: "k1", holiday_date: "2027-03-22", rate: "NORMAL_RATE", note: "Plant runs" }]);
    expect(calendarChoice(form, "2027-05-01")).toEqual({ rate: "", note: "" });
    expect(setCalendarChoice(form, "2027-03-22", "", "k3").working).toEqual([]);
    expect(CALENDAR_CHOICE_OPTIONS.map((option) => option.label)).toEqual(["Holiday", "Working day, normal rate", "Working day, overtime rate"]);
  });

  it("lists as typed in only the working days not beside a calendar holiday", () => {
    const form = formFromHolidayList(changed);
    expect(typedWorkingRows(form, [{ holiday_date: "2027-03-22" }]).map((row) => row.holiday_date)).toEqual(["2027-11-01"]);
    // Before the calendar is read, every working day is listed by date, so none is hidden.
    expect(typedWorkingRows(form, []).map((row) => row.holiday_date)).toEqual(["2027-03-22", "2027-11-01"]);
  });
});

describe("what stops a save (the server checks everything again)", () => {
  it("needs an answer", () => {
    expect(holidayFormProblem(empty(""))).toBe("Choose whether the Work Order follows PBL's holiday calendar unchanged, or changes it as listed.");
  });

  it("refuses 'follows unchanged' with changes listed", () => {
    expect(holidayFormProblem({ ...formFromHolidayList(changed), answer: "CALENDAR_UNCHANGED" })).toBe(
      "Remove the changes listed, or choose that the Work Order changes PBL's calendar as listed.",
    );
    expect(holidayFormProblem(empty("CALENDAR_UNCHANGED"))).toBeNull();
  });

  it("needs every date, kind and rate", () => {
    expect(holidayFormProblem(addAddedRow(empty("CALENDAR_CHANGED"), "a"))).toBe("Enter a date for every holiday added, or remove the empty row.");
    expect(holidayFormProblem(addWorkingRow(empty("CALENDAR_CHANGED"), "w"))).toBe("Enter a date for every working day, or remove the empty row.");
    const kindless = updateAddedRow(addAddedRow(empty("CALENDAR_CHANGED"), "a"), "a", { holiday_date: "2027-08-29" });
    expect(holidayFormProblem(kindless)).toBe("Choose national or festival for every holiday added.");
    const rateless = updateWorkingRow(addWorkingRow(empty("CALENDAR_CHANGED"), "w"), "w", { holiday_date: "2027-08-15" });
    expect(holidayFormProblem(rateless)).toBe("Choose the normal rate or the overtime rate for the working day on 15 August 2027.");
  });

  it("refuses a date listed twice, as a holiday added and a working day too", () => {
    const form: HolidayForm = {
      answer: "CALENDAR_CHANGED",
      added: [{ key: "a", holiday_date: "2027-03-22", holiday_kind_code: "FESTIVAL", description: "" }],
      working: [{ key: "w", holiday_date: "2027-03-22", rate: "NORMAL_RATE", note: "" }],
    };
    expect(holidayFormProblem(form)).toBe("22 March 2027 is listed more than once. A date is either a holiday added or a working day: list it once.");
  });

  it("lets a complete list through", () => {
    expect(holidayFormProblem(formFromHolidayList(changed))).toBeNull();
    // "Changes as listed" with none entered may be saved: the server records it, and reports it missing.
    expect(holidayFormProblem(empty("CALENDAR_CHANGED"))).toBeNull();
  });
});

describe("the request body", () => {
  it("sends each change with its own parts, blank words as none", () => {
    const form = formFromHolidayList(changed);
    const body = holidayListPayload(updateAddedRow(form, "h1", { description: "   " }), 2);
    expect(body).toEqual({
      expected_list_version: 2,
      holidays_answer_code: "CALENDAR_CHANGED",
      changes: [
        { change_code: "HOLIDAY_ADDED", holiday_date: "2027-01-26", holiday_kind_code: "NATIONAL", description: null },
        { change_code: "WORKING_DAY", holiday_date: "2027-03-22", working_day_rate_code: "OVERTIME_RATE", description: "Plant runs" },
        { change_code: "WORKING_DAY", holiday_date: "2027-11-01", working_day_rate_code: "NORMAL_RATE", description: null },
      ],
    });
  });

  it("sends no change with 'follows unchanged'", () => {
    expect(holidayListPayload({ ...formFromHolidayList(changed), answer: "CALENDAR_UNCHANGED" }, 2).changes).toEqual([]);
    expect(holidayListPayload(empty("CALENDAR_UNCHANGED"), null)).toEqual({ expected_list_version: null, holidays_answer_code: "CALENDAR_UNCHANGED", changes: [] });
  });
});

describe("words", () => {
  it("says where the list stands", () => {
    expect(holidaysStatusText(null)).toBe("Holidays: not answered yet");
    expect(holidaysStatusText(notAnswered)).toBe("Holidays: not answered yet");
    expect(holidaysStatusText({ ...changed, holidays_answer_code: "CALENDAR_UNCHANGED", changes: [] })).toBe("Follows PBL's holiday calendar unchanged");
    expect(holidaysStatusText({ ...changed, changes: [] })).toBe("Changes PBL's calendar: none entered yet");
    expect(holidaysStatusText(changed)).toBe("Changes PBL's calendar: 1 holiday added, 2 working days");
    expect(holidaysStatusText({ ...changed, changes: changed.changes.slice(1, 2) })).toBe("Changes PBL's calendar: 1 working day");
  });

  it("writes each change as one line", () => {
    expect(changeText(changed.changes[0])).toBe("26 January 2027 - Holiday added - National holiday - Republic Day");
    expect(changeText(changed.changes[1])).toBe("22 March 2027 - Working day, overtime rate - Plant runs");
    expect(changeText(changed.changes[2])).toBe("1 November 2027 - Working day, normal rate");
    expect(holidayKindLabel("FESTIVAL")).toBe("Festival holiday");
    expect(holidayKindLabel(null)).toBe("-");
    expect(HOLIDAY_KIND_OPTIONS.map((option) => option.code)).toEqual(["NATIONAL", "FESTIVAL"]);
  });

  it("names a calendar day's holidays with where each applies", () => {
    const entry = (name: string, states: string[]) => ({
      holiday_name: name,
      holiday_kind_code: "FESTIVAL",
      applies_to_code: states.length ? "STATES" : "ALL_INDIA",
      state_codes: states,
      state_labels: states,
    });
    expect(calendarDayText({ entries: [entry("Holi", [])] })).toBe("Holi");
    expect(calendarDayText({ entries: [entry("Gujarat Day", ["Gujarat"]), entry("Maharashtra Day", ["Maharashtra"])] })).toBe(
      "Gujarat Day (Gujarat); Maharashtra Day (Maharashtra)",
    );
  });

  it("heads each group of lines", () => {
    expect(linesText([3])).toBe("Line 3");
    expect(linesText([1, 2, 4])).toBe("Lines 1, 2 and 4");
    expect(groupTitle({ line_numbers: [1, 3], state_label: "Gujarat", problem_code: null })).toBe("Lines 1 and 3 - Gujarat");
    expect(groupTitle({ line_numbers: [2], state_label: null, problem_code: "SITE_NOT_RECORDED" })).toBe("Line 2 - no site recorded");
    expect(groupTitle({ line_numbers: [2], state_label: null, problem_code: "SITE_STATE_NOT_RECOGNISED" })).toBe("Line 2 - site state not recognised");
  });

  it("says what a day is and how it is charged", () => {
    expect(dayWhatText({ name: "Holi", holiday_kind_code: "FESTIVAL", source_code: "CALENDAR" })).toBe("Holi - festival holiday, PBL's calendar");
    expect(dayWhatText({ name: null, holiday_kind_code: "NATIONAL", source_code: "WORK_ORDER" })).toBe("national holiday, added by this Work Order");
    expect(dayChargeText({ day_code: "HOLIDAY", working_day_rate_code: null, lines_without_overtime_rate: [] })).toBe("Holiday: as each line's off-day term says");
    expect(dayChargeText({ day_code: "WORKING_DAY", working_day_rate_code: "NORMAL_RATE", lines_without_overtime_rate: [] })).toBe("Working day, normal rate");
    expect(dayChargeText({ day_code: "WORKING_DAY", working_day_rate_code: "OVERTIME_RATE", lines_without_overtime_rate: [] })).toBe(
      "Working day, every hour at the line's overtime rate",
    );
    expect(dayChargeText({ day_code: "WORKING_DAY", working_day_rate_code: "OVERTIME_RATE", lines_without_overtime_rate: [2, 3] })).toBe(
      "Working day, every hour at the line's overtime rate. Lines 2 and 3 record no overtime rate for this day.",
    );
  });

  it("says which days are shown", () => {
    expect(periodText({ period_from: "2026-12-01", period_to: "2027-11-30", period_message: null })).toBe("1 December 2026 to 30 November 2027");
    expect(periodText({ period_from: null, period_to: null, period_message: "Record the contract start to see the holidays that apply." })).toBe(
      "Record the contract start to see the holidays that apply.",
    );
    expect(periodText({ period_from: "2026-12-01", period_to: "2027-12-31", period_message: "No end date is recorded, so the holidays are shown to 31 December 2027." })).toBe(
      "1 December 2026 to 31 December 2027. No end date is recorded, so the holidays are shown to 31 December 2027.",
    );
  });

  it("writes runs of years as ranges", () => {
    expect(yearsText([2027])).toBe("2027");
    expect(yearsText([2028, 2027])).toBe("2027 and 2028");
    expect(yearsText([2027, 2028, 2029, 2031])).toBe("2027 to 2029 and 2031");
    expect(yearsNotCompleteText([])).toBeNull();
    expect(yearsNotCompleteText([2027])).toBe(
      "PBL's holiday calendar for 2027 is not complete yet: the holidays shown for 2027 may change when Admin completes it.",
    );
  });
});

describe("the notes shown beside Save holidays (the owner's HOL-1 screen check)", () => {
  const note = { holiday_date: "2027-08-15", change_code: "WORKING_DAY", note_code: "DOES_NOTHING", message: "does nothing" };
  const resulting = (listVersion: number | null) => ({ list_version: listVersion, change_notes: [note] }) as never;

  it("are the notes on the version this save made, once worked out", () => {
    expect(notesForSavedVersion(resulting(3), 3)).toEqual([note]);
  });

  it("are none while the holidays that apply are still an earlier version's, or nothing was saved", () => {
    expect(notesForSavedVersion(resulting(2), 3)).toEqual([]);
    expect(notesForSavedVersion(resulting(3), null)).toEqual([]);
    expect(notesForSavedVersion(null, 3)).toEqual([]);
  });
});

describe("reading the holidays that apply again", () => {
  const parts = {
    workOrderPublicId: "wo1",
    contractVersion: 2,
    extensionCount: 1,
    lineDetailVersions: [1, null, 3],
    billingTermRevisions: [1, 2],
    holidayListVersion: 4,
  };

  it("changes when anything they are worked out from changes", () => {
    const key = resultingRefreshKey(parts);
    expect(resultingRefreshKey({ ...parts })).toBe(key);
    for (const change of [
      { contractVersion: 3 },
      { extensionCount: 2 },
      { lineDetailVersions: [1, 1, 3] },
      { billingTermRevisions: [1, 3] },
      { holidayListVersion: 5 },
      { workOrderPublicId: "wo2" },
    ]) {
      expect(resultingRefreshKey({ ...parts, ...change })).not.toBe(key);
    }
  });
});
