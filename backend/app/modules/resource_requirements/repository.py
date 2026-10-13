"""Resource Requirement database access (WRR-001). Its own three tables only: nothing here reads or
writes a Work Order table beyond the foreign key the insert carries."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

REQUIREMENT_SELECT = """
    SELECT
        rr.id,
        rr.requirement_public_id,
        rr.requirement_reference,
        rr.work_order_public_id,
        rr.work_order_code,
        rr.work_order_line_public_id,
        rr.work_order_line_number,
        rr.source_offer_line_public_id,
        rr.account_public_id,
        rr.units_required,
        rr.required_from,
        rr.required_to,
        rr.crew_operators_required,
        rr.crew_helpers_required,
        rr.crew_notes,
        rr.priority_code,
        rr.planning_notes,
        rr.requirement_status_code,
        rr.requirement_version,
        rr.taxonomy_version,
        rr.cancellation_reason,
        rr.cancelled_by,
        canceller.display_name AS cancelled_by_display_name,
        rr.cancelled_at,
        rr.created_by,
        creator.display_name AS created_by_display_name,
        rr.created_at,
        rr.updated_by,
        updater.display_name AS updated_by_display_name,
        rr.updated_at
    FROM resource_requirement rr
    LEFT JOIN app_user creator ON creator.public_id = rr.created_by
    LEFT JOIN app_user updater ON updater.public_id = rr.updated_by
    LEFT JOIN app_user canceller ON canceller.public_id = rr.cancelled_by
"""

# Urgent first, then the earliest start; the reference breaks ties so the order is stable.
PLANNING_ORDER = """
    ORDER BY CASE rr.priority_code WHEN 'URGENT' THEN 0 ELSE 1 END, rr.required_from, rr.id
"""


def _mapping(row: Any) -> dict[str, Any]:
    return dict(row._mapping)


def get_requirement_row(db: Session, *, public_id: str) -> dict[str, Any] | None:
    row = db.execute(
        text(f"{REQUIREMENT_SELECT} WHERE rr.requirement_public_id = :public_id"), {"public_id": public_id}
    ).first()
    return _mapping(row) if row else None


def list_requirement_rows(
    db: Session,
    *,
    work_order_public_id: str | None,
    work_order_line_public_id: str | None,
    status_codes: tuple[str, ...] | None,
    equipment_class_code: str | None,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    conditions: list[str] = []
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if work_order_public_id is not None:
        conditions.append("rr.work_order_public_id = :work_order_public_id")
        params["work_order_public_id"] = work_order_public_id
    if work_order_line_public_id is not None:
        conditions.append("rr.work_order_line_public_id = :work_order_line_public_id")
        params["work_order_line_public_id"] = work_order_line_public_id
    if status_codes is not None:
        conditions.append("rr.requirement_status_code = ANY(:status_codes)")
        params["status_codes"] = list(status_codes)
    if equipment_class_code is not None:
        conditions.append(
            "EXISTS (SELECT 1 FROM resource_requirement_item i "
            "WHERE i.resource_requirement_id = rr.id AND i.equipment_class_code = :equipment_class_code)"
        )
        params["equipment_class_code"] = equipment_class_code
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = db.execute(
        text(f"{REQUIREMENT_SELECT} {where} {PLANNING_ORDER} LIMIT :limit OFFSET :offset"), params
    ).fetchall()
    return [_mapping(row) for row in rows]


def count_requirements_for_line(db: Session, *, work_order_line_public_id: str) -> int:
    return int(
        db.execute(
            text("SELECT COUNT(*) FROM resource_requirement WHERE work_order_line_public_id = :line_public_id"),
            {"line_public_id": work_order_line_public_id},
        ).scalar_one()
    )


def list_item_rows(db: Session, *, requirement_ids: list[int]) -> list[dict[str, Any]]:
    if not requirement_ids:
        return []
    statement = text(
        """
        SELECT id, resource_requirement_id, item_number, equipment_class_code, equipment_type_code,
               equipment_specification
        FROM resource_requirement_item
        WHERE resource_requirement_id IN :ids
        ORDER BY resource_requirement_id, item_number
        """
    ).bindparams(bindparam("ids", expanding=True))
    return [_mapping(row) for row in db.execute(statement, {"ids": requirement_ids}).fetchall()]


def list_item_capability_rows(db: Session, *, item_ids: list[int]) -> list[dict[str, Any]]:
    if not item_ids:
        return []
    statement = text(
        """
        SELECT resource_requirement_item_id, capability_code, minimum_value, choice_value
        FROM resource_requirement_item_capability
        WHERE resource_requirement_item_id IN :ids
        ORDER BY resource_requirement_item_id, id
        """
    ).bindparams(bindparam("ids", expanding=True))
    return [_mapping(row) for row in db.execute(statement, {"ids": item_ids}).fetchall()]


def find_requirement_by_create_request_key(db: Session, *, create_request_key: str) -> dict[str, Any] | None:
    """The requirement a request key made, with that request's fingerprint (null for one made before migration
    0050)."""
    row = db.execute(
        text(
            """
            SELECT requirement_public_id, work_order_line_public_id, create_request_fingerprint
            FROM resource_requirement
            WHERE create_request_key = :create_request_key
            """
        ),
        {"create_request_key": create_request_key},
    ).first()
    return _mapping(row) if row else None


def lock_requirement_row(db: Session, *, public_id: str) -> dict[str, Any] | None:
    """Take the row lock every change and cancellation holds until it commits."""
    row = db.execute(
        text(
            """
            SELECT id, requirement_public_id, work_order_line_public_id, requirement_status_code, requirement_version
            FROM resource_requirement
            WHERE requirement_public_id = :public_id
            FOR UPDATE
            """
        ),
        {"public_id": public_id},
    ).first()
    return _mapping(row) if row else None


def lock_open_ended_live_rows_of_work_order(db: Session, *, work_order_public_id: str) -> list[str]:
    """The public ids of a Work Order's requirements that are not cancelled and have no end of their own, their rows
    locked in id order (8A core): those that run to the line's or the contract's end."""
    rows = db.execute(
        text(
            """
            SELECT requirement_public_id
            FROM resource_requirement
            WHERE work_order_public_id = :work_order_public_id
              AND requirement_status_code <> 'CANCELLED'
              AND required_to IS NULL
            ORDER BY id
            FOR UPDATE
            """
        ),
        {"work_order_public_id": work_order_public_id},
    ).all()
    return [str(row[0]) for row in rows]


def insert_requirement(db: Session, *, values: dict[str, Any]) -> int:
    columns = ", ".join(values)
    placeholders = ", ".join(f":{column}" for column in values)
    return int(
        db.execute(
            text(f"INSERT INTO resource_requirement ({columns}) VALUES ({placeholders}) RETURNING id"), values
        ).scalar_one()
    )


def update_requirement(
    db: Session,
    *,
    requirement_id: int,
    expected_version: int,
    values: dict[str, Any],
    current_user_public_id: str | None,
    updated_at: datetime,
) -> int:
    assignments = ", ".join(f"{column} = :{column}" for column in values)
    result = db.execute(
        text(
            f"""
            UPDATE resource_requirement
            SET {assignments},
                requirement_version = requirement_version + 1,
                updated_by = :updated_by,
                updated_at = :updated_at
            WHERE id = :requirement_id
              AND requirement_version = :expected_version
              AND requirement_status_code <> 'CANCELLED'
            """
        ),
        {
            **values,
            "updated_by": current_user_public_id,
            "updated_at": updated_at,
            "requirement_id": requirement_id,
            "expected_version": expected_version,
        },
    )
    return result.rowcount or 0


def cancel_requirement(
    db: Session,
    *,
    requirement_id: int,
    expected_version: int,
    reason: str,
    current_user_public_id: str | None,
    cancelled_at: datetime,
) -> int:
    result = db.execute(
        text(
            """
            UPDATE resource_requirement
            SET requirement_status_code = 'CANCELLED',
                cancellation_reason = :reason,
                cancelled_by = :cancelled_by,
                cancelled_at = :cancelled_at,
                requirement_version = requirement_version + 1,
                updated_by = :cancelled_by,
                updated_at = :cancelled_at
            WHERE id = :requirement_id
              AND requirement_version = :expected_version
              AND requirement_status_code <> 'CANCELLED'
            """
        ),
        {
            "reason": reason,
            "cancelled_by": current_user_public_id,
            "cancelled_at": cancelled_at,
            "requirement_id": requirement_id,
            "expected_version": expected_version,
        },
    )
    return result.rowcount or 0


def set_requirement_status(db: Session, *, requirement_id: int, status_code: str) -> None:
    """Set a live requirement's fulfilment status (8A core). Not a user's edit: its version and who last
    changed it stay as they are, so a change form opened before stays valid; the event records it."""
    db.execute(
        text(
            """
            UPDATE resource_requirement
            SET requirement_status_code = :status_code
            WHERE id = :requirement_id AND requirement_status_code <> 'CANCELLED'
            """
        ),
        {"status_code": status_code, "requirement_id": requirement_id},
    )


def delete_items(db: Session, *, requirement_id: int) -> None:
    """Remove a requirement's items and their capabilities, before a whole replacement writes new ones."""
    db.execute(
        text(
            """
            DELETE FROM resource_requirement_item_capability c
            USING resource_requirement_item i
            WHERE i.id = c.resource_requirement_item_id
              AND i.resource_requirement_id = :requirement_id
            """
        ),
        {"requirement_id": requirement_id},
    )
    db.execute(
        text("DELETE FROM resource_requirement_item WHERE resource_requirement_id = :requirement_id"),
        {"requirement_id": requirement_id},
    )


def insert_item(
    db: Session,
    *,
    requirement_id: int,
    item_number: int,
    equipment_class_code: str,
    equipment_type_code: str | None,
    equipment_specification: str | None,
) -> int:
    return int(
        db.execute(
            text(
                """
                INSERT INTO resource_requirement_item
                    (resource_requirement_id, item_number, equipment_class_code, equipment_type_code,
                     equipment_specification)
                VALUES (:requirement_id, :item_number, :equipment_class_code, :equipment_type_code,
                        :equipment_specification)
                RETURNING id
                """
            ),
            {
                "requirement_id": requirement_id,
                "item_number": item_number,
                "equipment_class_code": equipment_class_code,
                "equipment_type_code": equipment_type_code,
                "equipment_specification": equipment_specification,
            },
        ).scalar_one()
    )


def insert_item_capability(
    db: Session,
    *,
    item_id: int,
    equipment_class_code: str,
    capability_code: str,
    minimum_value: Decimal | None,
    choice_value: str | None,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO resource_requirement_item_capability
                (resource_requirement_item_id, equipment_class_code, capability_code, minimum_value, choice_value)
            VALUES (:item_id, :equipment_class_code, :capability_code, :minimum_value, :choice_value)
            """
        ),
        {
            "item_id": item_id,
            "equipment_class_code": equipment_class_code,
            "capability_code": capability_code,
            "minimum_value": minimum_value,
            "choice_value": choice_value,
        },
    )
