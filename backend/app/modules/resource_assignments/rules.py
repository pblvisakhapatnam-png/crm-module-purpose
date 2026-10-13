"""The rules of allocation that need no database and no clock (8A core, design sections 6.2 to 6.10).

Days are whole days, both ends included; an end of None runs on. Kept pure, as Eligibility's `evaluation.py` is, so
each rule is tested on its own.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Iterable, Protocol

from app.modules.resource_assignments.contract import (
    LEFT_OUT_BELOW_REQUIREMENT,
    LEFT_OUT_CLASS_DIFFERS,
    LEFT_OUT_RATING_UNKNOWN,
    LEFT_OUT_TYPE_DIFFERS,
    LEFT_OUT_TYPE_UNKNOWN,
)

ONE_DAY = timedelta(days=1)


@dataclass(frozen=True)
class Days:
    """Days from `start` to `end`, both included; `end` None runs on."""

    start: date
    end: date | None

    def overlaps(self, other: "Days") -> bool:
        return (self.end is None or other.start <= self.end) and (other.end is None or self.start <= other.end)

    def contains(self, other: "Days") -> bool:
        if other.start < self.start:
            return False
        if self.end is None:
            return True
        return other.end is not None and other.end <= self.end


def effective_end(planned_to: date | None, ended_on: date | None) -> date | None:
    """The last day an allocation keeps its machine: the earlier of its planned end and the day it ended."""
    if planned_to is None:
        return ended_on
    if ended_on is None:
        return planned_to
    return min(planned_to, ended_on)


def busy_days(planned_from: date, planned_to: date | None, ended_on: date | None) -> Days | None:
    """The days an allocation keeps its machine, or None when it ended before it started. The database's
    generated `busy_range` says the same."""
    end = effective_end(planned_to, ended_on)
    if end is not None and end < planned_from:
        return None
    return Days(planned_from, end)


def unit_covered(held: Iterable[Days], required_from: date, planned_end: date | None) -> bool:
    """Whether a unit's held allocations cover every day from the requirement's start to its planned end. An
    open-ended requirement needs an open-ended allocation at the end of the chain."""
    cursor = required_from
    for days in sorted(held, key=lambda item: item.start):
        if days.end is not None and days.end < cursor:
            continue
        if days.start > cursor:
            return False
        if days.end is None:
            return True
        cursor = days.end + ONE_DAY
        if planned_end is not None and cursor > planned_end:
            return True
    return False


def first_uncovered_day(held: Iterable[Days], required_from: date, planned_end: date | None) -> date | None:
    """The first day of the requirement's period no held allocation of the unit covers, or None when every day is
    covered: where a new allocation for the unit starts by default."""
    cursor = required_from
    for days in sorted(held, key=lambda item: item.start):
        if days.end is not None and days.end < cursor:
            continue
        if days.start > cursor:
            return cursor
        if days.end is None:
            return None
        cursor = days.end + ONE_DAY
    if planned_end is not None and cursor > planned_end:
        return None
    return cursor


def covered_units(
    units_required: int, held_by_unit: dict[int, list[Days]], required_from: date, planned_end: date | None
) -> tuple[int, ...]:
    """The units, among 1 .. units required, whose allocations cover every day of the requirement's period: the ones
    no screen offers to allocate to again (8A-R8-002)."""
    period = Days(required_from, planned_end)
    return tuple(
        unit
        for unit in range(1, units_required + 1)
        if unit_covered([days for days in held_by_unit.get(unit, []) if days.overlaps(period)], required_from, planned_end)
    )


def requirement_coverage(
    units_required: int, held_by_unit: dict[int, list[Days]], required_from: date, planned_end: date | None
) -> tuple[int, int]:
    """(units covered on every day, units with a machine on some day), counting only units 1 .. units required and
    days of the requirement's period: a unit above the number now required counts for nothing (UNIT_NOT_REQUIRED),
    and so do days outside the period (OUTSIDE_REQUIREMENT)."""
    period = Days(required_from, planned_end)
    covered = 0
    with_machines = 0
    for unit in range(1, units_required + 1):
        held = [days for days in held_by_unit.get(unit, []) if days.overlaps(period)]
        if held:
            with_machines += 1
        if held and unit_covered(held, required_from, planned_end):
            covered += 1
    return covered, with_machines


def most_in_use(lines: Iterable[tuple[Days, int]], window: Days) -> int:
    """The most pieces of a counted set listed on any one day of the window: its lines' quantities summed over
    the days they overlap. What is free over the window is the set's quantity less this."""
    overlapping = [(days, quantity) for days, quantity in lines if days.overlaps(window)]
    if not overlapping:
        return 0
    # The total can rise only on a day a line starts (or the window starts), so those are the days to try.
    starts = {max(days.start, window.start) for days, _quantity in overlapping}
    return max(
        sum(quantity for days, quantity in overlapping if days.start <= day and (days.end is None or day <= days.end))
        for day in starts
    )


# --- Does a machine meet the requirement? ------------------------------------------------------------------


class _Capability(Protocol):
    capability_code: str
    value: Decimal | None
    choice_value: str | None


class _Asset(Protocol):
    class_code: str
    type_code: str | None

    def capability(self, capability_code: str) -> _Capability | None: ...


@dataclass(frozen=True)
class Asked:
    """One capability a requirement asks for: a least value, or a choice from a fixed list."""

    capability_code: str
    minimum_value: Decimal | None
    choice_value: str | None


def left_out_reason(
    asset: _Asset, *, class_code: str, type_code: str | None, asked: Iterable[Asked]
) -> str | None:
    """Why a machine does not meet a requirement's item, or None when it does (ADR-037). Unknown never counts as
    meeting it: a machine with no type is left out where a type is named, and one with no value for a capability
    asked for is left out (the owner's conservative principle)."""
    if asset.class_code != class_code:
        return LEFT_OUT_CLASS_DIFFERS
    if type_code is not None:
        if asset.type_code is None:
            return LEFT_OUT_TYPE_UNKNOWN
        if asset.type_code != type_code:
            return LEFT_OUT_TYPE_DIFFERS
    for item in asked:
        has = asset.capability(item.capability_code)
        if has is None or (has.value is None and has.choice_value is None):
            return LEFT_OUT_RATING_UNKNOWN
        if item.choice_value is not None:
            if (has.choice_value or "").upper() != item.choice_value.upper():
                return LEFT_OUT_BELOW_REQUIREMENT
        elif item.minimum_value is not None and (has.value is None or has.value < item.minimum_value):
            return LEFT_OUT_BELOW_REQUIREMENT
    return None


ANSWER_ORDER = {"ELIGIBLE": 0, "WARNING": 1, "OVERRIDE_REQUIRED": 2, "BLOCKED": 3}


def candidate_order(
    *, available: bool, overall_code: str | None, key_value: Decimal | None, machine_number: str | None
) -> tuple[int, int, int, Decimal, str]:
    """Advisory only (RPA-001): free machines first; then can be allocated, with a warning, the rest; the smallest
    key capability first, so a bigger machine is not taken when a smaller one will do; then the registration."""
    return (
        0 if available else 1,
        ANSWER_ORDER.get(overall_code or "", 4),
        0 if key_value is not None else 1,
        key_value if key_value is not None else Decimal(0),
        machine_number or "",
    )
