import { describe, expect, it } from "vitest";

import {
  type CalendarAnswer,
  type CalendarYear,
  type YearForm,
  addRow,
  appliesText,
  calendarPageAfter,
  calendarPageSaved,
  changedDates,
  formFromYear,
  initialCalendarPage,
  passedDaysWarning,
  pickerYears,
  removeRow,
  startYearProblem,
  toggleState,
  updateRow,
  yearFormChanged,
  yearFormProblem,
  yearFromSearch,
  yearPayload,
  yearStateText,
  yearToShow,
} from "./holidayCalendarState";

// PBL's holiday calendar page (HOL-1): the form's checks are the server's (docs/agent/slices/hol-1-holiday-calendar.md,
// section 5.1), and the page keeps its form across reads as the reminder settings page does.

const STATES = { "IN-GJ": "Gujarat", "IN-MH": "Maharashtra", "IN-TN": "Tamil Nadu" };

const year: CalendarYear = {
  calendar_year: 2027,
  year_public_id: "y1",
  year_version: 2,
  is_complete: false,
  complete_marked_by_display_name: null,
  complete_marked_at: null,
  holiday_count: 3,
  updated_by_display_name: "Admin User 1",
  updated_at: "2026-10-02T10:00:00Z",
  today: "2027-03-01",
  holidays: [
    { holiday_public_id: "h1", holiday_date: "2027-01-26", holiday_kind_code: "NATIONAL", holiday_kind_label: "National holiday", holiday_name: "Republic Day", applies_to_code: "ALL_INDIA", states: [] },
    { holiday_public_id: "h2", holiday_date: "2027-03-22", holiday_kind_code: "FESTIVAL", holiday_kind_label: "Festival holiday", holiday_name: "Holi", applies_to_code: "ALL_INDIA", states: [] },
    {
      holiday_public_id: "h3",
      holiday_date: "2027-05-01",
      holiday_kind_code: "NATIONAL",
      holiday_kind_label: "National holiday",
      holiday_name: "Maharashtra Day",
      applies_to_code: "STATES",
      states: [{ state_code: "IN-MH", state_label: "Maharashtra" }],
    },
  ],
};

const notStarted: CalendarYear = { ...year, year_public_id: null, year_version: null, holiday_count: 0, updated_at: null, updated_by_display_name: null, holidays: [] };

function row(form: YearForm, key: string, change: Parameters<typeof updateRow>[2]): YearForm {
  return updateRow(form, key, change);
}

describe("the year picked", () => {
  it("is read from the address, within 2000 to 2100", () => {
    expect(yearFromSearch("?year=2027")).toBe(2027);
    expect(yearFromSearch("")).toBeNull();
    expect(yearFromSearch("?year=1999")).toBeNull();
    expect(yearFromSearch("?year=27")).toBeNull();
    expect(yearFromSearch("?year=2027x")).toBeNull();
  });

  it("is the current year when none is asked for, and never a year the calendar cannot keep (HOL1-R2-001)", () => {
    expect(yearToShow(null, "2026-10-02")).toBe(2026);
    expect(yearToShow(2027, "2026-10-02")).toBe(2027);
    expect(yearToShow(null, "2100-12-31")).toBe(2100);
    // From 2101 the server refuses the current year; the page reads 2100, which it keeps, instead.
    expect(yearToShow(null, "2101-01-01")).toBe(2100);
    expect(yearToShow(null, "1999-12-31")).toBe(2000);
  });

  it("says where each year stands", () => {
    expect(yearStateText(notStarted)).toBe("Not set up");
    expect(yearStateText(year)).toBe("Being entered (version 2)");
    expect(yearStateText({ ...year, is_complete: true })).toBe("Complete (version 2)");
  });

  it("checks a year typed to open", () => {
    expect(startYearProblem("2028")).toBeNull();
    expect(startYearProblem(" 2028 ")).toBeNull();
    expect(startYearProblem("28")).toBe("Type a year of four digits.");
    expect(startYearProblem("2101")).toBe("Choose a year from 2000 to 2100.");
  });

  it("offers the year shown even when the server does not list it", () => {
    const answer: CalendarAnswer = { years: { today: "2026-10-02", years: [{ ...notStarted, calendar_year: 2026 }] }, year, states: [] };
    expect(pickerYears(answer).map((item) => item.calendar_year)).toEqual([2026, 2027]);
  });
});

describe("the form", () => {
  it("is made from the year", () => {
    const form = formFromYear(year);
    expect(form.complete).toBe(false);
    expect(form.rows[2]).toEqual({ key: "h3", date: "2027-05-01", kind: "NATIONAL", name: "Maharashtra Day", appliesTo: "STATES", states: ["IN-MH"] });
    expect(appliesText(year.holidays[2])).toBe("Maharashtra");
    expect(appliesText(year.holidays[0])).toBe("All of India");
  });

  it("adds a festival for all of India, edits and removes rows", () => {
    let form = addRow(formFromYear(notStarted), "n1");
    expect(form.rows).toEqual([{ key: "n1", date: "", kind: "FESTIVAL", name: "", appliesTo: "ALL_INDIA", states: [] }]);
    form = row(form, "n1", { date: "2027-04-14", name: "Tamil New Year", appliesTo: "STATES" });
    form = toggleState(toggleState(form, "n1", "IN-TN"), "n1", "IN-GJ");
    expect(form.rows[0].states).toEqual(["IN-TN", "IN-GJ"]);
    form = toggleState(form, "n1", "IN-GJ");
    expect(form.rows[0].states).toEqual(["IN-TN"]);
    // All of India names no states.
    expect(row(form, "n1", { appliesTo: "ALL_INDIA" }).rows[0].states).toEqual([]);
    expect(removeRow(form, "n1").rows).toEqual([]);
  });
});

describe("what stops a save (the server's own checks)", () => {
  const base = formFromYear(year);

  it("lets a valid year through - a national holiday for one state included", () => {
    expect(yearFormProblem(base, 2027, STATES)).toBeNull();
    expect(yearFormProblem(formFromYear(notStarted), 2027, STATES)).toBeNull();
  });

  it.each([
    [{ date: "" }, "Enter a date for every holiday, or remove the empty row."],
    [{ date: "2026-12-25" }, "25 December 2026 is not in 2027. Enter only the holidays of 2027 here."],
    [{ kind: "" }, "Choose whether the holiday on 26 January 2027 is a national or a festival holiday."],
    [{ name: "  " }, "Give the holiday on 26 January 2027 a name."],
    [{ appliesTo: "STATES" }, "Choose at least one state for the holiday on 26 January 2027, or make it apply to all of India."],
  ])("refuses %o", (change, message) => {
    expect(yearFormProblem(row(base, "h1", change), 2027, STATES)).toBe(message);
  });

  it("refuses an unknown state", () => {
    expect(yearFormProblem(row(base, "h3", { states: ["IN-XX"] }), 2027, STATES)).toBe(
      "The holiday on 1 May 2027 names IN-XX, which is not a state or union territory the platform knows.",
    );
  });

  it("refuses a date that is a holiday twice for one state", () => {
    const twoAllIndia = row(addRow(base, "n"), "n", { date: "2027-01-26", name: "Another" });
    expect(yearFormProblem(twoAllIndia, 2027, STATES)).toBe("Two holidays on 26 January 2027 apply to all of India. Keep one.");
    const allIndiaAndState = row(addRow(base, "n"), "n", { date: "2027-03-22", name: "Dhuleti", appliesTo: "STATES", states: ["IN-GJ"] });
    expect(yearFormProblem(allIndiaAndState, 2027, STATES)).toBe(
      "22 March 2027 is already a holiday for all of India, so it cannot also be a holiday for Gujarat alone.",
    );
    const stateTwice = row(addRow(base, "n"), "n", { date: "2027-05-01", name: "Labour Day", appliesTo: "STATES", states: ["IN-MH"] });
    expect(yearFormProblem(stateTwice, 2027, STATES)).toBe("1 May 2027 is a holiday for Maharashtra twice. Keep one.");
    // The same date for another state is fine.
    const other = row(addRow(base, "n"), "n", { date: "2027-05-01", name: "Gujarat Day", appliesTo: "STATES", states: ["IN-GJ"] });
    expect(yearFormProblem(other, 2027, STATES)).toBeNull();
  });
});

describe("the request body and what a save changes", () => {
  it("sends names trimmed and states only for 'these states'", () => {
    const form = row(row(formFromYear(year), "h2", { name: " Holi " }), "h3", { states: ["IN-TN", "IN-MH"] });
    expect(yearPayload({ ...form, complete: true }, 2)).toEqual({
      expected_version: 2,
      is_complete: true,
      holidays: [
        { holiday_date: "2027-01-26", holiday_kind_code: "NATIONAL", holiday_name: "Republic Day", applies_to_code: "ALL_INDIA", state_codes: [] },
        { holiday_date: "2027-03-22", holiday_kind_code: "FESTIVAL", holiday_name: "Holi", applies_to_code: "ALL_INDIA", state_codes: [] },
        { holiday_date: "2027-05-01", holiday_kind_code: "NATIONAL", holiday_name: "Maharashtra Day", applies_to_code: "STATES", state_codes: ["IN-MH", "IN-TN"] },
      ],
    });
  });

  it("reports the dates added, removed and changed, as the server counts them", () => {
    let form = formFromYear(year);
    expect(changedDates(form, year)).toEqual([]);
    expect(yearFormChanged(form, year)).toBe(false);
    form = row(form, "h2", { name: "Holi (Dhuleti)" });
    form = removeRow(form, "h1");
    form = row(addRow(form, "n"), "n", { date: "2027-10-02", name: "Gandhi Jayanti", kind: "NATIONAL" });
    expect(changedDates(form, year)).toEqual(["2027-01-26", "2027-03-22", "2027-10-02"]);
    expect(yearFormChanged(form, year)).toBe(true);
    // The complete mark alone is a change; an empty new row is one too, to be filled in or removed.
    expect(yearFormChanged({ ...formFromYear(year), complete: true }, year)).toBe(true);
    expect(yearFormChanged(addRow(formFromYear(year), "e"), year)).toBe(true);
  });

  it("warns when a change touches a day already passed (Q3)", () => {
    expect(passedDaysWarning(formFromYear(year), year)).toBeNull();
    // Today is 1 March 2027 in this year's reading: Republic Day has passed, Holi has not.
    expect(passedDaysWarning(row(formFromYear(year), "h2", { name: "Dhuleti" }), year)).toBeNull();
    expect(passedDaysWarning(removeRow(formFromYear(year), "h1"), year)).toBe(
      "This changes a day already passed: 26 January 2027. Every Work Order shows the calendar as it is now.",
    );
  });
});

describe("the page as reads arrive", () => {
  const answer: CalendarAnswer = { years: { today: "2027-03-01", years: [year] }, year, states: [] };

  it("takes its form from each answer, and clears both when another read starts", () => {
    const loaded = calendarPageAfter(initialCalendarPage(), { kind: "answer", answer });
    expect(loaded.form).toEqual(formFromYear(year));
    const edited = { ...loaded, form: removeRow(loaded.form!, "h1") };
    const reading = calendarPageAfter(edited, { kind: "loading" });
    expect(reading.view.answer).toBeNull();
    expect(reading.form).toBeNull();
  });

  it("keeps the year and the unsaved form while the same session reads again after a stale save", () => {
    const loaded = calendarPageAfter(initialCalendarPage(), { kind: "answer", answer });
    const edited = { ...loaded, form: removeRow(loaded.form!, "h1") };
    const reading = calendarPageAfter(edited, { kind: "loading" }, true);
    expect(reading.view.answer).toEqual(answer);
    expect(reading.form).toEqual(edited.form);
  });

  it("shows a save's year, its form, and its summary in the picker", () => {
    const loaded = calendarPageAfter(initialCalendarPage(), { kind: "answer", answer });
    const saved: CalendarYear = { ...year, year_version: 3, is_complete: true, holidays: year.holidays.slice(1), holiday_count: 2 };
    const after = calendarPageSaved(loaded, saved);
    expect(after.view.answer?.year).toEqual(saved);
    expect(after.form).toEqual(formFromYear(saved));
    expect(after.view.answer?.years.years[0]).toMatchObject({ calendar_year: 2027, year_version: 3, is_complete: true, holiday_count: 2 });
    // A save of another year changes nothing shown.
    expect(calendarPageSaved(loaded, { ...saved, calendar_year: 2028 })).toBe(loaded);
  });

  it("adds a year started from nothing to the picker", () => {
    const fresh: CalendarAnswer = { years: { today: "2027-03-01", years: [] }, year: notStarted, states: [] };
    const loaded = calendarPageAfter(initialCalendarPage(), { kind: "answer", answer: fresh });
    const after = calendarPageSaved(loaded, { ...notStarted, year_public_id: "y9", year_version: 1 });
    expect(after.view.answer?.years.years.map((item) => item.calendar_year)).toEqual([2027]);
  });
});
