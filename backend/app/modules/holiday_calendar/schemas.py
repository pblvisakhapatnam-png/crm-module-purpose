"""Holiday calendar requests and responses (HOL-1). docs/agent/contracts/holiday-calendar-api-contract.md."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.modules.holiday_calendar.contract import MAX_HOLIDAYS_PER_YEAR


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HolidayCalendarState(BaseModel):
    """A state or union territory a holiday may name: ELG-1's list, without the central government's own sites."""

    state_code: str
    state_label: str
    state_kind_code: str


class HolidayCalendarHolidayState(BaseModel):
    state_code: str
    state_label: str


class HolidayCalendarHoliday(BaseModel):
    holiday_public_id: str
    holiday_date: date
    holiday_kind_code: str
    holiday_kind_label: str
    holiday_name: str
    applies_to_code: str
    # Empty for an all-India holiday; otherwise in the list's own order.
    states: list[HolidayCalendarHolidayState]


class HolidayCalendarYearSummary(BaseModel):
    calendar_year: int
    # All null, and the count 0, until Admin first saves the year.
    year_public_id: str | None
    year_version: int | None
    is_complete: bool
    complete_marked_by_display_name: str | None
    complete_marked_at: datetime | None
    holiday_count: int
    updated_by_display_name: str | None
    updated_at: datetime | None


class HolidayCalendarYearsResponse(BaseModel):
    # India's date, which the current and next year are taken from.
    today: date
    years: list[HolidayCalendarYearSummary]


class HolidayCalendarYearResponse(HolidayCalendarYearSummary):
    today: date
    holidays: list[HolidayCalendarHoliday]


class HolidayCalendarHolidayInput(_Request):
    """Only the date is required here. A name, kind or "applies to" left out, null, blank, too long or not known is
    refused by `rules.year_problem` in words that name the date; a check here would answer first, with no date
    (independent review, HOL1-R3-001 and HOL1-R4-002). A holiday with no date has no date to name: the request is
    refused as it stands."""

    holiday_date: date
    holiday_kind_code: str | None = None
    holiday_name: str | None = None
    applies_to_code: str | None = None
    state_codes: list[str] | None = None


class HolidayCalendarYearInput(_Request):
    """Whole replacement of a year, guarded by the version last read: null before the year is first saved."""

    expected_version: int | None = Field(default=None, ge=1)
    is_complete: bool
    holidays: list[HolidayCalendarHolidayInput] = Field(default_factory=list, max_length=MAX_HOLIDAYS_PER_YEAR)


class HolidayCalendarYearActionResponse(BaseModel):
    year: HolidayCalendarYearResponse
    # None when the save changed nothing: an identical save records no event and keeps the version.
    event: dict[str, Any] | None = None
