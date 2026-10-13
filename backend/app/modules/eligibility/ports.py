"""What Eligibility asks of Resource Assignments (ELG-2) and of the holiday calendar (HOL-1) for the reminders, without
importing either (ADR-017).

Two of the reminders - a certificate running out before an allocated machine's job starts, and one running out during
it - need 8A's allocations. Resource Assignments imports Eligibility (it stores Eligibility's decisions), so Eligibility
never imports it back: Resource Assignments registers an `AllocationSource` when it is loaded, as it registers
`AssignmentPort` with Resource Requirements. `app.main` loads it, and so does the smoke-data harness.

With none registered, reading the reminders fails rather than showing no allocation reminders merely because Resource
Assignments was not loaded (fail closed).

Design: docs/agent/slices/elg-2-certificate-reminders.md, section 10.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from sqlalchemy.orm import Session


@dataclass(frozen=True)
class AllocatedAsset:
    """A machine held on an allocation, or a piece of kit listed on one of its Trips (Own Load), with what its check
    needs: the site as it now is and the days, as the allocation's own "today's answer" uses them (8A, section 6.4)."""

    # resource_assignment (the machine) or resource_assignment_kit (a piece), as for record_decision.
    subject_type: str
    # The allocation's or the kit line's public id.
    subject_public_id: str
    assignment_public_id: str
    assignment_reference: str
    work_order_public_id: str
    work_order_code: str
    work_order_line_number: int
    unit_number: int
    trip_number: int | None
    asset_public_id: str
    # The allocation's first day and last day (None: it runs on); for a piece, its kit line's days.
    period_from: date
    period_to: date | None
    # The day the allocation, or the kit line, was recorded, in Asia/Kolkata.
    began_on: date
    # The site's state as matched, and whether it is a central-government site; both None, with a problem code,
    # when the site cannot be judged (8A's SiteFacts).
    site_state_code: str | None
    central_government_site: bool | None
    site_label: str | None
    site_problem_code: str | None


class AllocationSource(Protocol):
    def hold(self, db: Session) -> None:
        """Take Resource Assignments' lock in the caller's transaction, as its writes do after the Work Order's and the
        requirement's: marking reminders seen reads the allocations under it, so an allocation freed, replaced, moved or
        given kit meanwhile is seen - or waits (independent review, ELG2-R1-002). The lock alone; it writes nothing."""
        ...

    def held_for_reminders(self, db: Session, *, today: date) -> list[AllocatedAsset]:
        """Every held allocation whose last day has not passed, and every listed kit line of it with days left. A
        read: it writes nothing and takes no lock."""
        ...


_registered: list[AllocationSource] = []


def register_allocation_source(source: AllocationSource) -> None:
    """Called once, by the Resource Assignments module, when it is loaded. A second registration replaces the first,
    so reloading the module in a test does not leave two."""
    _registered[:] = [source]


def allocation_source() -> AllocationSource:
    if not _registered:
        raise RuntimeError(
            "Resource Assignments is not loaded, so the allocation reminders cannot be read. "
            "Import app.modules.resource_assignments.service first."
        )
    return _registered[0]


# --- PBL's holiday calendar (HOL-1, Q2) ----------------------------------------------------------------------------
#
# The reminder "PBL's holiday calendar for <year> is not set up" needs to know which years are complete. The calendar
# reads Eligibility's list of states, so Eligibility never imports it back: the calendar registers a
# `CalendarYearSource` when its service is loaded. `app.main` loads it, and so does the smoke-data harness. With none
# registered, reading the reminders fails rather than showing no calendar reminder (fail closed, as above).
# Design: docs/agent/slices/hol-1-holiday-calendar.md, sections 5.4 and 10.


class CalendarYearSource(Protocol):
    def hold(self, db: Session) -> None:
        """Take the calendar's write lock in the caller's transaction, as a save of a year does: marking reminders seen
        reads the years under it, so a year marked complete meanwhile is seen - or waits. The lock alone; it writes
        nothing."""
        ...

    def years_not_complete(self, db: Session, *, years: list[int]) -> list[int]:
        """Those of `years` the calendar keeps (2000 to 2100) and does not hold as complete - not started, or started
        and not marked complete - in order. A year it cannot keep is never returned: its reminder could never end. A
        read: it writes nothing and takes no lock."""
        ...


_calendar_registered: list[CalendarYearSource] = []


def register_calendar_source(source: CalendarYearSource) -> None:
    """Called once, by the holiday calendar, when it is loaded. A second registration replaces the first."""
    _calendar_registered[:] = [source]


def calendar_source() -> CalendarYearSource:
    if not _calendar_registered:
        raise RuntimeError(
            "The holiday calendar is not loaded, so the calendar reminders cannot be read. "
            "Import app.modules.holiday_calendar.service first."
        )
    return _calendar_registered[0]
