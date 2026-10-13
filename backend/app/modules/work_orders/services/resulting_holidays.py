"""HOL-1: the holidays that apply to a Work Order's lines - PBL's calendar as the Work Order changes it.

docs/agent/slices/hol-1-holiday-calendar.md, section 5.3. A read: it never writes. For each group of lines whose sites
are in one state, over the contract period, the days `holiday_rules.resulting_days` gives - with the notes beside them:
the years whose calendar is not complete (Q2), the changes that do nothing more than the calendar (1.2, point 6), the
lines whose state is not known (point 8), and the lines with no overtime rate on a working day charged at it (point 15).

A line's state is read from its site address on the Account exactly as the line's detail reads the site, and matched
to a state as 8A's allocation matches it (the calendar's `state_for_address`). The calendar is read through its
service's public reads, never its tables. Imports `services/common.py` and nothing else under services/.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.holiday_calendar.contract import FIRST_YEAR, LAST_YEAR
from app.modules.holiday_calendar.rules import CalendarHoliday
from app.modules.holiday_calendar.service import calendar_between, last_year_started, list_states, state_for_address
from app.modules.work_orders import holiday_rules
from app.modules.work_orders.contract import (
    WORK_ORDER_CHANGE_ALREADY_IN_CALENDAR,
    WORK_ORDER_CHANGE_DOES_NOTHING,
    WORK_ORDER_HOLIDAY_PERIOD_NO_START,
    WORK_ORDER_HOLIDAY_PERIOD_OPEN_END,
    WORK_ORDER_LINE_SITE_ADDRESS_TYPES,
    WORK_ORDER_SITE_NOT_RECORDED,
    WORK_ORDER_SITE_STATE_NOT_RECOGNISED,
    WORK_ORDER_WORKING_DAY_OVERTIME_RATE,
)
from app.modules.work_orders.contract_period_rules import format_contract_date
from app.modules.work_orders.repository import (
    get_work_order_holiday_list_snapshot,
    list_work_order_billing_term_rows,
    list_work_order_line_detail_rows,
)
from app.modules.work_orders.schemas import (
    WorkOrderCalendarDay,
    WorkOrderCalendarHolidayEntry,
    WorkOrderHolidayChangeNote,
    WorkOrderHolidayGroup,
    WorkOrderResultingDay,
    WorkOrderResultingHolidaysResponse,
)
from app.modules.work_orders.services.common import (
    _account_reference_maps,
    _get_work_order_and_id,
    _usable_address,
    contract_bounds_for_work_order,
    contract_gaps_for_work_order,
)

_DOES_NOTHING = "Not a holiday in PBL's calendar for any site of this Work Order: making it a working day does nothing."
_ALREADY_IN_CALENDAR = "Already a holiday in PBL's calendar for every site of this Work Order."


@dataclass(frozen=True)
class _Line:
    line_id: int
    line_number: int
    state_code: str | None
    state_label: str | None
    problem_code: str | None
    # The site's state as written, when the platform does not recognise it.
    state_text: str | None


def _lines_text(numbers: list[int]) -> str:
    if len(numbers) == 1:
        return f"Line {numbers[0]}"
    return "Lines " + ", ".join(str(number) for number in numbers[:-1]) + f" and {numbers[-1]}"


def _lines(db: Session, *, account_public_id: UUID | None, work_order_id: int) -> list[_Line]:
    """Each line with its site's state, or why it is not known."""
    addresses, _gstins = _account_reference_maps(db, account_public_id)
    lines: list[_Line] = []
    for row in list_work_order_line_detail_rows(db, work_order_id=work_order_id):
        site = _usable_address(addresses, row.get("site_address_public_id"), WORK_ORDER_LINE_SITE_ADDRESS_TYPES)
        number, line_id = int(row["line_number"]), int(row["work_order_line_id"])
        if site is None:
            lines.append(_Line(line_id, number, None, None, WORK_ORDER_SITE_NOT_RECORDED, None))
            continue
        state = state_for_address(db, site.state)
        if state is None:
            lines.append(_Line(line_id, number, None, None, WORK_ORDER_SITE_STATE_NOT_RECOGNISED, site.state or ""))
        else:
            lines.append(_Line(line_id, number, state.state_code, state.state_label, None, None))
    return lines


def _groups(lines: list[_Line]) -> list[list[_Line]]:
    """Lines in the same state together; lines whose state is not known together by why, and by the state written."""
    grouped: dict[tuple[Any, ...], list[_Line]] = {}
    for line in lines:
        grouped.setdefault((line.state_code, line.problem_code, line.state_text), []).append(line)
    return sorted(grouped.values(), key=lambda members: min(line.line_number for line in members))


def _problem_message(members: list[_Line]) -> str | None:
    first = members[0]
    lines = _lines_text([line.line_number for line in members])
    if first.problem_code == WORK_ORDER_SITE_NOT_RECORDED:
        return (
            f"{lines}: no site recorded, so only the all-India holidays are shown, as this Work Order changes them, with "
            "the holidays it adds. Record the site on the line's details."
        )
    if first.problem_code == WORK_ORDER_SITE_STATE_NOT_RECOGNISED:
        return (
            f"{lines}: the site's state '{first.state_text}' is not a state or union territory the platform knows, so only "
            "the all-India holidays are shown, as this Work Order changes them, with the holidays it adds. Correct the "
            "site address on the Account."
        )
    return None


def _term_periods(db: Session, *, work_order_id: int) -> dict[int, list[holiday_rules.TermPeriod]]:
    periods: dict[int, list[holiday_rules.TermPeriod]] = {}
    for row in list_work_order_billing_term_rows(db, work_order_id=work_order_id):
        periods.setdefault(int(row["work_order_line_id"]), []).append(
            holiday_rules.TermPeriod(
                period_number=int(row["period_number"]),
                effective_from=row.get("effective_from"),
                billing_uom_code=row.get("billing_uom_code"),
                overtime_rate_method_code=row.get("overtime_rate_method_code"),
                overtime_rate_amount=row.get("overtime_rate_amount"),
                overtime_rate_percent=row.get("overtime_rate_percent"),
            )
        )
    return periods


def _calendar_days(
    holidays: Iterable[CalendarHoliday], within: holiday_rules.Window, lines: list[_Line], labels: dict[str, str]
) -> list[WorkOrderCalendarDay]:
    """The calendar holidays inside the contract for at least one of the Work Order's lines, by date."""
    by_date: dict[date, tuple[list[WorkOrderCalendarHolidayEntry], set[int]]] = {}
    for holiday in holidays:
        if not within.holds(holiday.holiday_date):
            continue
        numbers = {line.line_number for line in lines if holiday.applies_to(line.state_code)}
        if not numbers:
            continue
        entries, line_numbers = by_date.setdefault(holiday.holiday_date, ([], set()))
        entries.append(
            WorkOrderCalendarHolidayEntry(
                holiday_name=holiday.name,
                holiday_kind_code=holiday.kind_code,
                applies_to_code=holiday.applies_to_code,
                state_codes=list(holiday.state_codes),
                state_labels=[labels.get(code, code) for code in holiday.state_codes],
            )
        )
        line_numbers.update(numbers)
    return [
        WorkOrderCalendarDay(holiday_date=on, entries=entries, line_numbers=sorted(numbers))
        for on, (entries, numbers) in sorted(by_date.items())
    ]


def get_work_order_resulting_holidays(db: Session, work_order_public_id: UUID) -> WorkOrderResultingHolidaysResponse:
    work_order, work_order_id = _get_work_order_and_id(db, work_order_public_id)
    row, change_rows = get_work_order_holiday_list_snapshot(db, work_order_id=work_order_id)
    changes = [
        holiday_rules.Change(
            holiday_date=item["holiday_date"],
            change_code=item["change_code"],
            kind_code=item.get("holiday_kind_code"),
            rate_code=item.get("working_day_rate_code"),
            description=item.get("description"),
        )
        for item in change_rows
    ]
    lines = _lines(db, account_public_id=work_order.account_public_id, work_order_id=work_order_id)
    groups = _groups(lines)
    contract_start, contract_end = contract_bounds_for_work_order(db, work_order_id=work_order_id)
    within = holiday_rules.window(
        contract_start=contract_start,
        contract_end=contract_end,
        gaps=contract_gaps_for_work_order(db, work_order_id=work_order_id),
        last_calendar_year=last_year_started(db),
        changes=changes,
    )
    response = {
        "work_order_public_id": work_order.public_id,
        "holidays_answer_code": row.get("holidays_answer_code") if row else None,
        "list_version": int(row["list_version"]) if row else None,
    }
    if within is None:
        return WorkOrderResultingHolidaysResponse(
            **response,
            period_note_code=WORK_ORDER_HOLIDAY_PERIOD_NO_START,
            period_message="Record the contract start to see the holidays that apply.",
            calendar_days=[],
            groups=[
                WorkOrderHolidayGroup(
                    state_code=members[0].state_code,
                    state_label=members[0].state_label,
                    problem_code=members[0].problem_code,
                    problem_message=_problem_message(members),
                    line_numbers=[line.line_number for line in members],
                    days=[],
                )
                for members in groups
            ],
            years_not_complete=[],
            change_notes=[],
        )

    # PBL's calendar covers 2000 to 2100: a contract running beyond is read, and its notes given, within those years.
    first_day = max(within.first_day, date(FIRST_YEAR, 1, 1))
    last_day = min(within.last_day, date(LAST_YEAR, 12, 31))
    reading = calendar_between(db, first_day=first_day, last_day=last_day) if first_day <= last_day else None
    holidays = list(reading.holidays) if reading else []
    labels = {state.state_code: state.state_label for state in list_states(db)}
    periods = _term_periods(db, work_order_id=work_order_id)

    group_responses: list[WorkOrderHolidayGroup] = []
    for members in groups:
        state_code = members[0].state_code
        days = []
        for day in holiday_rules.resulting_days(holidays, changes, state_code=state_code, within=within):
            without = []
            if day.rate_code == WORK_ORDER_WORKING_DAY_OVERTIME_RATE:
                without = [
                    line.line_number
                    for line in members
                    if not holiday_rules.has_overtime_rate(periods.get(line.line_id, []), day.holiday_date)
                ]
            days.append(
                WorkOrderResultingDay(
                    holiday_date=day.holiday_date,
                    day_code=day.day_code,
                    source_code=day.source_code,
                    holiday_kind_code=day.kind_code,
                    name=day.name,
                    working_day_rate_code=day.rate_code,
                    note=day.note,
                    lines_without_overtime_rate=without,
                )
            )
        group_responses.append(
            WorkOrderHolidayGroup(
                state_code=state_code,
                state_label=members[0].state_label,
                problem_code=members[0].problem_code,
                problem_message=_problem_message(members),
                line_numbers=[line.line_number for line in members],
                days=days,
            )
        )

    state_codes = [members[0].state_code for members in groups]
    notes: list[WorkOrderHolidayChangeNote] = []
    for change in changes:
        if holiday_rules.working_day_does_nothing(change, holidays, state_codes):
            notes.append(
                WorkOrderHolidayChangeNote(
                    holiday_date=change.holiday_date,
                    change_code=change.change_code,
                    note_code=WORK_ORDER_CHANGE_DOES_NOTHING,
                    message=_DOES_NOTHING,
                )
            )
        elif holiday_rules.added_holiday_already_in_calendar(change, holidays, state_codes):
            notes.append(
                WorkOrderHolidayChangeNote(
                    holiday_date=change.holiday_date,
                    change_code=change.change_code,
                    note_code=WORK_ORDER_CHANGE_ALREADY_IN_CALENDAR,
                    message=_ALREADY_IN_CALENDAR,
                )
            )

    open_end = contract_end is None
    return WorkOrderResultingHolidaysResponse(
        **response,
        period_from=within.first_day,
        period_to=within.last_day,
        period_note_code=WORK_ORDER_HOLIDAY_PERIOD_OPEN_END if open_end else None,
        period_message=(
            f"No end date is recorded, so the holidays are shown to {format_contract_date(within.last_day)}."
            if open_end
            else None
        ),
        calendar_days=_calendar_days(holidays, within, lines, labels),
        groups=group_responses,
        years_not_complete=sorted(year for year, status in reading.years.items() if not status.complete) if reading else [],
        change_notes=notes,
    )
