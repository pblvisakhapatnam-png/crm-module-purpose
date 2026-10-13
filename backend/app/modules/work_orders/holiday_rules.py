"""The holidays that apply to a Work Order's lines, pure (HOL-1).

docs/agent/slices/hol-1-holiday-calendar.md, section 5.3. No database and no clock, as `contract_period_rules.py`:
the service hands in PBL's calendar, the Work Order's changes to it, the contract's dates and gaps, and a line's
billing-term periods, and gets back the days.

For a line whose site is in state S, over the contract period:

    every calendar holiday applying to all of India or to S        a holiday, unless
      the Work Order makes that date a working day                   then a working day, at the rate it says
    plus each date the Work Order adds                               a holiday
    on days inside the contract (not before its start, not after its end, not in a gap before an extension)

A holiday is charged by the line's off-day term (answer 24). A calendar holiday the Work Order makes a working day is
charged at the normal rate, or - every hour of it - at the line's own overtime rate (Q4). Log sheets (8C) will call
this to mark a day as a holiday or a working day; billing (8D) will charge it so. Nothing here is calculated.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable

from app.modules.holiday_calendar.rules import CalendarHoliday, holidays_for_state
from app.modules.work_orders.contract import (
    WORK_ORDER_DAY_HOLIDAY,
    WORK_ORDER_DAY_SOURCE_CALENDAR,
    WORK_ORDER_DAY_SOURCE_WORK_ORDER,
    WORK_ORDER_DAY_WORKING,
    WORK_ORDER_HOLIDAY_CHANGE_ADDED,
    WORK_ORDER_HOLIDAY_CHANGE_WORKING_DAY,
    WORK_ORDER_LINE_BILLING_UOM_HOUR,
    WORK_ORDER_LINE_RATE_PER_HOUR,
    WORK_ORDER_LINE_RATE_PERCENT_OF_NORMAL,
)
from app.modules.work_orders.contract_period_rules import ContractGap, gap_containing


@dataclass(frozen=True)
class Change:
    """One of the Work Order's changes to PBL's calendar."""

    holiday_date: date
    change_code: str
    kind_code: str | None
    rate_code: str | None
    description: str | None


@dataclass(frozen=True)
class Day:
    """One day that is not an ordinary working day for a line - or a calendar holiday the Work Order works."""

    holiday_date: date
    day_code: str
    source_code: str
    kind_code: str | None
    # The calendar holiday's name, or an added holiday's description.
    name: str | None
    # A working day's rate and note; None for a holiday.
    rate_code: str | None
    note: str | None


@dataclass(frozen=True)
class Window:
    first_day: date
    last_day: date
    gaps: tuple[ContractGap, ...]

    def holds(self, day: date) -> bool:
        return self.first_day <= day <= self.last_day and gap_containing(day, self.gaps) is None


def window(
    *,
    contract_start: date | None,
    contract_end: date | None,
    gaps: Iterable[ContractGap],
    last_calendar_year: int | None,
    changes: Iterable[Change],
) -> Window | None:
    """The days the holidays are shown for: the contract period, without any gap before an extension (1.2, point 9).
    None with no start recorded - "inside the contract" is not knowable without one. With no fixed end, it runs to the
    end of the last year started in PBL's calendar, or of the start's year, or of the last change's - whichever is
    latest - so every change the Work Order lists is shown."""
    if contract_start is None:
        return None
    if contract_end is not None:
        last_day = contract_end
    else:
        years = [contract_start.year, *(change.holiday_date.year for change in changes)]
        if last_calendar_year is not None:
            years.append(last_calendar_year)
        last_day = date(max(years), 12, 31)
    return Window(contract_start, last_day, tuple(gaps))


def resulting_days(calendar: Iterable[CalendarHoliday], changes: Iterable[Change], *, state_code: str | None, within: Window) -> list[Day]:
    """The days for a line whose site is in `state_code` (None: not known - the all-India holidays only), earliest
    first."""
    by_date = {change.holiday_date: change for change in changes}
    days: list[Day] = []
    calendar_dates: set[date] = set()
    for holiday in holidays_for_state(calendar, state_code):
        if not within.holds(holiday.holiday_date):
            continue
        calendar_dates.add(holiday.holiday_date)
        change = by_date.get(holiday.holiday_date)
        if change is not None and change.change_code == WORK_ORDER_HOLIDAY_CHANGE_WORKING_DAY:
            days.append(
                Day(
                    holiday.holiday_date,
                    WORK_ORDER_DAY_WORKING,
                    WORK_ORDER_DAY_SOURCE_CALENDAR,
                    holiday.kind_code,
                    holiday.name,
                    change.rate_code,
                    change.description,
                )
            )
        else:
            days.append(
                Day(holiday.holiday_date, WORK_ORDER_DAY_HOLIDAY, WORK_ORDER_DAY_SOURCE_CALENDAR, holiday.kind_code, holiday.name, None, None)
            )
    for change in by_date.values():
        if (
            change.change_code == WORK_ORDER_HOLIDAY_CHANGE_ADDED
            and change.holiday_date not in calendar_dates
            and within.holds(change.holiday_date)
        ):
            days.append(
                Day(
                    change.holiday_date,
                    WORK_ORDER_DAY_HOLIDAY,
                    WORK_ORDER_DAY_SOURCE_WORK_ORDER,
                    change.kind_code,
                    change.description,
                    None,
                    None,
                )
            )
    return sorted(days, key=lambda day: day.holiday_date)


# --- What a change does --------------------------------------------------------------------------------------------


def working_day_does_nothing(change: Change, calendar: Iterable[CalendarHoliday], state_codes: Iterable[str | None]) -> bool:
    """A working day on a date that is a holiday in PBL's calendar for none of the Work Order's sites (1.2, point 6)."""
    holidays = list(calendar)
    return change.change_code == WORK_ORDER_HOLIDAY_CHANGE_WORKING_DAY and not any(
        holiday.holiday_date == change.holiday_date and holiday.applies_to(state_code)
        for state_code in state_codes
        for holiday in holidays
    )


def added_holiday_already_in_calendar(
    change: Change, calendar: Iterable[CalendarHoliday], state_codes: Iterable[str | None]
) -> bool:
    """A holiday added on a date PBL's calendar already has for every site of the Work Order (1.2, point 6). With no
    site at all, nothing can be said of every site."""
    holidays = list(calendar)
    codes = list(state_codes)
    return (
        change.change_code == WORK_ORDER_HOLIDAY_CHANGE_ADDED
        and bool(codes)
        and all(
            any(holiday.holiday_date == change.holiday_date and holiday.applies_to(state_code) for holiday in holidays)
            for state_code in codes
        )
    )


# --- The overtime rate a working day needs ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TermPeriod:
    """The part of one billing-terms period this rule reads. Period 1 has no date of its own: it starts with the
    contract."""

    period_number: int
    effective_from: date | None
    billing_uom_code: str | None
    overtime_rate_method_code: str | None
    overtime_rate_amount: Decimal | None
    overtime_rate_percent: Decimal | None


def has_overtime_rate(periods: Iterable[TermPeriod], on: date) -> bool:
    """Whether a line's billing terms record an overtime rate for the period `on` falls in (1.2, point 15): a rate per
    hour with its amount, or a percentage of the normal rate with its percentage. Not when overtime is not in the Work
    Order or not recorded yet, when the line has no terms, or on an hourly line, which has no overtime."""
    in_force = [period for period in periods if period.effective_from is None or period.effective_from <= on]
    if not in_force:
        return False
    period = max(in_force, key=lambda item: item.period_number)
    if period.billing_uom_code in (None, WORK_ORDER_LINE_BILLING_UOM_HOUR):
        return False
    if period.overtime_rate_method_code == WORK_ORDER_LINE_RATE_PER_HOUR:
        return period.overtime_rate_amount is not None
    if period.overtime_rate_method_code == WORK_ORDER_LINE_RATE_PERCENT_OF_NORMAL:
        return period.overtime_rate_percent is not None
    return False
