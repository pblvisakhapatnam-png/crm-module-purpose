"""The holiday calendar's rules, pure (HOL-1).

docs/agent/slices/hol-1-holiday-calendar.md, section 5.1. No database and no clock: the service hands in a year's
holidays and the states the platform knows, and gets back the first refusal in words, the dates a save changes, or
the holidays that apply to a state.

- **A holiday** has its date, its kind (national or festival), its name, and where it applies: all of India, or the
  states named. The kind does not decide where it applies (1.2, point 2).
- **A date is never a holiday twice for one state** (1.2, point 3): one all-India holiday on a date, and then no
  state's own; a state named once on a date. The same date may be a holiday for different states under different
  names - 14 April is Tamil New Year in Tamil Nadu and Baisakhi in Punjab.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Iterable

from app.modules.holiday_calendar.contract import (
    APPLIES_ALL_INDIA,
    APPLIES_STATES,
    APPLIES_TO_CODES,
    KIND_CODES,
    NAME_MAX_LENGTH,
)


@dataclass(frozen=True)
class CalendarHoliday:
    holiday_date: date
    kind_code: str
    name: str
    applies_to_code: str
    # Sorted; empty for an all-India holiday.
    state_codes: tuple[str, ...]

    def applies_to(self, state_code: str | None) -> bool:
        """Whether this holiday is one for a site in `state_code`. A site whose state is not known gets the all-India
        holidays only (1.2, point 8)."""
        return self.applies_to_code == APPLIES_ALL_INDIA or (state_code is not None and state_code in self.state_codes)


def day_text(value: date) -> str:
    """"26 January 2027", the form every message here uses."""
    return f"{value.day} {value.strftime('%B %Y')}"


def year_problem(calendar_year: int, holidays: Iterable[CalendarHoliday], *, state_labels: dict[str, str]) -> str | None:
    """Why a year's holidays cannot be saved, naming the date, or None. `state_labels` are the states and union
    territories the platform knows, by code. Codes are compared as given: the service has already put them in
    capitals."""
    ordered = sorted(holidays, key=lambda item: item.holiday_date)
    for holiday in ordered:
        day = day_text(holiday.holiday_date)
        if holiday.holiday_date.year != calendar_year:
            return f"{day} is not in {calendar_year}. Enter only the holidays of {calendar_year} here."
        if holiday.kind_code not in KIND_CODES:
            return f"Choose whether the holiday on {day} is a national or a festival holiday."
        if not holiday.name.strip():
            return f"Give the holiday on {day} a name."
        if len(holiday.name) > NAME_MAX_LENGTH:
            return f"The name of the holiday on {day} is longer than {NAME_MAX_LENGTH} characters."
        if holiday.applies_to_code not in APPLIES_TO_CODES:
            return f"Choose whether the holiday on {day} applies to all of India or to the states named."
        if holiday.applies_to_code == APPLIES_ALL_INDIA and holiday.state_codes:
            return f"The holiday on {day} applies to all of India, so it names no states."
        if holiday.applies_to_code == APPLIES_STATES and not holiday.state_codes:
            return f"Choose at least one state for the holiday on {day}, or make it apply to all of India."
        unknown = [code for code in holiday.state_codes if code not in state_labels]
        if unknown:
            return f"The holiday on {day} names {unknown[0]}, which is not a state or union territory the platform knows."
        if len(set(holiday.state_codes)) != len(holiday.state_codes):
            twice = next(code for code in holiday.state_codes if holiday.state_codes.count(code) > 1)
            return f"The holiday on {day} names {state_labels[twice]} twice."

    by_date: dict[date, list[CalendarHoliday]] = defaultdict(list)
    for holiday in ordered:
        by_date[holiday.holiday_date].append(holiday)
    for on, entries in by_date.items():
        day = day_text(on)
        all_india = [entry for entry in entries if entry.applies_to_code == APPLIES_ALL_INDIA]
        if len(all_india) > 1:
            return f"Two holidays on {day} apply to all of India. Keep one."
        named = [code for entry in entries if entry.applies_to_code == APPLIES_STATES for code in entry.state_codes]
        if all_india and named:
            return (
                f"{day} is already a holiday for all of India, so it cannot also be a holiday for "
                f"{state_labels[named[0]]} alone."
            )
        seen: set[str] = set()
        for code in named:
            if code in seen:
                return f"{day} is a holiday for {state_labels[code]} twice. Keep one."
            seen.add(code)
    return None


def _by_date(holidays: Iterable[CalendarHoliday]) -> dict[date, frozenset[tuple[str, str, str, tuple[str, ...]]]]:
    grouped: dict[date, set[tuple[str, str, str, tuple[str, ...]]]] = defaultdict(set)
    for holiday in holidays:
        grouped[holiday.holiday_date].add((holiday.kind_code, holiday.name, holiday.applies_to_code, holiday.state_codes))
    return {on: frozenset(entries) for on, entries in grouped.items()}


def year_changes(
    before: Iterable[CalendarHoliday], after: Iterable[CalendarHoliday]
) -> tuple[list[date], list[date], list[date]]:
    """The dates a save adds, removes, and changes - a change of kind, name or states - each earliest first."""
    old, new = _by_date(before), _by_date(after)
    added = sorted(on for on in new if on not in old)
    removed = sorted(on for on in old if on not in new)
    changed = sorted(on for on in new if on in old and new[on] != old[on])
    return added, removed, changed


def holidays_for_state(holidays: Iterable[CalendarHoliday], state_code: str | None) -> list[CalendarHoliday]:
    """The calendar holidays for a site in `state_code`, earliest first: the all-India ones and the state's own. With
    no state known, the all-India ones only (1.2, point 8). At most one per date, by the rule above."""
    return sorted((holiday for holiday in holidays if holiday.applies_to(state_code)), key=lambda item: item.holiday_date)
