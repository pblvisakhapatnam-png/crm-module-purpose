"""The Plum report adapter's side of `EquipmentSourcePort` (ADR-037, ERT-1).

Phase 1: Plum is the source of each machine's identity and status, through the transformer, as corrected
by the Fleet Admin; the platform holds how it is classified and described. A snapshot is therefore read
from the platform's own records, which the confirmed reports built - never from a Plum row or a binding.
Parts are not machines and are not in it.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.modules.equipment_reference.contract import (
    ASSET_KIND_MACHINE,
    CanonicalCapabilityValue,
    CanonicalMachine,
    DataQualityFlag,
    EquipmentSourceSnapshot,
)
from app.modules.equipment_reference.service import get_equipment_structure
from app.modules.equipment_reference.services.machines import get_machine, list_machines

_PAGE = 200


class PlumReportEquipmentSource:
    """Machines as the platform holds them, built from Plum's confirmed reports."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def snapshot(self, as_of: datetime) -> EquipmentSourceSnapshot:
        machines: list[CanonicalMachine] = []
        offset = 0
        while True:
            page = list_machines(self._db, kind_code=ASSET_KIND_MACHINE, limit=_PAGE, offset=offset)
            for summary in page:
                machine = get_machine(self._db, summary.asset_public_id)
                machines.append(
                    CanonicalMachine(
                        machine_public_id=str(machine.asset_public_id),
                        machine_reference=machine.asset_reference,
                        class_code=machine.class_code,
                        type_code=machine.type_code,
                        model_public_id=str(machine.model_public_id) if machine.model_public_id else None,
                        status_code=machine.asset_status_code,
                        master_version=machine.asset_version,
                        facts_as_of=machine.facts_report_date,
                        capabilities=tuple(
                            CanonicalCapabilityValue(item.capability_code, item.value, item.choice_value)
                            for item in machine.capabilities
                            if item.source_code != "NONE"
                        ),
                        flags=tuple(
                            DataQualityFlag(flag.flag_code, flag.subject_code or None, flag.flag_code)
                            for flag in machine.flags
                        ),
                    )
                )
            if len(page) < _PAGE:
                break
            offset += _PAGE
        return EquipmentSourceSnapshot(
            taxonomy_version=get_equipment_structure(self._db).taxonomy_version,
            snapshot_at=as_of,
            machines=tuple(machines),
        )
