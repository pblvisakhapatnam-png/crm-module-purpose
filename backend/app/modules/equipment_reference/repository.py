"""Equipment Reference database access. Its own tables only.

The structure (classes, types, capabilities, aliases, part fits) has no writes outside a migration. Models,
machines and parts, the import and the Fleet Admin's corrections (ERT-1) are written below, each through
the service that holds the module's write lock.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session
from app.shared.transactions import take_advisory_lock


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


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str)


def list_taxonomy_version_rows(db: Session) -> list[dict[str, Any]]:
    return _rows(
        db,
        """
        SELECT version_number, version_label, source_note, loaded_at, component_depth
        FROM equipment_taxonomy_version
        ORDER BY version_number
        """,
    )


def list_class_rows(db: Session) -> list[dict[str, Any]]:
    return _rows(
        db,
        """
        SELECT class_code, class_label, class_kind_code, tracking_code, display_order, introduced_in_version,
               retired_in_version
        FROM equipment_class
        ORDER BY display_order, class_code
        """,
    )


def list_class_business_line_rows(db: Session) -> list[dict[str, Any]]:
    return _rows(
        db,
        """
        SELECT class_code, business_line_code, introduced_in_version, retired_in_version
        FROM equipment_class_business_line
        ORDER BY class_code, business_line_code
        """,
    )


def list_type_rows(db: Session) -> list[dict[str, Any]]:
    return _rows(
        db,
        """
        SELECT type_code, class_code, type_label, display_order, introduced_in_version, retired_in_version
        FROM equipment_type
        ORDER BY class_code, display_order, type_code
        """,
    )


def list_capability_rows(db: Session) -> list[dict[str, Any]]:
    return _rows(
        db,
        """
        SELECT capability_code, capability_label, unit_code, value_kind_code, allowed_values,
               introduced_in_version, retired_in_version
        FROM equipment_capability
        ORDER BY capability_code
        """,
    )


def list_class_capability_rows(db: Session) -> list[dict[str, Any]]:
    return _rows(
        db,
        """
        SELECT class_code, capability_code, is_key, display_order, introduced_in_version, retired_in_version
        FROM equipment_class_capability
        ORDER BY class_code, display_order, capability_code
        """,
    )


def list_alias_rows(db: Session) -> list[dict[str, Any]]:
    return _rows(
        db,
        """
        SELECT term, normalized_term, source_code, class_code, type_code, introduced_in_version, retired_in_version
        FROM equipment_term_alias
        ORDER BY source_code, normalized_term
        """,
    )


def list_part_fit_rows(db: Session) -> list[dict[str, Any]]:
    return _rows(
        db,
        """
        SELECT part_class_code, parent_class_code, fit_kind_code, introduced_in_version, retired_in_version
        FROM equipment_part_fit
        ORDER BY part_class_code, parent_class_code
        """,
    )


# --- The write lock and the change count ------------------------------------------------------------

# One lock for every write in this module and every preview computation. Imports, corrections and pairs
# are few and made by one or two people, so serializing them costs nothing and leaves no race to reason
# about between a confirmation and a correction.
_WRITE_LOCK_KEY = "equipment_reference.write"


def take_write_lock(db: Session) -> None:
    take_advisory_lock(db, _WRITE_LOCK_KEY)


def bump_change_number(db: Session) -> int:
    return int(
        db.execute(
            text(
                "UPDATE equipment_reference_state SET change_number = change_number + 1 "
                "WHERE state_key = 'EQUIPMENT' RETURNING change_number"
            )
        ).scalar_one()
    )


def current_change_number(db: Session) -> int:
    return int(
        db.execute(text("SELECT change_number FROM equipment_reference_state WHERE state_key = 'EQUIPMENT'")).scalar_one()
    )


# --- Category rules ----------------------------------------------------------------------------------


def list_category_rule_rows(db: Session) -> list[dict[str, Any]]:
    return _rows(
        db,
        """
        SELECT r.normalized_category, a.term AS category_term, a.class_code, r.capability_code, r.plum_unit_code,
               r.plausible_low, r.plausible_high, r.check_code
        FROM equipment_source_category_rule r
        INNER JOIN equipment_term_alias a
            ON a.source_code = r.alias_source_code AND a.normalized_term = r.normalized_category
        ORDER BY a.class_code, r.normalized_category
        """,
    )


# --- Models ------------------------------------------------------------------------------------------

MODEL_SELECT = """
    SELECT m.id, m.model_public_id, m.maker, m.model_name, m.normalized_key, m.class_code, m.type_code,
           m.maker_part_number, m.model_version, m.is_retired, m.created_by, m.created_at, m.updated_by,
           m.updated_at,
           (SELECT COUNT(*) FROM equipment_asset a WHERE a.equipment_model_id = m.id) AS asset_count,
           (SELECT COUNT(*) FROM equipment_asset a
            WHERE a.equipment_model_id = m.id AND a.asset_kind_code = 'MACHINE' AND a.asset_status_code = 'ACTIVE')
               AS active_unit_count,
           (SELECT COALESCE(SUM(a.quantity), 0) FROM equipment_asset a
            WHERE a.equipment_model_id = m.id AND a.origin_code = 'PLATFORM' AND a.asset_status_code = 'ACTIVE')
               AS pieces_held
    FROM equipment_model m
"""


def list_model_rows(db: Session) -> list[dict[str, Any]]:
    return _rows(db, f"{MODEL_SELECT} ORDER BY m.class_code, m.normalized_key, m.id")


def get_model_row(db: Session, *, public_id: str) -> dict[str, Any] | None:
    return _first(db, f"{MODEL_SELECT} WHERE m.model_public_id = :public_id", {"public_id": public_id})


def find_model_by_create_request_key(db: Session, *, create_request_key: str) -> dict[str, Any] | None:
    """The model a request key made, with that request's fingerprint (null for a model made before migration 0050)."""
    return _first(
        db,
        "SELECT model_public_id, create_request_fingerprint FROM equipment_model WHERE create_request_key = :key",
        {"key": create_request_key},
    )


def find_model_by_key(db: Session, *, maker: str, model_name: str, class_code: str) -> dict[str, Any] | None:
    """The model with this maker and name in this class, compared in the database's own normalized form."""
    return _first(
        db,
        """
        SELECT model_public_id FROM equipment_model
        WHERE class_code = :class_code
          AND normalized_key = upper(btrim(regexp_replace(:maker || ' ' || :model_name, '\\s+', ' ', 'g')))
        """,
        {"maker": maker, "model_name": model_name, "class_code": class_code},
    )


def list_model_capability_rows(db: Session, *, model_ids: list[int] | None = None) -> list[dict[str, Any]]:
    sql = """
        SELECT equipment_model_id, capability_code, capability_value, choice_value
        FROM equipment_model_capability
    """
    if model_ids is None:
        return _rows(db, f"{sql} ORDER BY equipment_model_id, id")
    return _rows_in(db, f"{sql} WHERE equipment_model_id IN :ids ORDER BY equipment_model_id, id", model_ids)


def insert_model(db: Session, *, values: dict[str, Any]) -> int:
    columns = ", ".join(values)
    placeholders = ", ".join(f":{column}" for column in values)
    return int(
        db.execute(text(f"INSERT INTO equipment_model ({columns}) VALUES ({placeholders}) RETURNING id"), values).scalar_one()
    )


def update_model(
    db: Session, *, model_id: int, expected_version: int, values: dict[str, Any], user_public_id: str | None, at: datetime
) -> int:
    assignments = ", ".join(f"{column} = :{column}" for column in values)
    result = db.execute(
        text(
            f"""
            UPDATE equipment_model
            SET {assignments}, model_version = model_version + 1, updated_by = :updated_by, updated_at = :updated_at
            WHERE id = :model_id AND model_version = :expected_version
            """
        ),
        {**values, "updated_by": user_public_id, "updated_at": at, "model_id": model_id, "expected_version": expected_version},
    )
    return result.rowcount or 0


def delete_model_capabilities(db: Session, *, model_id: int) -> None:
    db.execute(text("DELETE FROM equipment_model_capability WHERE equipment_model_id = :model_id"), {"model_id": model_id})


def insert_model_capability(
    db: Session, *, model_id: int, class_code: str, capability_code: str, value: Decimal | None, choice: str | None
) -> None:
    db.execute(
        text(
            """
            INSERT INTO equipment_model_capability
                (equipment_model_id, class_code, capability_code, capability_value, choice_value)
            VALUES (:model_id, :class_code, :capability_code, :value, :choice)
            """
        ),
        {"model_id": model_id, "class_code": class_code, "capability_code": capability_code, "value": value, "choice": choice},
    )


def list_model_mapping_rows(db: Session) -> list[dict[str, Any]]:
    return _rows(
        db,
        """
        SELECT k.source_name, k.normalized_source_name, k.mapped_by, k.mapped_at, m.model_public_id, m.id AS model_id
        FROM equipment_model_source_key k
        INNER JOIN equipment_model m ON m.id = k.equipment_model_id
        WHERE k.provider_code = 'PLUM'
        ORDER BY k.normalized_source_name
        """,
    )


def find_model_mapping(db: Session, *, source_name: str) -> dict[str, Any] | None:
    return _first(
        db,
        """
        SELECT k.id, k.source_name, m.model_public_id
        FROM equipment_model_source_key k
        INNER JOIN equipment_model m ON m.id = k.equipment_model_id
        WHERE k.provider_code = 'PLUM'
          AND k.normalized_source_name = upper(btrim(regexp_replace(:source_name, '\\s+', ' ', 'g')))
        FOR UPDATE OF k
        """,
        {"source_name": source_name},
    )


def insert_model_mapping(db: Session, *, source_name: str, model_id: int, user_public_id: str | None, at: datetime) -> None:
    db.execute(
        text(
            """
            INSERT INTO equipment_model_source_key (provider_code, source_name, equipment_model_id, mapped_by, mapped_at)
            VALUES ('PLUM', :source_name, :model_id, :mapped_by, :mapped_at)
            """
        ),
        {"source_name": source_name, "model_id": model_id, "mapped_by": user_public_id, "mapped_at": at},
    )


def update_model_mapping(db: Session, *, mapping_id: int, model_id: int, user_public_id: str | None, at: datetime) -> None:
    db.execute(
        text(
            "UPDATE equipment_model_source_key SET equipment_model_id = :model_id, mapped_by = :mapped_by, "
            "mapped_at = :mapped_at WHERE id = :mapping_id"
        ),
        {"mapping_id": mapping_id, "model_id": model_id, "mapped_by": user_public_id, "mapped_at": at},
    )


def delete_model_mapping(db: Session, *, mapping_id: int) -> None:
    db.execute(text("DELETE FROM equipment_model_source_key WHERE id = :mapping_id"), {"mapping_id": mapping_id})


# --- Model fits: which crane models a kit model fits (ERT-2) -------------------------------------------


def list_model_fit_rows(db: Session, *, model_ids: list[int] | None = None) -> list[dict[str, Any]]:
    """Every fit in which one of the models is the kit model or the crane model; every fit when none are
    named."""
    sql = """
        SELECT f.kit_model_id, k.model_public_id AS kit_model_public_id,
               f.crane_model_id, c.model_public_id AS crane_model_public_id,
               c.maker || ' ' || c.model_name AS crane_model_label, c.is_retired AS crane_model_is_retired,
               (SELECT COUNT(*) FROM equipment_asset a
                WHERE a.equipment_model_id = c.id AND a.asset_kind_code = 'MACHINE' AND a.asset_status_code = 'ACTIVE')
                   AS crane_active_unit_count
        FROM equipment_model_fit f
        INNER JOIN equipment_model k ON k.id = f.kit_model_id
        INNER JOIN equipment_model c ON c.id = f.crane_model_id
    """
    order = " ORDER BY f.kit_model_id, c.maker, c.model_name, f.id"
    if model_ids is None:
        return _rows(db, sql + order)
    return _rows_in(db, sql + " WHERE f.kit_model_id IN :ids OR f.crane_model_id IN :ids" + order, model_ids)


def count_fits_to_crane_model(db: Session, *, model_id: int) -> int:
    return int(
        db.execute(
            text("SELECT COUNT(*) FROM equipment_model_fit WHERE crane_model_id = :model_id"), {"model_id": model_id}
        ).scalar_one()
    )


def delete_model_fits(db: Session, *, kit_model_id: int) -> None:
    db.execute(text("DELETE FROM equipment_model_fit WHERE kit_model_id = :model_id"), {"model_id": kit_model_id})


def insert_model_fit(
    db: Session, *, kit_model_id: int, kit_class_code: str, crane_model_id: int, crane_class_code: str, user_public_id: str | None
) -> None:
    db.execute(
        text(
            """
            INSERT INTO equipment_model_fit (kit_model_id, kit_class_code, crane_model_id, crane_class_code, created_by)
            VALUES (:kit_model_id, :kit_class_code, :crane_model_id, :crane_class_code, :created_by)
            """
        ),
        {
            "kit_model_id": kit_model_id,
            "kit_class_code": kit_class_code,
            "crane_model_id": crane_model_id,
            "crane_class_code": crane_class_code,
            "created_by": user_public_id,
        },
    )


def list_kit_held_rows(db: Session, *, crane_model_id: int) -> list[dict[str, Any]]:
    """Every kit model fitting the crane model, with the active pieces held of it: counted sets by their
    quantity, and the records holding them. A kit model with nothing held is listed too, with zero."""
    return _rows(
        db,
        """
        SELECT k.id AS kit_model_id, k.model_public_id AS kit_model_public_id, k.maker, k.model_name,
               k.class_code, k.type_code,
               COALESCE(SUM(a.quantity) FILTER (WHERE a.asset_status_code = 'ACTIVE'), 0) AS pieces_held,
               COUNT(a.id) FILTER (WHERE a.asset_status_code = 'ACTIVE') AS records_held
        FROM equipment_model_fit f
        INNER JOIN equipment_model k ON k.id = f.kit_model_id
        LEFT JOIN equipment_asset a ON a.equipment_model_id = k.id AND a.origin_code = 'PLATFORM'
        WHERE f.crane_model_id = :crane_model_id
        GROUP BY k.id, k.model_public_id, k.maker, k.model_name, k.class_code, k.type_code
        ORDER BY k.class_code, k.maker, k.model_name, k.id
        """,
        {"crane_model_id": crane_model_id},
    )


# --- Assets ------------------------------------------------------------------------------------------

ASSET_SELECT = """
    SELECT a.id, a.asset_public_id, a.asset_reference, a.asset_kind_code, a.origin_code, a.quantity, a.class_code,
           a.type_code, a.equipment_model_id, m.model_public_id, a.machine_number, a.engine_number, a.chassis_number,
           a.commenced_year, a.owning_company, a.asset_status_code, a.serial_number, a.year_of_manufacture,
           a.retired_on, a.retirement_reason_code, a.retirement_note,
           a.asset_version, a.facts_report_date, a.created_by, a.created_at, a.updated_by, a.updated_at,
           b.source_values, b.reconciliation_status_code, b.provider_key,
           li.import_public_id AS last_import_public_id
    FROM equipment_asset a
    LEFT JOIN equipment_model m ON m.id = a.equipment_model_id
    LEFT JOIN equipment_source_binding b ON b.equipment_asset_id = a.id
    LEFT JOIN equipment_source_import li ON li.id = b.last_import_id
"""


def get_asset_row(db: Session, *, public_id: str) -> dict[str, Any] | None:
    return _first(db, f"{ASSET_SELECT} WHERE a.asset_public_id = :public_id", {"public_id": public_id})


def get_asset_row_by_id(db: Session, *, asset_id: int) -> dict[str, Any]:
    row = _first(
        db,
        "SELECT id, asset_public_id, asset_kind_code, class_code, asset_status_code, asset_version FROM equipment_asset "
        "WHERE id = :asset_id FOR UPDATE",
        {"asset_id": asset_id},
    )
    assert row is not None
    return row


def lock_asset_row(db: Session, *, public_id: str) -> dict[str, Any] | None:
    return _first(
        db,
        "SELECT id, asset_public_id, asset_kind_code, origin_code, quantity, class_code, equipment_model_id, asset_status_code, "
        "asset_version "
        "FROM equipment_asset WHERE asset_public_id = :public_id FOR UPDATE",
        {"public_id": public_id},
    )


# What "details to complete" means (ERT-1 section 5A, ERT-2 Q5): a machine without its serial number or year
# of manufacture, or a piece of kit tracked one by one without its own number. The machine summary's
# `details_missing` says the same of one record.
DETAILS_TO_COMPLETE = """(
    (a.asset_kind_code = 'MACHINE' AND (a.serial_number IS NULL OR a.year_of_manufacture IS NULL))
    OR (a.origin_code = 'PLATFORM' AND a.serial_number IS NULL
        AND EXISTS (SELECT 1 FROM equipment_class dc WHERE dc.class_code = a.class_code AND dc.tracking_code = 'SINGLE'))
)"""


def list_asset_rows(
    db: Session,
    *,
    kind_code: str | None,
    class_code: str | None,
    type_code: str | None,
    status_code: str | None,
    flagged_only: bool,
    details_to_complete: bool,
    search: str | None,
    limit: int,
    offset: int,
    kit_model_public_id: str | None = None,
    fits_model_public_id: str | None = None,
) -> list[dict[str, Any]]:
    conditions: list[str] = []
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    for column, value, name in (
        ("a.asset_kind_code", kind_code, "kind_code"),
        ("a.class_code", class_code, "class_code"),
        ("a.type_code", type_code, "type_code"),
        ("a.asset_status_code", status_code, "status_code"),
        ("m.model_public_id", kit_model_public_id, "kit_model_public_id"),
    ):
        if value is not None:
            conditions.append(f"{column} = :{name}")
            params[name] = value
    if fits_model_public_id is not None:
        # The kit held for a machine model: pieces of every kit model that fits it.
        conditions.append(
            "a.origin_code = 'PLATFORM' AND EXISTS (SELECT 1 FROM equipment_model_fit ff "
            "INNER JOIN equipment_model fc ON fc.id = ff.crane_model_id "
            "WHERE ff.kit_model_id = a.equipment_model_id AND fc.model_public_id = :fits_model_public_id)"
        )
        params["fits_model_public_id"] = fits_model_public_id
    if flagged_only:
        conditions.append("EXISTS (SELECT 1 FROM equipment_asset_flag f WHERE f.equipment_asset_id = a.id)")
    if details_to_complete:
        conditions.append(DETAILS_TO_COMPLETE)
    if search:
        # A literal search: % and _ typed by the user match themselves. A piece of kit is found by its own
        # number, as a machine is by Plum's.
        conditions.append(
            "(a.machine_number ILIKE :search ESCAPE '\\' OR a.asset_reference ILIKE :search ESCAPE '\\'"
            " OR a.serial_number ILIKE :search ESCAPE '\\')"
        )
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        params["search"] = f"%{escaped}%"
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return _rows(
        db, f"{ASSET_SELECT} {where} ORDER BY a.class_code, a.machine_number, a.id LIMIT :limit OFFSET :offset", params
    )


def list_asset_keys_using_model(db: Session, *, model_id: int) -> list[dict[str, Any]]:
    return _rows(
        db,
        "SELECT id, asset_public_id FROM equipment_asset WHERE equipment_model_id = :model_id ORDER BY id",
        {"model_id": model_id},
    )


def list_plum_bound_asset_rows(db: Session) -> list[dict[str, Any]]:
    """Every asset bound to a Plum machine number: what a report is compared with."""
    return _rows(db, f"{ASSET_SELECT} WHERE b.provider_code = 'PLUM' ORDER BY a.id")


def list_asset_flag_rows(db: Session, *, asset_ids: list[int]) -> list[dict[str, Any]]:
    return _rows_in(
        db,
        """
        SELECT f.equipment_asset_id, f.flag_code, f.subject_code, f.raised_at,
               i.import_public_id AS raised_by_import_public_id
        FROM equipment_asset_flag f
        LEFT JOIN equipment_source_import i ON i.id = f.raised_by_import_id
        WHERE f.equipment_asset_id IN :ids
        ORDER BY f.equipment_asset_id, f.flag_code, f.subject_code
        """,
        asset_ids,
    )


def list_asset_capability_rows(db: Session, *, asset_ids: list[int]) -> list[dict[str, Any]]:
    return _rows_in(
        db,
        """
        SELECT c.equipment_asset_id, c.capability_code, c.capability_value, c.choice_value, c.reason, c.set_by,
               u.display_name AS set_by_display_name, c.set_at
        FROM equipment_asset_capability c
        LEFT JOIN app_user u ON u.public_id = c.set_by
        WHERE c.equipment_asset_id IN :ids
        ORDER BY c.equipment_asset_id, c.id
        """,
        asset_ids,
    )


def list_asset_correction_rows(db: Session, *, asset_ids: list[int], open_only: bool) -> list[dict[str, Any]]:
    status_filter = "AND c.correction_status_code = 'OPEN'" if open_only else ""
    return _rows_in(
        db,
        f"""
        SELECT c.id, c.correction_public_id, c.equipment_asset_id, c.field_code, c.plum_value, c.corrected_value,
               c.reason, c.correction_status_code, c.closed_reason_code, c.closed_by,
               closer.display_name AS closed_by_display_name, c.closed_at,
               c.recorded_by, recorder.display_name AS recorded_by_display_name, c.recorded_at
        FROM equipment_asset_correction c
        LEFT JOIN app_user recorder ON recorder.public_id = c.recorded_by
        LEFT JOIN app_user closer ON closer.public_id = c.closed_by
        WHERE c.equipment_asset_id IN :ids {status_filter}
        ORDER BY c.equipment_asset_id, c.recorded_at DESC, c.id DESC
        """,
        asset_ids,
    )


def list_asset_link_rows(db: Session, *, asset_ids: list[int]) -> list[dict[str, Any]]:
    """Every link, open or removed, in which one of the assets is the machine or the part."""
    return _rows_in(
        db,
        """
        SELECT l.id, l.link_public_id, l.parent_asset_id, l.child_asset_id, l.link_kind_code, l.fitted_on, l.removed_on,
               l.fitted_at, l.removed_at,
               p.asset_public_id AS parent_public_id, p.asset_reference AS parent_reference,
               p.machine_number AS parent_machine_number, p.class_code AS parent_class_code,
               p.asset_version AS parent_asset_version,
               c.asset_public_id AS child_public_id, c.asset_reference AS child_reference,
               c.machine_number AS child_machine_number, c.class_code AS child_class_code,
               c.asset_version AS child_asset_version
        FROM equipment_asset_link l
        INNER JOIN equipment_asset p ON p.id = l.parent_asset_id
        INNER JOIN equipment_asset c ON c.id = l.child_asset_id
        WHERE l.parent_asset_id IN :ids OR l.child_asset_id IN :ids
        ORDER BY l.fitted_on DESC, l.id DESC
        """,
        asset_ids,
    )


def list_open_link_rows(db: Session) -> list[dict[str, Any]]:
    return _rows(
        db,
        """
        SELECT l.parent_asset_id, l.child_asset_id, p.asset_public_id AS parent_public_id, c.class_code AS child_class_code
        FROM equipment_asset_link l
        INNER JOIN equipment_asset p ON p.id = l.parent_asset_id
        INNER JOIN equipment_asset c ON c.id = l.child_asset_id
        WHERE l.removed_on IS NULL
        """,
    )


# --- What Eligibility reads (ELG-1): each asset's identity, kind and status, and the open fitted links ------

ASSET_FACTS_SELECT = """
    SELECT a.asset_public_id, a.asset_reference, a.asset_kind_code, a.origin_code, a.class_code, a.type_code,
           a.machine_number, a.serial_number, a.asset_status_code, a.asset_version,
           CAST(a.created_at AT TIME ZONE 'Asia/Kolkata' AS date) AS added_on
    FROM equipment_asset a
"""


def list_asset_fact_rows(db: Session, *, public_ids: list[str] | None = None, active_only: bool = False) -> list[dict[str, Any]]:
    condition = "WHERE a.asset_status_code = 'ACTIVE'" if active_only else ""
    if public_ids is None:
        return _rows(db, f"{ASSET_FACTS_SELECT} {condition} ORDER BY a.id")
    return _rows_in(db, f"{ASSET_FACTS_SELECT} WHERE a.asset_public_id IN :ids ORDER BY a.id", public_ids)


def list_open_fitted_link_pairs(db: Session) -> list[dict[str, Any]]:
    return _rows(
        db,
        """
        SELECT p.asset_public_id AS parent_public_id, c.asset_public_id AS child_public_id
        FROM equipment_asset_link l
        INNER JOIN equipment_asset p ON p.id = l.parent_asset_id
        INNER JOIN equipment_asset c ON c.id = l.child_asset_id
        WHERE l.removed_on IS NULL AND l.link_kind_code = 'FITTED'
        ORDER BY l.id
        """,
    )


def list_all_asset_capability_rows(db: Session) -> list[dict[str, Any]]:
    return _rows(
        db, "SELECT equipment_asset_id, capability_code, capability_value, choice_value FROM equipment_asset_capability"
    )


def list_all_open_correction_rows(db: Session) -> list[dict[str, Any]]:
    return _rows(
        db,
        """
        SELECT id, correction_public_id, equipment_asset_id, field_code, plum_value, corrected_value
        FROM equipment_asset_correction WHERE correction_status_code = 'OPEN'
        ORDER BY equipment_asset_id, id
        """,
    )


def insert_asset(db: Session, *, values: dict[str, Any]) -> int:
    columns = ", ".join(values)
    placeholders = ", ".join(f":{column}" for column in values)
    return int(
        db.execute(text(f"INSERT INTO equipment_asset ({columns}) VALUES ({placeholders}) RETURNING id"), values).scalar_one()
    )


def update_asset(
    db: Session,
    *,
    asset_id: int,
    values: dict[str, Any],
    user_public_id: str | None,
    at: datetime,
    expected_version: int | None = None,
    bump_version: bool = True,
) -> int:
    """Change an asset and increase its version - unless `bump_version` is False, when the caller moves the
    version on itself, once, after everything it changes. With an expected version, only if nobody changed
    it since."""
    assignments = "".join(f"{column} = :{column}, " for column in values)
    version_guard = "AND asset_version = :expected_version" if expected_version is not None else ""
    increment = "asset_version + 1" if bump_version else "asset_version"
    result = db.execute(
        text(
            f"""
            UPDATE equipment_asset
            SET {assignments}asset_version = {increment}, updated_by = :updated_by, updated_at = :updated_at
            WHERE id = :asset_id {version_guard}
            """
        ),
        {
            **values,
            "updated_by": user_public_id,
            "updated_at": at,
            "asset_id": asset_id,
            "expected_version": expected_version,
        },
    )
    return result.rowcount or 0


def set_facts_report_date(db: Session, *, asset_ids: list[int], report_date: date) -> None:
    """How fresh the Plum facts are: the date of the report that last carried the asset. Not a change of
    facts, so the asset's version stays as it is."""
    if not asset_ids:
        return
    statement = text("UPDATE equipment_asset SET facts_report_date = :report_date WHERE id IN :ids").bindparams(
        bindparam("ids", expanding=True)
    )
    db.execute(statement, {"ids": asset_ids, "report_date": report_date})


def delete_asset_capabilities_not_of_class(db: Session, *, asset_id: int, class_code: str) -> list[str]:
    """Before a machine's class changes: remove its own values the new class does not take."""
    rows = db.execute(
        text(
            """
            DELETE FROM equipment_asset_capability c
            WHERE c.equipment_asset_id = :asset_id
              AND NOT EXISTS (
                  SELECT 1 FROM equipment_class_capability cc
                  WHERE cc.class_code = :class_code AND cc.capability_code = c.capability_code
              )
            RETURNING c.capability_code
            """
        ),
        {"asset_id": asset_id, "class_code": class_code},
    ).fetchall()
    return sorted(str(row[0]) for row in rows)


def delete_asset_capabilities(db: Session, *, asset_id: int) -> None:
    db.execute(text("DELETE FROM equipment_asset_capability WHERE equipment_asset_id = :asset_id"), {"asset_id": asset_id})


def insert_asset_capability(
    db: Session,
    *,
    asset_id: int,
    class_code: str,
    capability_code: str,
    value: Decimal | None,
    choice: str | None,
    reason: str,
    user_public_id: str,
    at: datetime,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO equipment_asset_capability
                (equipment_asset_id, class_code, capability_code, capability_value, choice_value, reason, set_by, set_at)
            VALUES (:asset_id, :class_code, :capability_code, :value, :choice, :reason, :set_by, :set_at)
            """
        ),
        {
            "asset_id": asset_id,
            "class_code": class_code,
            "capability_code": capability_code,
            "value": value,
            "choice": choice,
            "reason": reason,
            "set_by": user_public_id,
            "set_at": at,
        },
    )


def set_asset_flags(
    db: Session,
    *,
    asset_id: int,
    flags: set[tuple[str, str]],
    keep_codes: frozenset[str],
    import_id: int | None,
    at: datetime,
) -> bool:
    """Make the asset's flags `flags`, leaving any flag whose code is in `keep_codes` as it is. A flag that
    stays keeps the import and time it was first raised by. Returns whether anything changed."""
    current = {
        (str(row[0]), str(row[1]))
        for row in db.execute(
            text("SELECT flag_code, subject_code FROM equipment_asset_flag WHERE equipment_asset_id = :asset_id"),
            {"asset_id": asset_id},
        ).fetchall()
    }
    managed = {flag for flag in current if flag[0] not in keep_codes}
    wanted = {flag for flag in flags if flag[0] not in keep_codes}
    for flag_code, subject_code in sorted(managed - wanted):
        delete_asset_flag(db, asset_id=asset_id, flag_code=flag_code, subject_code=subject_code)
    for flag_code, subject_code in sorted(wanted - current):
        insert_asset_flag(db, asset_id=asset_id, flag_code=flag_code, subject_code=subject_code, import_id=import_id, at=at)
    return bool((managed - wanted) or (wanted - current))


def insert_asset_flag(
    db: Session, *, asset_id: int, flag_code: str, subject_code: str, import_id: int | None, at: datetime
) -> bool:
    """Raise a flag; False when the asset already had it (it keeps when it was first raised)."""
    result = db.execute(
        text(
            """
            INSERT INTO equipment_asset_flag (equipment_asset_id, flag_code, subject_code, raised_by_import_id, raised_at)
            VALUES (:asset_id, :flag_code, :subject_code, :import_id, :at)
            ON CONFLICT ON CONSTRAINT uq_equipment_asset_flag DO NOTHING
            """
        ),
        {"asset_id": asset_id, "flag_code": flag_code, "subject_code": subject_code, "import_id": import_id, "at": at},
    )
    return bool(result.rowcount)


def delete_asset_flag(db: Session, *, asset_id: int, flag_code: str, subject_code: str | None = None) -> bool:
    """Remove a flag - one subject of it, or every subject when none is named. True when one was removed."""
    subject_filter = "AND subject_code = :subject_code" if subject_code is not None else ""
    result = db.execute(
        text(
            f"DELETE FROM equipment_asset_flag WHERE equipment_asset_id = :asset_id AND flag_code = :flag_code {subject_filter}"
        ),
        {"asset_id": asset_id, "flag_code": flag_code, "subject_code": subject_code},
    )
    return bool(result.rowcount)


# A part that ought to be fitted and is not: a part of a class the structure fits by a dated link, with no
# open link. Kit is never fitted - it is held for the models it fits (ERT-2) - so it never raises the flag.
_UNFITTED_PART = """
    a.asset_kind_code = 'PART'
    AND EXISTS (SELECT 1 FROM equipment_part_fit pf WHERE pf.part_class_code = a.class_code AND pf.fit_kind_code = 'FITTED')
    AND NOT EXISTS (SELECT 1 FROM equipment_asset_link l WHERE l.child_asset_id = a.id AND l.removed_on IS NULL)
"""


def list_unfitted_part_ids(db: Session) -> list[int]:
    """Every part not fitted to a machine now, retired ones included: a retired carrier still unpaired is
    still unpaired."""
    return [
        int(row[0])
        for row in db.execute(text(f"SELECT a.id FROM equipment_asset a WHERE {_UNFITTED_PART} ORDER BY a.id")).fetchall()
    ]


def sync_part_not_fitted(db: Session, *, asset_ids: Iterable[int], at: datetime) -> set[int]:
    """PART_NOT_FITTED as it now stands, for the assets named only: raised on a part fitted to no machine,
    removed from every other. For a change outside an import, which recomputes it for every part. Returns
    the assets whose flag changed."""
    ids = sorted(set(asset_ids))
    if not ids:
        return set()
    statement = text(f"SELECT a.id FROM equipment_asset a WHERE a.id IN :ids AND {_UNFITTED_PART}").bindparams(
        bindparam("ids", expanding=True)
    )
    unfitted = {int(row[0]) for row in db.execute(statement, {"ids": ids}).fetchall()}
    changed: set[int] = set()
    for asset_id in ids:
        if asset_id in unfitted:
            if insert_asset_flag(db, asset_id=asset_id, flag_code="PART_NOT_FITTED", subject_code="", import_id=None, at=at):
                changed.add(asset_id)
        elif delete_asset_flag(db, asset_id=asset_id, flag_code="PART_NOT_FITTED"):
            changed.add(asset_id)
    return changed


def delete_part_not_fitted_flags_except(db: Session, *, asset_ids: list[int]) -> list[int]:
    """PART_NOT_FITTED stays only on the assets named: every other asset loses it. Returns the assets that
    lost it."""
    if asset_ids:
        statement = text(
            "DELETE FROM equipment_asset_flag WHERE flag_code = 'PART_NOT_FITTED' AND equipment_asset_id NOT IN :ids "
            "RETURNING equipment_asset_id"
        ).bindparams(bindparam("ids", expanding=True))
        rows = db.execute(statement, {"ids": asset_ids}).fetchall()
    else:
        rows = db.execute(
            text("DELETE FROM equipment_asset_flag WHERE flag_code = 'PART_NOT_FITTED' RETURNING equipment_asset_id")
        ).fetchall()
    return [int(row[0]) for row in rows]


# --- Source bindings -----------------------------------------------------------------------------------


def insert_binding(
    db: Session, *, asset_id: int, provider_key: str, source_values: dict[str, Any], import_id: int
) -> None:
    db.execute(
        text(
            """
            INSERT INTO equipment_source_binding
                (equipment_asset_id, provider_code, provider_key, source_values, reconciliation_status_code,
                 first_import_id, last_import_id)
            VALUES (:asset_id, 'PLUM', :provider_key, CAST(:source_values AS jsonb), 'CONFIRMED', :import_id, :import_id)
            """
        ),
        {"asset_id": asset_id, "provider_key": provider_key, "source_values": _json(source_values), "import_id": import_id},
    )


def update_binding(
    db: Session,
    *,
    asset_id: int,
    reconciliation_status_code: str,
    source_values: dict[str, Any] | None = None,
    import_id: int | None = None,
) -> bool:
    """Record how the latest confirmed report saw the asset. The values and the last import change only
    when the report carried a row the asset was built from. Returns whether what the report says of the
    asset changed - its status or its values; which import said it last is bookkeeping, like the facts'
    report date, and does not count."""
    row = db.execute(
        text(
            """
            WITH before AS (
                SELECT id, reconciliation_status_code, source_values
                FROM equipment_source_binding
                WHERE equipment_asset_id = :asset_id
                FOR UPDATE
            )
            UPDATE equipment_source_binding AS b
            SET reconciliation_status_code = :status,
                source_values = COALESCE(CAST(:source_values AS jsonb), b.source_values),
                last_import_id = COALESCE(:import_id, b.last_import_id)
            FROM before
            WHERE b.id = before.id
            RETURNING (before.reconciliation_status_code IS DISTINCT FROM b.reconciliation_status_code
                       OR before.source_values IS DISTINCT FROM b.source_values) AS changed
            """
        ),
        {
            "asset_id": asset_id,
            "status": reconciliation_status_code,
            "source_values": _json(source_values) if source_values is not None else None,
            "import_id": import_id,
        },
    ).first()
    return bool(row and row[0])


# --- Links ----------------------------------------------------------------------------------------------


def list_open_links_of(db: Session, *, asset_id: int) -> list[dict[str, Any]]:
    return _rows(
        db,
        """
        SELECT l.id, l.link_public_id, l.parent_asset_id, l.child_asset_id, l.fitted_on,
               p.asset_public_id AS parent_public_id, c.asset_public_id AS child_public_id,
               p.asset_kind_code AS parent_kind_code, p.class_code AS parent_class_code,
               c.asset_kind_code AS child_kind_code, c.class_code AS child_class_code
        FROM equipment_asset_link l
        INNER JOIN equipment_asset p ON p.id = l.parent_asset_id
        INNER JOIN equipment_asset c ON c.id = l.child_asset_id
        WHERE (l.parent_asset_id = :asset_id OR l.child_asset_id = :asset_id) AND l.removed_on IS NULL
        ORDER BY l.id
        """,
        {"asset_id": asset_id},
    )


def earliest_fitting_date(db: Session, *, part_id: int, machine_id: int, part_class_code: str) -> date | None:
    """The first day the part can be fitted to the machine without two links overlapping in time: the
    latest day the part was removed from any machine, or the machine lost a part of the same class
    (independent review, round 4, ERT1-R4-004). None when neither has such history."""
    value = db.execute(
        text(
            """
            SELECT MAX(l.removed_on) FROM equipment_asset_link l
            INNER JOIN equipment_asset c ON c.id = l.child_asset_id
            WHERE l.removed_on IS NOT NULL
              AND (l.child_asset_id = :part_id OR (l.parent_asset_id = :machine_id AND c.class_code = :part_class))
            """
        ),
        {"part_id": part_id, "machine_id": machine_id, "part_class": part_class_code},
    ).scalar()
    return value


# Recursion bound for the two walks below: far past any depth setting the version table allows (at most 10).
_WALK_LIMIT = 20


def current_component_depth(db: Session) -> int:
    """The depth setting in force: the current structure version's (ERT-2, owner Q9)."""
    return int(
        db.execute(
            text("SELECT component_depth FROM equipment_taxonomy_version ORDER BY version_number DESC LIMIT 1")
        ).scalar_one()
    )


def asset_level(db: Session, *, asset_id: int) -> int:
    """The asset's level in the tree of fitted parts: 1 for one fitted to nothing, one more for each open
    link above it."""
    return int(
        db.execute(
            text(
                f"""
                WITH RECURSIVE up(asset_id, level) AS (
                    SELECT CAST(:asset_id AS integer), 1
                    UNION ALL
                    SELECT l.parent_asset_id, up.level + 1
                    FROM equipment_asset_link l INNER JOIN up ON l.child_asset_id = up.asset_id
                    WHERE l.removed_on IS NULL AND up.level < {_WALK_LIMIT}
                )
                SELECT MAX(level) FROM up
                """
            ),
            {"asset_id": asset_id},
        ).scalar_one()
    )


def subtree_height(db: Session, *, asset_id: int) -> int:
    """How many levels the asset and the fitted parts below it take: 1 for one carrying nothing."""
    return int(
        db.execute(
            text(
                f"""
                WITH RECURSIVE down(asset_id, height) AS (
                    SELECT CAST(:asset_id AS integer), 1
                    UNION ALL
                    SELECT l.child_asset_id, down.height + 1
                    FROM equipment_asset_link l INNER JOIN down ON l.parent_asset_id = down.asset_id
                    WHERE l.removed_on IS NULL AND down.height < {_WALK_LIMIT}
                )
                SELECT MAX(height) FROM down
                """
            ),
            {"asset_id": asset_id},
        ).scalar_one()
    )


def list_assets_by_create_request_key(db: Session, *, create_request_key: str) -> list[dict[str, Any]]:
    """The records one "add kit" request made, in the order it made them (ADR-023: a repeat has one effect)."""
    return _rows(
        db,
        f"{ASSET_SELECT} WHERE a.create_request_key = :key ORDER BY a.create_request_position",
        {"key": create_request_key},
    )


def get_create_request_fingerprint(db: Session, *, create_request_key: str) -> str | None:
    """The fingerprint of the "add kit" request a key made its lot with: every record of the lot carries it (null for
    a lot made before migration 0050)."""
    row = _first(
        db,
        "SELECT create_request_fingerprint FROM equipment_asset WHERE create_request_key = :key "
        "ORDER BY create_request_position LIMIT 1",
        {"key": create_request_key},
    )
    return row["create_request_fingerprint"] if row else None


def insert_link(
    db: Session,
    *,
    public_id: str,
    parent_asset_id: int,
    child_asset_id: int,
    fitted_on: date,
    user_public_id: str,
    at: datetime,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO equipment_asset_link
                (link_public_id, parent_asset_id, child_asset_id, link_kind_code, fitted_on, fitted_by, fitted_at)
            VALUES (:public_id, :parent_asset_id, :child_asset_id, 'FITTED', :fitted_on, :fitted_by, :fitted_at)
            """
        ),
        {
            "public_id": public_id,
            "parent_asset_id": parent_asset_id,
            "child_asset_id": child_asset_id,
            "fitted_on": fitted_on,
            "fitted_by": user_public_id,
            "fitted_at": at,
        },
    )


def close_link(db: Session, *, link_id: int, removed_on: date, user_public_id: str, at: datetime) -> int:
    result = db.execute(
        text(
            "UPDATE equipment_asset_link SET removed_on = :removed_on, removed_by = :removed_by, removed_at = :removed_at "
            "WHERE id = :link_id AND removed_on IS NULL"
        ),
        {"link_id": link_id, "removed_on": removed_on, "removed_by": user_public_id, "removed_at": at},
    )
    return result.rowcount or 0


# --- Imports ----------------------------------------------------------------------------------------------

IMPORT_SELECT = """
    SELECT i.id, i.import_public_id, i.provider_code, i.fingerprint, i.row_count, i.report_date, i.import_status_code,
           i.based_on_import_id, based.import_public_id AS based_on_import_public_id,
           i.preview_version, i.preview_change_number, i.preview_computed_at,
           i.uploaded_by, uploader.display_name AS uploaded_by_display_name, i.uploaded_at,
           i.published_by, publisher.display_name AS published_by_display_name, i.published_at,
           i.discarded_by, discarder.display_name AS discarded_by_display_name, i.discarded_at, i.discard_reason_code,
           COALESCE(i.preview -> 'counts', '{}'::jsonb) AS counts
    FROM equipment_source_import i
    LEFT JOIN equipment_source_import based ON based.id = i.based_on_import_id
    LEFT JOIN app_user uploader ON uploader.public_id = i.uploaded_by
    LEFT JOIN app_user publisher ON publisher.public_id = i.published_by
    LEFT JOIN app_user discarder ON discarder.public_id = i.discarded_by
"""


def get_import_row(db: Session, *, public_id: str) -> dict[str, Any] | None:
    return _first(db, f"{IMPORT_SELECT} WHERE i.import_public_id = :public_id", {"public_id": public_id})


def get_import_preview(db: Session, *, import_id: int) -> Any:
    return db.execute(text("SELECT preview FROM equipment_source_import WHERE id = :id"), {"id": import_id}).scalar_one()


def lock_import_row(db: Session, *, public_id: str) -> dict[str, Any] | None:
    return _first(
        db,
        "SELECT id, import_public_id, import_status_code, preview_version, preview_change_number, based_on_import_id, "
        "report_date, fingerprint, row_count FROM equipment_source_import WHERE import_public_id = :public_id FOR UPDATE",
        {"public_id": public_id},
    )


def list_import_summary_rows(db: Session, *, limit: int, offset: int) -> list[dict[str, Any]]:
    return _rows(
        db,
        f"{IMPORT_SELECT} ORDER BY i.uploaded_at DESC, i.id DESC LIMIT :limit OFFSET :offset",
        {"limit": limit, "offset": offset},
    )


def latest_published_import(db: Session) -> dict[str, Any] | None:
    return _first(
        db,
        "SELECT id, import_public_id, fingerprint, report_date, published_at FROM equipment_source_import "
        "WHERE import_status_code = 'PUBLISHED' ORDER BY published_at DESC, id DESC LIMIT 1",
        {},
    )


def find_published_import_by_fingerprint(db: Session, *, fingerprint: str) -> dict[str, Any] | None:
    """The first confirmed import of this exact file, whichever reports were confirmed after it."""
    return _first(
        db,
        "SELECT id, import_public_id, published_at FROM equipment_source_import "
        "WHERE fingerprint = :fingerprint AND import_status_code = 'PUBLISHED' ORDER BY published_at, id LIMIT 1",
        {"fingerprint": fingerprint},
    )


def find_previewed_import_by_fingerprint(db: Session, *, fingerprint: str) -> dict[str, Any] | None:
    return _first(
        db,
        "SELECT import_public_id FROM equipment_source_import "
        "WHERE fingerprint = :fingerprint AND import_status_code = 'PREVIEWED' ORDER BY id DESC LIMIT 1",
        {"fingerprint": fingerprint},
    )


def insert_import(db: Session, *, values: dict[str, Any]) -> int:
    values = {**values, "preview": _json(values["preview"])}
    columns = ", ".join(values)
    placeholders = ", ".join("CAST(:preview AS jsonb)" if column == "preview" else f":{column}" for column in values)
    return int(
        db.execute(
            text(f"INSERT INTO equipment_source_import ({columns}) VALUES ({placeholders}) RETURNING id"), values
        ).scalar_one()
    )


def insert_import_row_values(db: Session, *, import_id: int, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    columns = list(rows[0])
    db.execute(
        text(
            f"INSERT INTO equipment_source_import_row (equipment_source_import_id, {', '.join(columns)}) "
            f"VALUES (:import_id, {', '.join(f':{column}' for column in columns)})"
        ),
        [{"import_id": import_id, **row} for row in rows],
    )


def list_import_row_values(db: Session, *, import_id: int) -> list[dict[str, Any]]:
    return _rows(
        db,
        """
        SELECT row_number, machine_number, category, schedule_type, make, model, capacity, load_capacity,
               engine_number, chassis_number, commenced_year, owning_company, status_text, bed_number, value_too_long
        FROM equipment_source_import_row
        WHERE equipment_source_import_id = :import_id
        ORDER BY row_number
        """,
        {"import_id": import_id},
    )


def store_preview(
    db: Session,
    *,
    import_id: int,
    preview: dict[str, Any],
    change_number: int,
    based_on_import_id: int | None,
    at: datetime,
) -> None:
    db.execute(
        text(
            """
            UPDATE equipment_source_import
            SET preview = CAST(:preview AS jsonb), preview_version = preview_version + 1,
                preview_change_number = :change_number, preview_computed_at = :at, based_on_import_id = :based_on
            WHERE id = :import_id AND import_status_code = 'PREVIEWED'
            """
        ),
        {
            "import_id": import_id,
            "preview": _json(preview),
            "change_number": change_number,
            "at": at,
            "based_on": based_on_import_id,
        },
    )


def mark_import_published(
    db: Session, *, import_id: int, preview: dict[str, Any], user_public_id: str | None, at: datetime
) -> int:
    result = db.execute(
        text(
            """
            UPDATE equipment_source_import
            SET import_status_code = 'PUBLISHED', preview = CAST(:preview AS jsonb), published_by = :user,
                published_at = :at
            WHERE id = :import_id AND import_status_code = 'PREVIEWED'
            """
        ),
        {"import_id": import_id, "preview": _json(preview), "user": user_public_id, "at": at},
    )
    return result.rowcount or 0


def discard_imports(
    db: Session, *, import_ids: list[int], reason_code: str, user_public_id: str | None, at: datetime
) -> int:
    if not import_ids:
        return 0
    statement = text(
        """
        UPDATE equipment_source_import
        SET import_status_code = 'DISCARDED', discard_reason_code = :reason, discarded_by = :user, discarded_at = :at
        WHERE id IN :ids AND import_status_code = 'PREVIEWED'
        """
    ).bindparams(bindparam("ids", expanding=True))
    return db.execute(statement, {"ids": import_ids, "reason": reason_code, "user": user_public_id, "at": at}).rowcount or 0


def list_previewed_import_ids(db: Session, *, except_id: int) -> list[int]:
    return [
        int(row[0])
        for row in db.execute(
            text("SELECT id FROM equipment_source_import WHERE import_status_code = 'PREVIEWED' AND id <> :except_id"),
            {"except_id": except_id},
        ).fetchall()
    ]


# The row column a value rule's column reads - the capacity figure falls back on the load capacity, as the
# transformer reads it.
_RULE_COLUMN_SQL = {
    "CAPACITY": "COALESCE(capacity, load_capacity)",
    "COMMENCED_YEAR": "commenced_year",
    "ENGINE_NUMBER": "engine_number",
    "CHASSIS_NUMBER": "chassis_number",
    "OWNING_COMPANY": "owning_company",
}


def count_value_in_import(db: Session, *, import_id: int, column_code: str, plum_value: str) -> int:
    """How many rows of an import carry a value in a rule's column, compared in the normalized form."""
    column = _RULE_COLUMN_SQL[column_code]
    return int(
        db.execute(
            text(
                f"""
                SELECT COUNT(*) FROM equipment_source_import_row
                WHERE equipment_source_import_id = :import_id
                  AND upper(btrim(regexp_replace({column}, '\\s+', ' ', 'g')))
                      = upper(btrim(regexp_replace(:value, '\\s+', ' ', 'g')))
                """
            ),
            {"import_id": import_id, "value": plum_value},
        ).scalar_one()
    )


# --- Value rules and corrections ---------------------------------------------------------------------------

VALUE_RULE_SELECT = """
    SELECT r.id, r.rule_public_id, r.column_code, r.plum_value, r.normalized_value, r.action_code, r.result_number,
           r.result_unit_code, r.result_class_code, r.result_type_code, r.reason, r.rule_status_code,
           r.closed_reason_code, r.closed_by, closer.display_name AS closed_by_display_name, r.closed_at,
           i.import_public_id AS recorded_during_import_public_id,
           r.recorded_by, recorder.display_name AS recorded_by_display_name, r.recorded_at
    FROM equipment_source_value_rule r
    LEFT JOIN equipment_source_import i ON i.id = r.recorded_during_import_id
    LEFT JOIN app_user recorder ON recorder.public_id = r.recorded_by
    LEFT JOIN app_user closer ON closer.public_id = r.closed_by
"""


def list_value_rule_rows(db: Session, *, open_only: bool) -> list[dict[str, Any]]:
    where = "WHERE r.rule_status_code = 'OPEN'" if open_only else ""
    return _rows(
        db,
        f"{VALUE_RULE_SELECT} {where} ORDER BY CASE r.rule_status_code WHEN 'OPEN' THEN 0 ELSE 1 END, "
        "r.column_code, r.normalized_value, r.recorded_at DESC, r.id DESC",
    )


def get_value_rule_row(db: Session, *, public_id: str) -> dict[str, Any] | None:
    return _first(db, f"{VALUE_RULE_SELECT} WHERE r.rule_public_id = :public_id", {"public_id": public_id})


def find_open_value_rule(db: Session, *, column_code: str, plum_value: str) -> dict[str, Any] | None:
    return _first(
        db,
        f"""{VALUE_RULE_SELECT}
        WHERE r.rule_status_code = 'OPEN' AND r.column_code = :column_code
          AND r.normalized_value = upper(btrim(regexp_replace(:plum_value, '\\s+', ' ', 'g')))
        """,
        {"column_code": column_code, "plum_value": plum_value},
    )


def insert_value_rule(db: Session, *, values: dict[str, Any]) -> None:
    columns = ", ".join(values)
    placeholders = ", ".join(f":{column}" for column in values)
    db.execute(text(f"INSERT INTO equipment_source_value_rule ({columns}) VALUES ({placeholders})"), values)


def close_value_rule(db: Session, *, rule_id: int, reason_code: str, user_public_id: str, at: datetime) -> int:
    result = db.execute(
        text(
            """
            UPDATE equipment_source_value_rule
            SET rule_status_code = 'CLOSED', closed_reason_code = :reason, closed_by = :user, closed_at = :at
            WHERE id = :rule_id AND rule_status_code = 'OPEN'
            """
        ),
        {"rule_id": rule_id, "reason": reason_code, "user": user_public_id, "at": at},
    )
    return result.rowcount or 0


def insert_correction(db: Session, *, values: dict[str, Any]) -> None:
    columns = ", ".join(values)
    placeholders = ", ".join(f":{column}" for column in values)
    db.execute(text(f"INSERT INTO equipment_asset_correction ({columns}) VALUES ({placeholders})"), values)


def find_open_correction(db: Session, *, asset_id: int, field_code: str) -> dict[str, Any] | None:
    return _first(
        db,
        "SELECT id, correction_public_id FROM equipment_asset_correction "
        "WHERE equipment_asset_id = :asset_id AND field_code = :field_code AND correction_status_code = 'OPEN'",
        {"asset_id": asset_id, "field_code": field_code},
    )


def get_correction_row(db: Session, *, asset_id: int, public_id: str) -> dict[str, Any] | None:
    return _first(
        db,
        "SELECT id, correction_public_id, field_code, correction_status_code FROM equipment_asset_correction "
        "WHERE equipment_asset_id = :asset_id AND correction_public_id = :public_id",
        {"asset_id": asset_id, "public_id": public_id},
    )


def close_correction(
    db: Session,
    *,
    correction_id: int,
    reason_code: str,
    user_public_id: str | None,
    import_id: int | None,
    at: datetime,
) -> int:
    result = db.execute(
        text(
            """
            UPDATE equipment_asset_correction
            SET correction_status_code = 'CLOSED', closed_reason_code = :reason, closed_by = :user,
                closed_by_import_id = :import_id, closed_at = :at
            WHERE id = :correction_id AND correction_status_code = 'OPEN'
            """
        ),
        {"correction_id": correction_id, "reason": reason_code, "user": user_public_id, "import_id": import_id, "at": at},
    )
    return result.rowcount or 0


def list_open_corrections_to_send(db: Session) -> list[dict[str, Any]]:
    return _rows(
        db,
        """
        SELECT c.correction_public_id, c.field_code, c.plum_value, c.corrected_value, c.reason, c.recorded_at,
               recorder.display_name AS recorded_by_display_name,
               a.asset_public_id, a.asset_reference, a.machine_number,
               EXISTS (
                   SELECT 1 FROM equipment_asset_flag f
                   WHERE f.equipment_asset_id = a.id AND f.flag_code = 'PLUM_CHANGED_CORRECTED_VALUE'
                     AND f.subject_code = c.field_code
               ) AS plum_changed
        FROM equipment_asset_correction c
        INNER JOIN equipment_asset a ON a.id = c.equipment_asset_id
        LEFT JOIN app_user recorder ON recorder.public_id = c.recorded_by
        WHERE c.correction_status_code = 'OPEN'
        ORDER BY a.machine_number, c.field_code
        """,
    )
