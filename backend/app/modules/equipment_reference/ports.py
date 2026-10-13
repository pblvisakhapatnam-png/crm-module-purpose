"""The interfaces of the Equipment Reference's ports.

`EquipmentSourcePort` - the interface a source of machines must implement (ADR-037). Implemented by
`plum_source.PlumReportEquipmentSource` (ERT-1): Plum's report is read and transformed into the platform's models
and machines (`plum_report.py`), and a snapshot is read from those. Consumers - Requirement, Availability,
Assignment, Eligibility - depend on this port and the canonical shapes in `contract.py`, never on a Plum field or
table.

Not wired, as of 8 October 2026 (TB-1 TB1-610): nothing calls the port or its Plum implementation. The import
services take the transformer (`plum_report.py`) directly, and Resource Requirements, Resource Assignments and
Eligibility ask this module's services for machines - still never a Plum field or table. The port is kept as
ADR-037's seam for a second source of machines; wire it when one is scheduled, or remove it before production if
none is.

`KitListingSource` - what the Equipment Reference asks of Resource Assignments before a counted set of kit shrinks
(TB-1 finding TB1-307, 4 October 2026). Resource Assignments registers it when it is loaded, as it registers its
ports with Eligibility and Resource Requirements, so this module never imports it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol, runtime_checkable

from sqlalchemy.orm import Session

from app.modules.equipment_reference.contract import EquipmentSourceSnapshot


@runtime_checkable
class EquipmentSourcePort(Protocol):
    """Machines as the platform sees them, from whichever system holds them in the current phase.

    Phase 1: Plum, through the transformer, for machine identity, status and statutory documents; the
    platform owns classification. Phase 2: the platform itself. Phase 3: Plum ingests from the
    platform through a reverse transformer (ADR-037).
    """

    def snapshot(self, as_of: datetime) -> EquipmentSourceSnapshot: ...


@dataclass(frozen=True)
class ListedKit:
    """How many pieces of one set trips list at once, at most, on any day from a given day on, and the allocations
    whose trips list it on those days."""

    most_at_once: int
    allocation_references: tuple[str, ...]


class KitListingSource(Protocol):
    def hold(self, db: Session) -> None:
        """Take Resource Assignments' lock in the caller's transaction, so no kit is listed or moved meanwhile. The
        lock alone; it writes nothing."""
        ...

    def listed_from(self, db: Session, *, piece_public_id: str, from_day: date) -> ListedKit:
        """What trips list of the piece from `from_day` on. A read: it writes nothing and takes no lock."""
        ...


_kit_listings: list[KitListingSource] = []


def register_kit_listing_source(source: KitListingSource) -> None:
    """Called once, by the Resource Assignments module, when it is loaded. A second registration replaces the first,
    so reloading the module in a test does not leave two."""
    _kit_listings[:] = [source]


def kit_listing_source() -> KitListingSource:
    if not _kit_listings:
        raise RuntimeError(
            "Resource Assignments is not loaded, so the trips listing this kit cannot be read. "
            "Import app.modules.resource_assignments.service first."
        )
    return _kit_listings[0]
