"""Resource Assignment database access (8A core): its own four tables only - allocations, trips, kit lines and
the request-key registry. Other modules' records are named by
public id and read through their services."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session
from app.shared.transactions import take_advisory_lock

# One transaction-level advisory lock for every write of the module, as the Equipment Reference and Eligibility
# take theirs: writes are few and made by a few people, so they are simply serialized (design section 6.12).
WRITE_LOCK_KEY = 80_450_001


def _rows(db: Session, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    return [dict(row._mapping) for row in db.execute(text(sql), params or {}).fetchall()]


def _first(db: Session, sql: str, params: dict[str, Any]) -> dict[str, Any] | None:
    row = db.execute(text(sql), params).first()
    return dict(row._mapping) if row else None


def _rows_in(db: Session, sql: str, ids: list[Any], params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    if not ids:
        return []
    statement = text(sql).bindparams(bindparam("ids", expanding=True))
    return [dict(row._mapping) for row in db.execute(statement, {"ids": ids, **(params or {})}).fetchall()]


# An allocation is written only in a transaction the service marks (independent review, 8A-FA2-001): a statement
# trigger refuses any other (migration 20260908_0045, resource_assignment_guard), so the requirement's stored status,
# kept by the service in the same transaction, is never left behind. Transaction-local, like the lock.
SERVICE_WRITE_SETTING = "pbl.resource_assignment_writer"


def mark_service_write(db: Session) -> None:
    """Mark this transaction as the service's own write. The service does it with its lock; the test harness's
    cleanup does it when it removes a run's allocations with their requirements."""
    db.execute(text("SELECT set_config(:name, 'service', true)"), {"name": SERVICE_WRITE_SETTING})


def take_lock(db: Session) -> None:
    """This module's lock alone: for Resource Requirements, which reads coverage under it to store a status and writes
    no allocation (the port's `hold`), so its transaction is not marked (independent review, 8A-F3-003)."""
    take_advisory_lock(db, WRITE_LOCK_KEY)


def take_write_lock(db: Session) -> None:
    """This module's lock, which every write takes after the Work Order's and the requirement's; the transaction
    is then marked as the service's own, so it may write allocations."""
    take_lock(db)
    mark_service_write(db)


# --- Allocations ------------------------------------------------------------------------------------------

ASSIGNMENT_SELECT = """
    SELECT a.id, a.assignment_public_id, a.assignment_reference, a.resource_requirement_public_id, a.unit_number,
           a.work_order_public_id, a.work_order_code, a.work_order_line_public_id, a.work_order_line_number,
           a.source_offer_line_public_id, a.equipment_asset_public_id, a.allocated_machine_number,
           a.allocated_class_code, a.allocated_type_code, a.allocated_model_public_id, a.allocated_asset_version,
           a.planned_from, a.planned_to, a.ended_on, a.assignment_status_code, a.replaces_assignment_id,
           a.end_reason_code, a.end_note, a.ended_by, ender.display_name AS ended_by_display_name, a.ended_at,
           a.billing_cycle_code, a.billing_cycle_set_by, cycler.display_name AS billing_cycle_set_by_display_name,
           a.billing_cycle_set_at, a.decision_public_id, a.notes, a.assignment_version, a.create_request_key,
           a.created_by, creator.display_name AS created_by_display_name, a.created_at,
           a.updated_by, updater.display_name AS updated_by_display_name, a.updated_at
    FROM resource_assignment a
    LEFT JOIN app_user ender ON ender.public_id = a.ended_by
    LEFT JOIN app_user cycler ON cycler.public_id = a.billing_cycle_set_by
    LEFT JOIN app_user creator ON creator.public_id = a.created_by
    LEFT JOIN app_user updater ON updater.public_id = a.updated_by
"""

# Lists come in the order allocations were recorded, which no later write changes, so a page read after a given
# allocation neither skips nor repeats a row however others change meanwhile (independent review, 8A-FB-004). The
# screens order them for display.
LIST_ORDER = "ORDER BY a.id"


def get_assignment_row(db: Session, *, public_id: str) -> dict[str, Any] | None:
    return _first(db, f"{ASSIGNMENT_SELECT} WHERE a.assignment_public_id = :public_id", {"public_id": public_id})


def lock_assignment_row(db: Session, *, public_id: str) -> dict[str, Any] | None:
    return _first(
        db, f"{ASSIGNMENT_SELECT} WHERE a.assignment_public_id = :public_id FOR UPDATE OF a", {"public_id": public_id}
    )


def list_assignment_rows_by_ids(db: Session, *, ids: list[int]) -> list[dict[str, Any]]:
    return _rows_in(db, f"{ASSIGNMENT_SELECT} WHERE a.id IN :ids", ids)


def list_replacer_rows(db: Session, *, replaced_ids: list[int]) -> list[dict[str, Any]]:
    """The allocations that replaced each of these."""
    return _rows_in(db, f"{ASSIGNMENT_SELECT} WHERE a.replaces_assignment_id IN :ids", replaced_ids)


def get_request(db: Session, *, create_request_key: str) -> dict[str, Any] | None:
    """The request a key was first used for - its kind and fingerprint - across allocating, replacing and listing
    kit (8A-R2-002)."""
    return _first(
        db,
        "SELECT create_request_key, request_kind_code, request_fingerprint FROM resource_assignment_request "
        "WHERE create_request_key = :key",
        {"key": create_request_key},
    )


def insert_request(
    db: Session, *, create_request_key: str, kind_code: str, requirement_public_id: str, fingerprint: str, user_public_id: str
) -> None:
    db.execute(
        text(
            """
            INSERT INTO resource_assignment_request (
                create_request_key, request_kind_code, resource_requirement_public_id, request_fingerprint, created_by
            )
            VALUES (:key, :kind, :requirement, :fingerprint, :user)
            """
        ),
        {
            "key": create_request_key,
            "kind": kind_code,
            "requirement": requirement_public_id,
            "fingerprint": fingerprint,
            "user": user_public_id,
        },
    )


def find_assignment_by_request_key(db: Session, *, create_request_key: str) -> dict[str, Any] | None:
    return _first(db, f"{ASSIGNMENT_SELECT} WHERE a.create_request_key = :key", {"key": create_request_key})


def list_assignment_rows(
    db: Session,
    *,
    work_order_public_id: str | None,
    requirement_public_id: str | None,
    machine_public_id: str | None,
    status_code: str | None,
    starts_from: date | None,
    starts_to: date | None,
    limit: int,
    offset: int,
    after_public_id: str | None = None,
) -> list[dict[str, Any]]:
    conditions: list[str] = []
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if after_public_id is not None:
        conditions.append("a.id > (SELECT id FROM resource_assignment WHERE assignment_public_id = :after_public_id)")
        params["after_public_id"] = after_public_id
    for column, value, name in (
        ("a.work_order_public_id", work_order_public_id, "work_order_public_id"),
        ("a.resource_requirement_public_id", requirement_public_id, "requirement_public_id"),
        ("a.equipment_asset_public_id", machine_public_id, "machine_public_id"),
        ("a.assignment_status_code", status_code, "status_code"),
    ):
        if value is not None:
            conditions.append(f"{column} = :{name}")
            params[name] = value
    if starts_from is not None:
        conditions.append("a.planned_from >= :starts_from")
        params["starts_from"] = starts_from
    if starts_to is not None:
        conditions.append("a.planned_from <= :starts_to")
        params["starts_to"] = starts_to
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return _rows(db, f"{ASSIGNMENT_SELECT} {where} {LIST_ORDER} LIMIT :limit OFFSET :offset", params)


def list_held_rows_for_reminders(db: Session, *, today: date) -> list[dict[str, Any]]:
    """Every held allocation whose last day has not passed: what Eligibility's reminders judge (ELG-2)."""
    return _rows(
        db,
        f"{ASSIGNMENT_SELECT} WHERE a.assignment_status_code = 'HELD' AND (a.planned_to IS NULL OR a.planned_to >= :today) {LIST_ORDER}",
        {"today": today},
    )


def list_rows_for_requirements(db: Session, *, requirement_public_ids: list[str]) -> list[dict[str, Any]]:
    """Every allocation of these requirements, whatever became of it: the days each kept are the days its unit had
    a machine."""
    return _rows_in(db, f"{ASSIGNMENT_SELECT} WHERE a.resource_requirement_public_id IN :ids", requirement_public_ids)


def lock_held_rows_for_requirement(db: Session, *, requirement_public_id: str) -> list[dict[str, Any]]:
    return _rows(
        db,
        f"{ASSIGNMENT_SELECT} WHERE a.resource_requirement_public_id = :public_id AND a.assignment_status_code = 'HELD' "
        "ORDER BY a.id FOR UPDATE OF a",
        {"public_id": requirement_public_id},
    )


def _overlapping(where: str) -> str:
    return (
        f"{ASSIGNMENT_SELECT} WHERE {where} AND a.busy_range && daterange(:start, :end, '[]') "
        "AND NOT (a.id = ANY(:excluding)) ORDER BY a.planned_from, a.id"
    )


def list_machine_overlaps(
    db: Session, *, machine_public_id: str, start: date, end: date | None, excluding: list[int]
) -> list[dict[str, Any]]:
    """Allocations keeping the machine on any of these days - held ones, and the days replaced or freed ones kept."""
    return _rows(
        db,
        _overlapping("a.equipment_asset_public_id = :machine_public_id"),
        {"machine_public_id": machine_public_id, "start": start, "end": end, "excluding": excluding},
    )


def list_machines_overlaps(db: Session, *, machine_public_ids: list[str], start: date, end: date | None) -> list[dict[str, Any]]:
    if not machine_public_ids:
        return []
    return _rows(
        db,
        _overlapping("a.equipment_asset_public_id = ANY(:machine_public_ids)"),
        {"machine_public_ids": machine_public_ids, "start": start, "end": end, "excluding": []},
    )


def list_unit_overlaps(
    db: Session, *, requirement_public_id: str, unit_number: int, start: date, end: date | None, excluding: list[int]
) -> list[dict[str, Any]]:
    return _rows(
        db,
        _overlapping("a.resource_requirement_public_id = :requirement_public_id AND a.unit_number = :unit_number"),
        {
            "requirement_public_id": requirement_public_id,
            "unit_number": unit_number,
            "start": start,
            "end": end,
            "excluding": excluding,
        },
    )


def insert_assignment(db: Session, *, values: dict[str, Any]) -> int:
    columns = ", ".join(values)
    placeholders = ", ".join(f":{name}" for name in values)
    return int(
        db.execute(text(f"INSERT INTO resource_assignment ({columns}) VALUES ({placeholders}) RETURNING id"), values).scalar_one()
    )


def update_assignment(db: Session, *, assignment_id: int, values: dict[str, Any], user_public_id: str, at: datetime) -> None:
    """Change an allocation and move its version on, once."""
    assignments = ", ".join(f"{name} = :{name}" for name in values)
    db.execute(
        text(
            f"""
            UPDATE resource_assignment
            SET {assignments}{", " if values else ""}
                assignment_version = assignment_version + 1, updated_by = :updated_by, updated_at = :updated_at
            WHERE id = :assignment_id
            """
        ),
        {**values, "assignment_id": assignment_id, "updated_by": user_public_id, "updated_at": at},
    )


# --- Trips and kit ------------------------------------------------------------------------------------------


def list_trip_rows(db: Session, *, assignment_ids: list[int]) -> list[dict[str, Any]]:
    return _rows_in(
        db,
        """
        SELECT t.id, t.trip_public_id, t.resource_assignment_id, t.trip_number, t.goes_on, t.note, t.created_by,
               creator.display_name AS created_by_display_name, t.created_at
        FROM resource_assignment_trip t
        LEFT JOIN app_user creator ON creator.public_id = t.created_by
        WHERE t.resource_assignment_id IN :ids
        ORDER BY t.resource_assignment_id, t.trip_number
        """,
        assignment_ids,
    )


def insert_trip(db: Session, *, values: dict[str, Any]) -> int:
    columns = ", ".join(values)
    placeholders = ", ".join(f":{name}" for name in values)
    return int(
        db.execute(
            text(f"INSERT INTO resource_assignment_trip ({columns}) VALUES ({placeholders}) RETURNING id"), values
        ).scalar_one()
    )


def update_trip_note(db: Session, *, trip_id: int, note: str | None) -> None:
    db.execute(text("UPDATE resource_assignment_trip SET note = :note WHERE id = :trip_id"), {"note": note, "trip_id": trip_id})


KIT_SELECT = """
    SELECT k.id, k.kit_line_public_id, k.resource_assignment_id, k.resource_assignment_trip_id, t.trip_number,
           k.equipment_asset_public_id, k.listed_kit_model_public_id, k.tracking_code, k.quantity, k.line_status_code,
           k.removed_by, remover.display_name AS removed_by_display_name, k.removed_at, k.decision_public_id,
           k.busy_from, k.busy_to, k.create_request_key, k.create_request_position,
           k.created_by,
           creator.display_name AS created_by_display_name, k.created_at,
           a.assignment_public_id, a.assignment_reference, a.work_order_code
    FROM resource_assignment_kit k
    INNER JOIN resource_assignment_trip t ON t.id = k.resource_assignment_trip_id
    INNER JOIN resource_assignment a ON a.id = k.resource_assignment_id
    LEFT JOIN app_user remover ON remover.public_id = k.removed_by
    LEFT JOIN app_user creator ON creator.public_id = k.created_by
"""


def list_kit_rows(db: Session, *, assignment_ids: list[int]) -> list[dict[str, Any]]:
    return _rows_in(db, f"{KIT_SELECT} WHERE k.resource_assignment_id IN :ids ORDER BY t.trip_number, k.id", assignment_ids)


def get_kit_row(db: Session, *, public_id: str) -> dict[str, Any] | None:
    return _first(db, f"{KIT_SELECT} WHERE k.kit_line_public_id = :public_id", {"public_id": public_id})


def list_listed_kit_overlaps(
    db: Session, *, piece_public_ids: list[str], start: date, end: date | None, excluding: list[int]
) -> list[dict[str, Any]]:
    """Listed lines of these pieces on any of these days, on any allocation."""
    if not piece_public_ids:
        return []
    return _rows(
        db,
        f"{KIT_SELECT} WHERE k.equipment_asset_public_id = ANY(:pieces) AND k.line_status_code = 'LISTED' "
        "AND k.busy_range && daterange(:start, :end, '[]') AND NOT (k.id = ANY(:excluding)) ORDER BY k.busy_from, k.id",
        {"pieces": piece_public_ids, "start": start, "end": end, "excluding": excluding},
    )


def insert_kit_line(db: Session, *, values: dict[str, Any]) -> int:
    columns = ", ".join(values)
    placeholders = ", ".join(f":{name}" for name in values)
    return int(
        db.execute(
            text(f"INSERT INTO resource_assignment_kit ({columns}) VALUES ({placeholders}) RETURNING id"), values
        ).scalar_one()
    )


def remove_kit_line(db: Session, *, kit_line_id: int, user_public_id: str, at: datetime) -> None:
    db.execute(
        text(
            """
            UPDATE resource_assignment_kit
            SET line_status_code = 'REMOVED', removed_by = :user_public_id, removed_at = :at
            WHERE id = :kit_line_id
            """
        ),
        {"kit_line_id": kit_line_id, "user_public_id": user_public_id, "at": at},
    )


def set_kit_decision(db: Session, *, kit_line_id: int, decision_public_id: str) -> None:
    db.execute(
        text("UPDATE resource_assignment_kit SET decision_public_id = :decision WHERE id = :kit_line_id"),
        {"kit_line_id": kit_line_id, "decision": decision_public_id},
    )

