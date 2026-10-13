"""HOL-1 - the pure rules: PBL's calendar (`holiday_calendar/rules.py`) and the holidays that apply to a Work Order's
lines (`work_orders/holiday_rules.py`). No database and no clock.

docs/agent/slices/hol-1-holiday-calendar.md, sections 1.2, 5.1, 5.3 and 14.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.modules.holiday_calendar.rules import CalendarHoliday, holidays_for_state, year_changes, year_problem
from app.modules.work_orders import holiday_rules
from app.modules.work_orders.contract_period_rules import ContractGap

STATES = {"IN-GJ": "Gujarat", "IN-MH": "Maharashtra", "IN-TN": "Tamil Nadu", "IN-PB": "Punjab", "IN-KL": "Kerala"}


def _holiday(on: str, name: str = "Holiday", *, kind: str = "FESTIVAL", states: tuple[str, ...] = ()) -> CalendarHoliday:
    return CalendarHoliday(date.fromisoformat(on), kind, name, "STATES" if states else "ALL_INDIA", tuple(sorted(states)))


REPUBLIC_DAY = _holiday("2027-01-26", "Republic Day", kind="NATIONAL")
HOLI = _holiday("2027-03-22", "Holi")
GUJARAT_DAY = _holiday("2027-05-01", "Gujarat Day", states=("IN-GJ",))
MAHARASHTRA_DAY = _holiday("2027-05-01", "Maharashtra Day", kind="NATIONAL", states=("IN-MH",))
TAMIL_NEW_YEAR = _holiday("2027-04-14", "Tamil New Year", states=("IN-TN",))
BAISAKHI = _holiday("2027-04-14", "Baisakhi", states=("IN-PB",))


# --- A year's refusals (section 5.1) --------------------------------------------------------------------------------


def test_a_year_of_valid_holidays_is_accepted() -> None:
    holidays = [REPUBLIC_DAY, HOLI, GUJARAT_DAY, MAHARASHTRA_DAY, TAMIL_NEW_YEAR, BAISAKHI]
    assert year_problem(2027, holidays, state_labels=STATES) is None
    assert year_problem(2027, [], state_labels=STATES) is None


def test_a_national_holiday_may_apply_to_named_states_only() -> None:
    """1.2, point 2: Maharashtra's Shops and Establishments Act, 2017 counts 1 May among its national holidays."""
    assert year_problem(2027, [MAHARASHTRA_DAY], state_labels=STATES) is None


def test_one_date_may_be_a_holiday_for_different_states_under_different_names() -> None:
    assert year_problem(2027, [TAMIL_NEW_YEAR, BAISAKHI, _holiday("2027-04-14", "Vishu", states=("IN-KL",))], state_labels=STATES) is None


@pytest.mark.parametrize(
    "holidays, words",
    [
        ([_holiday("2026-12-25")], "25 December 2026 is not in 2027. Enter only the holidays of 2027 here."),
        ([CalendarHoliday(date(2027, 1, 26), "WEEKLY_OFF", "x", "ALL_INDIA", ())], "national or a festival holiday"),
        ([CalendarHoliday(date(2027, 1, 26), "NATIONAL", "   ", "ALL_INDIA", ())], "Give the holiday on 26 January 2027 a name."),
        ([CalendarHoliday(date(2027, 1, 26), "NATIONAL", "x" * 256, "ALL_INDIA", ())], "longer than 255 characters"),
        ([CalendarHoliday(date(2027, 1, 26), "NATIONAL", "x", "SOMEWHERE", ())], "applies to all of India or to the states named"),
        (
            [CalendarHoliday(date(2027, 1, 26), "NATIONAL", "x", "ALL_INDIA", ("IN-GJ",))],
            "The holiday on 26 January 2027 applies to all of India, so it names no states.",
        ),
        (
            [CalendarHoliday(date(2027, 5, 1), "FESTIVAL", "x", "STATES", ())],
            "Choose at least one state for the holiday on 1 May 2027, or make it apply to all of India.",
        ),
        (
            [CalendarHoliday(date(2027, 5, 1), "FESTIVAL", "x", "STATES", ("IN",))],
            "names IN, which is not a state or union territory the platform knows",
        ),
        (
            [CalendarHoliday(date(2027, 5, 1), "FESTIVAL", "x", "STATES", ("IN-GJ", "IN-GJ"))],
            "The holiday on 1 May 2027 names Gujarat twice.",
        ),
        ([REPUBLIC_DAY, _holiday("2027-01-26", "Another")], "Two holidays on 26 January 2027 apply to all of India. Keep one."),
        (
            [REPUBLIC_DAY, _holiday("2027-01-26", "A state day", states=("IN-TN",))],
            "26 January 2027 is already a holiday for all of India, so it cannot also be a holiday for Tamil Nadu alone.",
        ),
        ([GUJARAT_DAY, _holiday("2027-05-01", "Again", states=("IN-GJ", "IN-MH"))], "1 May 2027 is a holiday for Gujarat twice. Keep one."),
    ],
)
def test_each_refusal_names_the_date(holidays: list[CalendarHoliday], words: str) -> None:
    problem = year_problem(2027, holidays, state_labels=STATES)
    assert problem is not None and words in problem


def test_the_earliest_date_is_named_first() -> None:
    later, earlier = _holiday("2027-11-01", " "), CalendarHoliday(date(2027, 2, 1), "x", "y", "ALL_INDIA", ())
    assert "1 February 2027" in (year_problem(2027, [later, earlier], state_labels=STATES) or "")


# --- What a save changes --------------------------------------------------------------------------------------------


def test_a_save_reports_the_dates_added_removed_and_changed() -> None:
    before = [REPUBLIC_DAY, HOLI, GUJARAT_DAY]
    after = [REPUBLIC_DAY, _holiday("2027-03-22", "Holi (Dhuleti)"), TAMIL_NEW_YEAR]
    assert year_changes(before, after) == ([date(2027, 4, 14)], [date(2027, 5, 1)], [date(2027, 3, 22)])


@pytest.mark.parametrize(
    "changed",
    [
        _holiday("2027-05-01", "Gujarat Day", kind="NATIONAL", states=("IN-GJ",)),
        _holiday("2027-05-01", "Gujarat Day", states=("IN-GJ", "IN-MH")),
        _holiday("2027-05-01", "Gujarat Day"),
    ],
)
def test_a_change_of_kind_or_states_changes_the_date(changed: CalendarHoliday) -> None:
    assert year_changes([GUJARAT_DAY], [changed]) == ([], [], [date(2027, 5, 1)])


def test_the_same_holidays_in_another_order_change_nothing() -> None:
    assert year_changes([TAMIL_NEW_YEAR, BAISAKHI, HOLI], [HOLI, BAISAKHI, TAMIL_NEW_YEAR]) == ([], [], [])


def test_the_holidays_for_a_state_are_the_all_india_ones_and_its_own() -> None:
    holidays = [HOLI, GUJARAT_DAY, REPUBLIC_DAY, MAHARASHTRA_DAY, TAMIL_NEW_YEAR]
    assert holidays_for_state(holidays, "IN-GJ") == [REPUBLIC_DAY, HOLI, GUJARAT_DAY]
    assert holidays_for_state(holidays, "IN-MH") == [REPUBLIC_DAY, HOLI, MAHARASHTRA_DAY]
    # A site whose state is not known: the all-India ones only (1.2, point 8).
    assert holidays_for_state(holidays, None) == [REPUBLIC_DAY, HOLI]


# --- The window of days shown (1.2, point 9) -------------------------------------------------------------------------


def _change(on: str, code: str = "HOLIDAY_ADDED", *, kind: str | None = "FESTIVAL", rate: str | None = None, text: str | None = None):
    if code == "WORKING_DAY":
        kind, rate = None, rate or "NORMAL_RATE"
    return holiday_rules.Change(date.fromisoformat(on), code, kind, rate, text)


def test_no_window_without_a_contract_start() -> None:
    assert holiday_rules.window(contract_start=None, contract_end=date(2027, 3, 31), gaps=(), last_calendar_year=2027, changes=()) is None


def test_a_fixed_end_bounds_the_window() -> None:
    gap = ContractGap(date(2027, 4, 1), date(2027, 4, 14), 1)
    within = holiday_rules.window(
        contract_start=date(2027, 1, 1), contract_end=date(2027, 6, 30), gaps=(gap,), last_calendar_year=2030, changes=()
    )
    assert within is not None and (within.first_day, within.last_day, within.gaps) == (date(2027, 1, 1), date(2027, 6, 30), (gap,))
    assert within.holds(date(2027, 1, 1)) and within.holds(date(2027, 6, 30)) and within.holds(date(2027, 4, 15))
    assert not within.holds(date(2026, 12, 31)) and not within.holds(date(2027, 7, 1)) and not within.holds(date(2027, 4, 10))


@pytest.mark.parametrize(
    "last_calendar_year, changes, last_day",
    [
        (None, (), date(2026, 12, 31)),
        (2028, (), date(2028, 12, 31)),
        (2027, (_change("2029-08-15"),), date(2029, 12, 31)),
        (2025, (), date(2026, 12, 31)),
    ],
)
def test_an_open_end_runs_to_the_latest_of_the_calendar_the_start_and_the_changes(last_calendar_year, changes, last_day) -> None:
    within = holiday_rules.window(
        contract_start=date(2026, 12, 1), contract_end=None, gaps=(), last_calendar_year=last_calendar_year, changes=changes
    )
    assert within is not None and within.last_day == last_day


# --- The holidays that apply (section 5.3) ----------------------------------------------------------------------------

WINDOW = holiday_rules.Window(date(2027, 1, 1), date(2027, 12, 31), ())
CALENDAR = [REPUBLIC_DAY, HOLI, GUJARAT_DAY, MAHARASHTRA_DAY, TAMIL_NEW_YEAR]


def _days(changes=(), state: str | None = "IN-GJ", within: holiday_rules.Window = WINDOW):
    return [
        (day.holiday_date.isoformat(), day.day_code, day.source_code, day.kind_code, day.name, day.rate_code, day.note)
        for day in holiday_rules.resulting_days(CALENDAR, list(changes), state_code=state, within=within)
    ]


def test_with_no_change_the_days_are_the_calendars_for_the_state() -> None:
    assert _days() == [
        ("2027-01-26", "HOLIDAY", "CALENDAR", "NATIONAL", "Republic Day", None, None),
        ("2027-03-22", "HOLIDAY", "CALENDAR", "FESTIVAL", "Holi", None, None),
        ("2027-05-01", "HOLIDAY", "CALENDAR", "FESTIVAL", "Gujarat Day", None, None),
    ]
    assert [day[4] for day in _days(state="IN-MH")] == ["Republic Day", "Holi", "Maharashtra Day"]
    assert [day[4] for day in _days(state=None)] == ["Republic Day", "Holi"]


@pytest.mark.parametrize("rate", ["NORMAL_RATE", "OVERTIME_RATE"])
def test_a_calendar_holiday_made_a_working_day_stays_listed_as_a_working_day_at_its_rate(rate: str) -> None:
    days = _days([_change("2027-03-22", "WORKING_DAY", rate=rate, text="Plant runs")])
    assert days[1] == ("2027-03-22", "WORKING_DAY", "CALENDAR", "FESTIVAL", "Holi", rate, "Plant runs")
    assert [day[1] for day in days] == ["HOLIDAY", "WORKING_DAY", "HOLIDAY"]


def test_a_holiday_added_is_a_holiday_from_the_work_order() -> None:
    days = _days([_change("2027-08-29", text="Site foundation day")])
    assert days[-1] == ("2027-08-29", "HOLIDAY", "WORK_ORDER", "FESTIVAL", "Site foundation day", None, None)


def test_a_holiday_added_on_a_calendar_holiday_is_listed_once() -> None:
    days = _days([_change("2027-03-22", kind="NATIONAL", text="Holi again")])
    assert [day for day in days if day[0] == "2027-03-22"] == [("2027-03-22", "HOLIDAY", "CALENDAR", "FESTIVAL", "Holi", None, None)]


def test_a_working_day_on_another_states_holiday_changes_nothing_for_this_state() -> None:
    assert _days([_change("2027-04-14", "WORKING_DAY")]) == _days()
    # Gujarat Day worked: Maharashtra's 1 May is not the same holiday, but the date is the Work Order's change for
    # every line (decision 27), so Maharashtra's lines work it too.
    worked = _days([_change("2027-05-01", "WORKING_DAY")], state="IN-MH")
    assert worked[-1][:5] == ("2027-05-01", "WORKING_DAY", "CALENDAR", "NATIONAL", "Maharashtra Day")


def test_only_days_inside_the_contract_are_shown() -> None:
    within = holiday_rules.Window(date(2027, 1, 26), date(2027, 5, 1), (ContractGap(date(2027, 3, 20), date(2027, 3, 25), 1),))
    days = _days([_change("2027-01-25"), _change("2027-03-21"), _change("2027-05-01", text="x")], within=within)
    # The first and last day are inside; a gap is not; a change outside the window is not shown.
    assert [day[0] for day in days] == ["2027-01-26", "2027-05-01"]


# --- What a change does (1.2, point 6) -------------------------------------------------------------------------------


def test_a_working_day_not_in_the_calendar_for_any_site_does_nothing() -> None:
    worked = _change("2027-08-15", "WORKING_DAY")
    assert holiday_rules.working_day_does_nothing(worked, CALENDAR, ["IN-GJ", None])
    assert not holiday_rules.working_day_does_nothing(_change("2027-03-22", "WORKING_DAY"), CALENDAR, ["IN-GJ"])
    # Tamil New Year is a holiday only in Tamil Nadu.
    assert holiday_rules.working_day_does_nothing(_change("2027-04-14", "WORKING_DAY"), CALENDAR, ["IN-GJ", "IN-MH"])
    assert not holiday_rules.working_day_does_nothing(_change("2027-04-14", "WORKING_DAY"), CALENDAR, ["IN-GJ", "IN-TN"])
    # A holiday added is never "does nothing".
    assert not holiday_rules.working_day_does_nothing(_change("2027-08-15"), CALENDAR, ["IN-GJ"])


def test_a_holiday_added_that_the_calendar_has_for_every_site_is_noted() -> None:
    assert holiday_rules.added_holiday_already_in_calendar(_change("2027-03-22"), CALENDAR, ["IN-GJ", "IN-MH", None])
    assert holiday_rules.added_holiday_already_in_calendar(_change("2027-05-01"), CALENDAR, ["IN-GJ", "IN-MH"])
    assert not holiday_rules.added_holiday_already_in_calendar(_change("2027-05-01"), CALENDAR, ["IN-GJ", None])
    assert not holiday_rules.added_holiday_already_in_calendar(_change("2027-08-15"), CALENDAR, ["IN-GJ"])
    # With no site at all nothing can be said of every site.
    assert not holiday_rules.added_holiday_already_in_calendar(_change("2027-03-22"), CALENDAR, [])
    assert not holiday_rules.added_holiday_already_in_calendar(_change("2027-03-22", "WORKING_DAY"), CALENDAR, ["IN-GJ"])


# --- The overtime rate a working day needs (1.2, point 15) ------------------------------------------------------------


def _period(number: int, effective_from: str | None, uom: str | None = "DAY", method: str | None = "RATE_PER_HOUR", amount="500", percent=None):
    return holiday_rules.TermPeriod(
        period_number=number,
        effective_from=date.fromisoformat(effective_from) if effective_from else None,
        billing_uom_code=uom,
        overtime_rate_method_code=method,
        overtime_rate_amount=Decimal(amount) if amount is not None else None,
        overtime_rate_percent=Decimal(percent) if percent is not None else None,
    )


ON = date(2027, 3, 22)


@pytest.mark.parametrize(
    "periods, expected",
    [
        ([], False),
        ([_period(1, None)], True),
        ([_period(1, None, method="PERCENT_OF_NORMAL", amount=None, percent="150")], True),
        ([_period(1, None, method="RATE_PER_HOUR", amount=None)], False),
        ([_period(1, None, method="PERCENT_OF_NORMAL", amount=None, percent=None)], False),
        ([_period(1, None, method="NONE", amount=None)], False),
        ([_period(1, None, method=None, amount=None)], False),
        ([_period(1, None, uom="HOUR", method=None, amount=None)], False),
        ([_period(1, None, uom=None, method=None, amount=None)], False),
        # A later period from after the day: period 1 still governs it.
        ([_period(1, None), _period(2, "2027-04-01", method="NONE", amount=None)], True),
        # A later period from before the day governs it.
        ([_period(1, None), _period(2, "2027-03-01", method="NONE", amount=None)], False),
        ([_period(1, None, method="NONE", amount=None), _period(2, "2027-03-22")], True),
    ],
)
def test_an_overtime_rate_is_one_recorded_for_the_period_the_day_falls_in(periods, expected: bool) -> None:
    assert holiday_rules.has_overtime_rate(periods, ON) is expected
