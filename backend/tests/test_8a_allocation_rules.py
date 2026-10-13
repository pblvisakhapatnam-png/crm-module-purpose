"""8A core - the allocation rules that need no database (resource_assignments/rules.py).

docs/agent/slices/8a-core-equipment-allocation.md, section 15, "The pure rules": busy days, a unit's coverage across
a planned hand-over and a replacement and with an open end, the status's inputs, the candidate order, whether a
machine meets a requirement, and the counted-set arithmetic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.modules.resource_assignments.rules import (
    Asked,
    Days,
    busy_days,
    candidate_order,
    effective_end,
    first_uncovered_day,
    left_out_reason,
    most_in_use,
    covered_units,
    requirement_coverage,
    unit_covered,
)

D = date(2027, 1, 10)


def day(offset: int) -> date:
    return D + timedelta(days=offset)


# --- Busy days ---------------------------------------------------------------------------------------------


def test_busy_days_run_to_the_earlier_of_the_planned_end_and_the_day_it_ended() -> None:
    assert busy_days(day(0), day(30), None) == Days(day(0), day(30))
    assert busy_days(day(0), day(30), day(9)) == Days(day(0), day(9))
    assert busy_days(day(0), None, None) == Days(day(0), None)
    assert busy_days(day(0), None, day(4)) == Days(day(0), day(4))
    assert effective_end(day(30), day(40)) == day(30)


def test_an_allocation_ended_before_it_started_keeps_no_day() -> None:
    assert busy_days(day(0), day(30), day(-1)) is None


def test_days_overlap_when_they_share_a_day_and_an_open_end_runs_on() -> None:
    assert Days(day(0), day(5)).overlaps(Days(day(5), day(9)))
    assert not Days(day(0), day(4)).overlaps(Days(day(5), day(9)))
    assert Days(day(0), None).overlaps(Days(day(100), day(101)))
    assert Days(day(0), day(9)).contains(Days(day(3), day(3)))
    assert not Days(day(0), day(9)).contains(Days(day(3), None))


# --- A unit's coverage (6.5) --------------------------------------------------------------------------------


def test_a_unit_is_covered_by_one_allocation_over_the_whole_period() -> None:
    assert unit_covered([Days(day(0), day(30))], day(0), day(30))
    assert not unit_covered([Days(day(0), day(29))], day(0), day(30))
    assert not unit_covered([Days(day(1), day(30))], day(0), day(30))


def test_a_planned_hand_over_or_a_replacement_keeps_the_unit_covered_and_a_gap_does_not() -> None:
    # A replacement ends the old machine the day before the new one starts.
    assert unit_covered([Days(day(0), day(9)), Days(day(10), day(30))], day(0), day(30))
    assert not unit_covered([Days(day(0), day(8)), Days(day(10), day(30))], day(0), day(30))
    # Given in any order, and an allocation reaching past the requirement still covers it.
    assert unit_covered([Days(day(10), day(40)), Days(day(-5), day(9))], day(0), day(30))


def test_an_open_ended_requirement_needs_an_open_ended_allocation_at_the_end_of_the_chain() -> None:
    assert unit_covered([Days(day(0), day(9)), Days(day(10), None)], day(0), None)
    assert not unit_covered([Days(day(0), day(900))], day(0), None)


def test_the_first_uncovered_day_is_where_a_new_allocation_for_the_unit_starts() -> None:
    assert first_uncovered_day([], day(0), day(30)) == day(0)
    assert first_uncovered_day([Days(day(0), day(9))], day(0), day(30)) == day(10)
    assert first_uncovered_day([Days(day(5), day(9))], day(0), day(30)) == day(0)
    assert first_uncovered_day([Days(day(0), day(30))], day(0), day(30)) is None
    assert first_uncovered_day([Days(day(0), None)], day(0), None) is None


def test_coverage_counts_only_the_units_now_required() -> None:
    held = {1: [Days(day(0), day(30))], 2: [Days(day(0), day(9))], 3: [Days(day(0), day(30))]}
    # Unit 3 is above the two now required (UNIT_NOT_REQUIRED): it counts for nothing.
    assert requirement_coverage(2, held, day(0), day(30)) == (1, 2)
    assert requirement_coverage(3, held, day(0), day(30)) == (2, 3)
    assert requirement_coverage(2, {}, day(0), day(30)) == (0, 0)


def test_the_covered_units_are_those_whose_machines_cover_every_day() -> None:
    # 8A-R8-002: unit 1 covered, unit 2 partly, unit 3 above the number required.
    held = {1: [Days(day(0), day(30))], 2: [Days(day(0), day(9))], 3: [Days(day(0), day(30))]}
    assert covered_units(2, held, day(0), day(30)) == (1,)
    assert covered_units(3, held, day(0), day(30)) == (1, 3)
    assert covered_units(2, {}, day(0), day(30)) == ()


def test_coverage_counts_only_days_of_the_requirements_period() -> None:
    # The requirement moved later than the machine's days (OUTSIDE_REQUIREMENT): the unit has no machine on any of
    # its days, so the requirement is open again rather than partly allocated.
    held = {1: [Days(day(0), day(9))], 2: [Days(day(5), day(40))]}
    assert requirement_coverage(2, held, day(20), day(30)) == (1, 1)
    assert requirement_coverage(2, held, day(20), None) == (0, 1)
    assert requirement_coverage(2, {1: [Days(day(0), day(9))]}, day(10), None) == (0, 0)


# --- Counted sets (6.10) ----------------------------------------------------------------------------------


def test_the_most_in_use_is_the_largest_total_listed_on_any_one_day_of_the_window() -> None:
    lines = [(Days(day(0), day(10)), 2), (Days(day(5), day(20)), 1), (Days(day(15), None), 3)]
    assert most_in_use(lines, Days(day(0), day(4))) == 2
    assert most_in_use(lines, Days(day(0), day(12))) == 3
    assert most_in_use(lines, Days(day(11), day(30))) == 4
    assert most_in_use(lines, Days(day(-10), day(-1))) == 0
    # A line already started when the window opens counts from the window's first day.
    assert most_in_use([(Days(day(-5), None), 2)], Days(day(0), day(1))) == 2


# --- Does a machine meet the requirement? (6.2) --------------------------------------------------------------


@dataclass(frozen=True)
class Cap:
    capability_code: str
    value: Decimal | None = None
    choice_value: str | None = None


@dataclass(frozen=True)
class Machine:
    class_code: str = "CRANE"
    type_code: str | None = "CRAWLER"
    capabilities: tuple[Cap, ...] = (Cap("RATED_CAPACITY", Decimal("250")),)

    def capability(self, capability_code: str) -> Cap | None:
        return next((item for item in self.capabilities if item.capability_code == capability_code), None)


ASKED_220 = [Asked("RATED_CAPACITY", Decimal("220"), None)]


@pytest.mark.parametrize(
    ("machine", "type_code", "asked", "reason"),
    [
        (Machine(), "CRAWLER", ASKED_220, None),
        (Machine(), None, ASKED_220, None),
        (Machine(class_code="FORKLIFT"), "CRAWLER", ASKED_220, "CLASS_DIFFERS"),
        (Machine(type_code=None), "CRAWLER", ASKED_220, "TYPE_UNKNOWN"),
        (Machine(type_code="ALL_TERRAIN"), "CRAWLER", ASKED_220, "TYPE_DIFFERS"),
        (Machine(capabilities=()), "CRAWLER", ASKED_220, "RATING_UNKNOWN"),
        (Machine(capabilities=(Cap("RATED_CAPACITY", Decimal("100")),)), "CRAWLER", ASKED_220, "BELOW_REQUIREMENT"),
        (Machine(capabilities=(Cap("RATED_CAPACITY", Decimal("220")),)), "CRAWLER", ASKED_220, None),
        (Machine(capabilities=(Cap("AXLES", choice_value="6X4"),)), None, [Asked("AXLES", None, "6x4")], None),
        (Machine(capabilities=(Cap("AXLES", choice_value="6X2"),)), None, [Asked("AXLES", None, "6X4")], "BELOW_REQUIREMENT"),
    ],
)
def test_a_machine_meets_the_requirement_only_when_it_is_known_to(machine, type_code, asked, reason) -> None:
    """Unknown never counts as meeting a requirement: a machine with no type, or no value for a capability asked
    for, is left out (the owner's conservative principle)."""
    assert left_out_reason(machine, class_code="CRANE", type_code=type_code, asked=asked) == reason


def test_the_order_is_free_first_then_can_be_allocated_then_the_smallest_that_will_do() -> None:
    rows = [
        ("busy", False, "ELIGIBLE", Decimal("250"), "A"),
        ("blocked", True, "BLOCKED", Decimal("250"), "B"),
        ("warning", True, "WARNING", Decimal("250"), "C"),
        ("big", True, "ELIGIBLE", Decimal("400"), "D"),
        ("small", True, "ELIGIBLE", Decimal("250"), "E"),
        ("unknown", True, "ELIGIBLE", None, "F"),
    ]
    ordered = sorted(
        rows,
        key=lambda row: candidate_order(available=row[1], overall_code=row[2], key_value=row[3], machine_number=row[4]),
    )
    assert [row[0] for row in ordered] == ["small", "big", "unknown", "warning", "blocked", "busy"]
