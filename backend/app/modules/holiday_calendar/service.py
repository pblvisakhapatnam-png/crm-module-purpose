"""PBL's holiday calendar (HOL-1): reading and saving a year, and what other modules read of it.

Design: docs/agent/slices/hol-1-holiday-calendar.md, section 5.1; the API is
docs/agent/contracts/holiday-calendar-api-contract.md.

- **A year** is not started until Admin first saves it, started once saved, and complete once Admin marks it so.
  Saving replaces its holidays as a whole and gives it a new version; an identical save records nothing. Any year
  may be changed at any time, and every change is kept as an event (Q3).
- **The states** are ELG-1's list (Eligibility's public `list_jurisdictions`), without the central government's own
  sites. The calendar keeps no copy.
- **Other modules** read the calendar through `calendar_between` and `state_for_address` below, never its tables.
  Work Orders does; the calendar never reads Work Orders.
- **The Alerts** (Q2) ask which years are not complete through the port Eligibility defines; this module registers
  it when loaded.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.modules.eligibility.contract import JURISDICTION_KIND_CENTRAL
from app.modules.eligibility.ports import register_calendar_source
from app.modules.eligibility.service import jurisdiction_for_state_text, list_jurisdictions
from app.modules.events.schemas import BusinessEventSummary
from app.modules.events.service import record_business_event
from app.modules.holiday_calendar import repository as repo
from app.modules.holiday_calendar import rules
from app.modules.holiday_calendar.contract import (
    EVENT_YEAR_CHANGED,
    EVENT_YEAR_RECORDED,
    FIRST_YEAR,
    HOLIDAY_CALENDAR_MODULE_NAME,
    KIND_LABELS,
    LAST_YEAR,
    RECORD_TYPE_YEAR,
)
from app.modules.holiday_calendar.schemas import (
    HolidayCalendarHoliday,
    HolidayCalendarHolidayState,
    HolidayCalendarState,
    HolidayCalendarYearActionResponse,
    HolidayCalendarYearInput,
    HolidayCalendarYearResponse,
    HolidayCalendarYearsResponse,
    HolidayCalendarYearSummary,
)
from app.shared import business_time



class HolidayCalendarValidationError(ValueError):
    pass


class HolidayCalendarConflictError(ValueError):
    """Someone saved the year after the caller read it."""


def _event_dict(event: BusinessEventSummary) -> dict[str, Any]:
    return event.model_dump(mode="json")


# --- The states --------------------------------------------------------------------------------------------------


def list_states(db: Session) -> list[HolidayCalendarState]:
    """The states and union territories a holiday may name, in ELG-1's order."""
    return [
        HolidayCalendarState(
            state_code=item.jurisdiction_code, state_label=item.jurisdiction_label, state_kind_code=item.jurisdiction_kind_code
        )
        for item in list_jurisdictions(db)
        if item.jurisdiction_kind_code != JURISDICTION_KIND_CENTRAL
    ]


def _state_labels(db: Session) -> dict[str, str]:
    return {item.state_code: item.state_label for item in list_states(db)}


@dataclass(frozen=True)
class SiteState:
    state_code: str
    state_label: str


def state_for_address(db: Session, text: str | None) -> SiteState | None:
    """The state or union territory an address's free-text state names, read exactly as 8A's allocation reads a
    site's (`jurisdiction_for_state_text`), or None when it names none."""
    found = jurisdiction_for_state_text(db, text)
    return SiteState(found.jurisdiction_code, found.jurisdiction_label) if found is not None else None


# --- Reading -------------------------------------------------------------------------------------------------------


def _check_year(calendar_year: int) -> None:
    if not FIRST_YEAR <= calendar_year <= LAST_YEAR:
        raise HolidayCalendarValidationError(f"Choose a year from {FIRST_YEAR} to {LAST_YEAR}.")


def _calendar_holiday(row: dict[str, Any]) -> rules.CalendarHoliday:
    return rules.CalendarHoliday(
        holiday_date=row["holiday_date"],
        kind_code=row["holiday_kind_code"],
        name=row["holiday_name"],
        applies_to_code=row["applies_to_code"],
        state_codes=tuple(row["state_codes"] or ()),
    )


def _holiday_response(row: dict[str, Any], labels: dict[str, str]) -> HolidayCalendarHoliday:
    # States in ELG-1's own order, as the picker lists them.
    order = {code: index for index, code in enumerate(labels)}
    return HolidayCalendarHoliday(
        holiday_public_id=row["holiday_public_id"],
        holiday_date=row["holiday_date"],
        holiday_kind_code=row["holiday_kind_code"],
        holiday_kind_label=KIND_LABELS.get(row["holiday_kind_code"], row["holiday_kind_code"]),
        holiday_name=row["holiday_name"],
        applies_to_code=row["applies_to_code"],
        states=[
            HolidayCalendarHolidayState(state_code=code, state_label=labels.get(code, code))
            for code in sorted(row["state_codes"] or (), key=lambda code: order.get(code, len(order)))
        ],
    )


def _summary_values(calendar_year: int, row: dict[str, Any] | None, holiday_count: int) -> dict[str, Any]:
    return {
        "calendar_year": calendar_year,
        "year_public_id": row["year_public_id"] if row else None,
        "year_version": int(row["year_version"]) if row else None,
        "is_complete": bool(row and row["complete_marked_at"] is not None),
        "complete_marked_by_display_name": row["complete_marked_by_display_name"] if row else None,
        "complete_marked_at": row["complete_marked_at"] if row else None,
        "holiday_count": holiday_count,
        "updated_by_display_name": row["updated_by_display_name"] if row else None,
        "updated_at": row["updated_at"] if row else None,
    }


def list_years(db: Session) -> HolidayCalendarYearsResponse:
    """Every year started, and the current and next year even when not started (section 6, the year picker) - those of
    them the calendar keeps, 2000 to 2100: in 2100 the next year is not offered (independent review, HOL1-R1-002)."""
    today = business_time.india_today()
    started = {int(row["calendar_year"]): row for row in repo.list_year_rows(db)}
    years = sorted(set(started) | {year for year in (today.year, today.year + 1) if FIRST_YEAR <= year <= LAST_YEAR})
    return HolidayCalendarYearsResponse(
        today=today,
        years=[
            HolidayCalendarYearSummary(
                **_summary_values(year, started.get(year), int(started[year]["holiday_count"]) if year in started else 0)
            )
            for year in years
        ],
    )


def _year_response(db: Session, calendar_year: int) -> HolidayCalendarYearResponse:
    row, holidays = repo.year_snapshot(db, calendar_year=calendar_year)
    labels = _state_labels(db)
    return HolidayCalendarYearResponse(
        **_summary_values(calendar_year, row, len(holidays)),
        today=business_time.india_today(),
        holidays=[_holiday_response(item, labels) for item in holidays],
    )


def get_year(db: Session, calendar_year: int) -> HolidayCalendarYearResponse:
    _check_year(calendar_year)
    return _year_response(db, calendar_year)


# --- Saving --------------------------------------------------------------------------------------------------------


def _holidays_from(payload: HolidayCalendarYearInput) -> list[rules.CalendarHoliday]:
    return [
        rules.CalendarHoliday(
            holiday_date=item.holiday_date,
            # A field left out reads as blank, which the rules refuse naming the date (HOL1-R4-002).
            kind_code=(item.holiday_kind_code or "").strip().upper(),
            name=(item.holiday_name or "").strip(),
            applies_to_code=(item.applies_to_code or "").strip().upper(),
            # Sorted, duplicates kept, so the rule can name a state given twice.
            state_codes=tuple(sorted(code.strip().upper() for code in item.state_codes or ())),
        )
        for item in payload.holidays
    ]


def save_year(
    db: Session, *, calendar_year: int, payload: HolidayCalendarYearInput, user_public_id: str | None
) -> HolidayCalendarYearActionResponse:
    """Replace a year's holidays and its "complete" mark as a whole (section 5.1). Refused when someone saved the year
    after the caller read it. An identical save changes nothing and records nothing."""
    _check_year(calendar_year)
    if not user_public_id:
        raise HolidayCalendarValidationError("The signed-in user could not be identified, so nothing was saved.")
    holidays = _holidays_from(payload)
    try:
        repo.take_write_lock(db)
        row, current_rows = repo.year_snapshot(db, calendar_year=calendar_year)
        current_version = int(row["year_version"]) if row else None
        if payload.expected_version != current_version:
            raise HolidayCalendarConflictError(
                f"Someone saved the {calendar_year} calendar after you opened it, so your change was not saved. "
                "Read it again."
            )
        problem = rules.year_problem(calendar_year, holidays, state_labels=_state_labels(db))
        if problem is not None:
            raise HolidayCalendarValidationError(problem)
        added, removed, changed = rules.year_changes([_calendar_holiday(item) for item in current_rows], holidays)
        was_complete = bool(row and row["complete_marked_at"] is not None)
        if row is not None and not (added or removed or changed) and payload.is_complete == was_complete:
            # An identical save: the answer is read while the lock still holds, so it is the year as this save found
            # it, never one another save committed after the lock was let go (independent review, HOL1-R1-001).
            unchanged = HolidayCalendarYearActionResponse(year=_year_response(db, calendar_year), event=None)
            db.rollback()
            return unchanged

        now = datetime.now(timezone.utc)
        if payload.is_complete and was_complete:
            marked_by, marked_at = row["complete_marked_by"], row["complete_marked_at"]  # type: ignore[index]
        elif payload.is_complete:
            marked_by, marked_at = user_public_id, now
        else:
            marked_by, marked_at = None, None

        if row is None:
            year_public_id = str(uuid4())
            year_id = repo.insert_year(
                db,
                public_id=year_public_id,
                calendar_year=calendar_year,
                marked_by=marked_by,
                marked_at=marked_at,
                user_public_id=user_public_id,
            )
            new_version, event_name, reason = 1, EVENT_YEAR_RECORDED, f"Holiday calendar for {calendar_year} started."
        else:
            year_public_id, year_id = row["year_public_id"], int(row["year_id"])
            if (
                repo.update_year(
                    db,
                    year_id=year_id,
                    expected_version=int(current_version),  # type: ignore[arg-type]
                    marked_by=marked_by,
                    marked_at=marked_at,
                    user_public_id=user_public_id,
                )
                != 1
            ):
                raise HolidayCalendarConflictError(
                    f"Someone saved the {calendar_year} calendar after you opened it, so your change was not saved. "
                    "Read it again."
                )
            new_version, event_name = int(current_version) + 1, EVENT_YEAR_CHANGED  # type: ignore[arg-type]
            reason = f"Holiday calendar for {calendar_year} changed."
            repo.delete_holidays(db, year_id=year_id)

        for holiday in holidays:
            repo.insert_holiday(
                db,
                public_id=str(uuid4()),
                year_id=year_id,
                calendar_year=calendar_year,
                holiday_date=holiday.holiday_date,
                kind_code=holiday.kind_code,
                name=holiday.name,
                applies_to_code=holiday.applies_to_code,
                state_codes=holiday.state_codes,
            )
        event = record_business_event(
            db,
            event_name=event_name,
            source_module=HOLIDAY_CALENDAR_MODULE_NAME,
            record_type=RECORD_TYPE_YEAR,
            record_public_id=year_public_id,
            user_public_id=user_public_id,
            reason=reason,
            event_payload={
                # Dates, codes and counts only: a holiday's name is free text and stays out of the payload.
                "calendar_year": calendar_year,
                "year_version": new_version,
                "is_complete": payload.is_complete,
                "was_complete": was_complete,
                "holiday_count": len(holidays),
                "added_dates": [day.isoformat() for day in added],
                "removed_dates": [day.isoformat() for day in removed],
                "changed_dates": [day.isoformat() for day in changed],
            },
        )
        # The answer is read before the commit lets the lock go, from this transaction's own writes: the year this save
        # produced, beside its own event - never a version another save committed straight after (HOL1-R1-001).
        response = HolidayCalendarYearActionResponse(year=_year_response(db, calendar_year), event=_event_dict(event))
        db.commit()
    except Exception:
        db.rollback()
        raise
    return response


# --- What other modules read ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class YearStatus:
    calendar_year: int
    started: bool
    complete: bool
    year_version: int | None


@dataclass(frozen=True)
class CalendarReading:
    """The calendar over a span of days, read in one statement: each year's status, and the holidays on those days."""

    years: dict[int, YearStatus]
    holidays: tuple[rules.CalendarHoliday, ...]


def calendar_between(db: Session, *, first_day: date, last_day: date) -> CalendarReading:
    """PBL's calendar from `first_day` to `last_day`: every year they touch, started or not, and every holiday on those
    days. Work Orders reads "the holidays that apply" from this (section 5.3)."""
    year_rows, holiday_rows = repo.calendar_between(db, first_day=first_day, last_day=last_day)
    by_year = {int(row["calendar_year"]): row for row in year_rows}
    years = {
        year: YearStatus(
            calendar_year=year,
            started=year in by_year,
            complete=bool(by_year[year]["is_complete"]) if year in by_year else False,
            year_version=int(by_year[year]["year_version"]) if year in by_year else None,
        )
        for year in range(first_day.year, last_day.year + 1)
    }
    return CalendarReading(years=years, holidays=tuple(_calendar_holiday(row) for row in holiday_rows))


def last_year_started(db: Session) -> int | None:
    rows = repo.list_year_rows(db)
    return int(rows[-1]["calendar_year"]) if rows else None


class _CalendarYearSource:
    """What the Alerts ask of the calendar (Eligibility's `CalendarYearSource`)."""

    def hold(self, db: Session) -> None:
        repo.take_write_lock(db)

    def years_not_complete(self, db: Session, *, years: list[int]) -> list[int]:
        # Only years the calendar keeps: a year it cannot hold could never be marked complete, so its reminder could
        # never end (HOL1-R1-002).
        kept = [year for year in years if FIRST_YEAR <= year <= LAST_YEAR]
        complete = repo.list_complete_years(db, years=kept)
        return [year for year in kept if year not in complete]


register_calendar_source(_CalendarYearSource())
