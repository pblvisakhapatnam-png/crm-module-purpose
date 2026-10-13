"""What Resource Requirements asks of Resource Assignment (8A core), without importing it (ADR-017).

A requirement's fulfilment - which of its units are covered by held machines - is Assignment's to know, and a
cancelled requirement frees the machines held for it (`WRR-001`: "Cancellation ... releases uncommitted
reservations"). This module never reads Assignment's tables and never imports it: Assignment registers an
implementation of `AssignmentPort` when it is loaded, as the Eligibility module registers its attach check
with the documents module (`register_attach_check`). `app.main` loads it, so the application always has one.

With none registered, every call fails closed: a requirement is never read as having no machines, or
cancelled without freeing them, merely because Assignment was not loaded.

Design: docs/agent/slices/8a-core-equipment-allocation.md, section 5.2.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from sqlalchemy.orm import Session


@dataclass(frozen=True)
class RequirementToCover:
    requirement_public_id: str
    units_required: int
    required_from: date
    # The requirement's own end, else its line's, else the contract's fixed end; None when nothing bounds it.
    planned_end: date | None


@dataclass(frozen=True)
class Coverage:
    # Units 1 .. units required whose held machines cover every day of the requirement's period.
    units_covered: int
    # Units 1 .. units required with at least one machine held on them.
    units_with_machines: int
    # Which units are covered (8A core, independent review round 8): the screens offer allocation on the others.
    covered_unit_numbers: tuple[int, ...] = ()


NO_COVERAGE = Coverage(units_covered=0, units_with_machines=0)


class AssignmentPort(Protocol):
    def hold(self, db: Session) -> None:
        """Take Resource Assignment's write lock in the caller's transaction, after the Work Order's and the
        requirement's locks - the order every write keeps - so coverage read next for a status that will be stored
        is what committed allocation writes left (independent review, 8A-FA-001). A write alone: reads do not."""
        ...

    def coverage(self, db: Session, requirements: list[RequirementToCover]) -> dict[str, Coverage]:
        """Each requirement's coverage by the machines held for it. A read."""
        ...

    def release_for_cancelled_requirement(self, db: Session, *, requirement_public_id: str, user_public_id: str) -> int:
        """Free every machine held for a requirement being cancelled, inside the caller's transaction, keeping
        their history. Returns how many were freed."""
        ...


_registered: list[AssignmentPort] = []


def register_assignment_port(port: AssignmentPort) -> None:
    """Called once, by the Resource Assignments module, when it is loaded. A second registration replaces the
    first, so reloading the module in a test does not leave two."""
    _registered[:] = [port]


def assignment_port() -> AssignmentPort:
    if not _registered:
        raise RuntimeError(
            "Resource Assignments is not loaded, so a requirement's machines cannot be read or freed. "
            "Import app.modules.resource_assignments.service first."
        )
    return _registered[0]
