"""Shared helpers for the ERT-1 and ERT-2 tests: Plum-shaped reports built from invented rows, and removing
exactly the equipment records a test module created (kit models' fits and pieces of kit included).

Plum's report has a title line, then a header of 32 columns in this order (the report of 24 September
2026). A test report carries invented machines only; the realistic test reads the dummified copy under
tests/fixtures, made under the owner's rule of 25 September 2026 (registration, engine and chassis numbers,
PAN, insurance and the like replaced; manufacturer-level facts kept).
"""

from __future__ import annotations

import csv
import io
import uuid
from contextlib import contextmanager
from typing import Any, Iterator

from sqlalchemy import text

from app.core.database import SessionLocal

PLUM_HEADER = (
    "VehicleNo,ScheduleMaintanceType,BedNo,EngineNo,ChassisNo,Make,Model,Capacity,TankCapacity,Manufacturer,"
    "CommencedYear,Owner,PAN,InsPolicyNo,InsuranceCo,DateOfPurchase,InvoiceNo,InvoiceDt,VehCategory,Status,"
    "ConsPostingAcc,TollTagAcc,MaintAcc,DieselAcc,TollPostingAcc,PostingAccount,GPS,StandardTyre,StepneyTyre,"
    "GrossVehicleWeight,UnladenWeight,LoadCapacity"
).split(",")

# Test names for Plum's columns, so a row reads as what it is.
_COLUMN_FOR = {
    "number": "VehicleNo",
    "schedule": "ScheduleMaintanceType",
    "bed": "BedNo",
    "engine": "EngineNo",
    "chassis": "ChassisNo",
    "make": "Make",
    "model": "Model",
    "capacity": "Capacity",
    "year": "CommencedYear",
    "owner": "Owner",
    "pan": "PAN",
    "policy": "InsPolicyNo",
    "category": "VehCategory",
    "status": "Status",
    "load": "LoadCapacity",
}


def suffix() -> str:
    """A short run-unique token, so invented machines, model names and values never meet real ones."""
    return uuid.uuid4().hex[:8].upper()


def plum_row(**values: Any) -> dict[str, str]:
    row = {column: "" for column in PLUM_HEADER}
    row["Status"] = "Active"
    row["Owner"] = "TEST OWNER"
    row["PAN"] = "AAAAA0000A"
    for name, value in values.items():
        row[_COLUMN_FOR[name]] = "" if value is None else str(value)
    return row


def plum_report(rows: list[dict[str, str]], *, title: str = "Own Vehicle Complete Information Report (test)", bom: bool = False) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow([title] + [""] * (len(PLUM_HEADER) - 1))
    writer.writerow(PLUM_HEADER)
    for row in rows:
        writer.writerow([row[column] for column in PLUM_HEADER])
    content = buffer.getvalue().encode("utf-8")
    return (b"\xef\xbb\xbf" + content) if bom else content


_TABLES_WITH_IDS = (
    "equipment_source_import",
    "equipment_asset",
    "equipment_model",
    "equipment_model_source_key",
    "equipment_source_value_rule",
    "equipment_asset_correction",
    "equipment_asset_link",
    "equipment_model_fit",
)


def equipment_boundaries() -> dict[str, int]:
    with SessionLocal() as db:
        return {table: int(db.execute(text(f"SELECT COALESCE(MAX(id), 0) FROM {table}")).scalar_one()) for table in _TABLES_WITH_IDS}


def remove_equipment_created_after(boundaries: dict[str, int]) -> None:
    """Delete every equipment record created after the boundaries, children first. Records that existed
    before are left, apart from flags a test report raised on them."""
    b = boundaries
    statements = (
        ("DELETE FROM equipment_asset_flag WHERE equipment_asset_id > :asset OR raised_by_import_id > :import", {}),
        ("DELETE FROM equipment_asset_correction WHERE id > :correction OR equipment_asset_id > :asset", {}),
        ("DELETE FROM equipment_asset_link WHERE id > :link OR parent_asset_id > :asset OR child_asset_id > :asset", {}),
        ("DELETE FROM equipment_asset_capability WHERE equipment_asset_id > :asset", {}),
        ("DELETE FROM equipment_source_binding WHERE equipment_asset_id > :asset", {}),
        ("DELETE FROM equipment_asset WHERE id > :asset", {}),
        ("DELETE FROM equipment_source_value_rule WHERE id > :rule OR recorded_during_import_id > :import", {}),
        ("DELETE FROM equipment_model_source_key WHERE id > :mapping OR equipment_model_id > :model", {}),
        # ERT-2: a kit model's crane models. Removed before either model.
        ("DELETE FROM equipment_model_fit WHERE id > :fit OR kit_model_id > :model OR crane_model_id > :model", {}),
        ("DELETE FROM equipment_model_capability WHERE equipment_model_id > :model", {}),
        ("DELETE FROM equipment_model WHERE id > :model", {}),
        ("DELETE FROM equipment_source_import_row WHERE equipment_source_import_id > :import", {}),
        ("DELETE FROM equipment_source_import WHERE id > :import", {}),
    )
    params = {
        "import": b["equipment_source_import"],
        "asset": b["equipment_asset"],
        "model": b["equipment_model"],
        "mapping": b["equipment_model_source_key"],
        "rule": b["equipment_source_value_rule"],
        "correction": b["equipment_asset_correction"],
        "link": b["equipment_asset_link"],
        "fit": b["equipment_model_fit"],
    }
    with SessionLocal() as db:
        for sql, extra in statements:
            db.execute(text(sql), {**params, **extra})
        db.commit()


@contextmanager
def equipment_created_here() -> Iterator[None]:
    boundaries = equipment_boundaries()
    try:
        yield
    finally:
        remove_equipment_created_after(boundaries)
