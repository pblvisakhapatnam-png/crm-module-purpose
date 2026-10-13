"""Eligibility database access. Its own tables only (ELG-1).

Jurisdictions and certificate kinds change only by migration. Certificates, "not applicable" marks, rules and
decisions are written below, each through the service that holds the module's write lock. Nothing is ever
updated but a withdrawal or a rule's end.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

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


# One lock for every write in this module. Certificates and rules are recorded by one or two people, so
# serializing them costs nothing, and a mark is checked against the rules in force without a race.
_WRITE_LOCK_KEY = "eligibility.write"


def take_write_lock(db: Session) -> None:
    take_advisory_lock(db, _WRITE_LOCK_KEY)


# --- Jurisdictions and kinds ----------------------------------------------------------------------------


def list_jurisdiction_rows(db: Session) -> list[dict[str, Any]]:
    return _rows(
        db,
        "SELECT jurisdiction_code, jurisdiction_label, jurisdiction_kind_code, gst_state_code, display_order "
        "FROM eligibility_jurisdiction ORDER BY display_order, jurisdiction_code",
    )


def list_kind_rows(db: Session) -> list[dict[str, Any]]:
    return _rows(
        db,
        "SELECT kind_code, kind_label, end_date_optional, valid_in_required, is_examination, states_registration, display_order "
        "FROM eligibility_certificate_kind ORDER BY display_order, kind_code",
    )


# --- Rules ------------------------------------------------------------------------------------------------

RULE_SELECT = """
    SELECT r.id, r.rule_public_id, r.kind_code, r.class_code, r.type_code, r.applies_when_code, r.jurisdiction_code,
           r.effective_from, r.effective_to, r.renew_every_months, r.basis_code, r.lapse_code, r.not_applicable_code,
           r.not_applicable_max_months, r.source, r.note, r.create_request_key, r.recorded_by,
           recorder.display_name AS recorded_by_display_name, r.recorded_at, r.ended_by,
           ender.display_name AS ended_by_display_name, r.ended_at, r.end_reason
    FROM eligibility_rule r
    INNER JOIN eligibility_certificate_kind k ON k.kind_code = r.kind_code
    INNER JOIN equipment_class c ON c.class_code = r.class_code
    LEFT JOIN app_user recorder ON recorder.public_id = r.recorded_by
    LEFT JOIN app_user ender ON ender.public_id = r.ended_by
"""


def list_rule_rows(db: Session) -> list[dict[str, Any]]:
    # Where, then the kinds in their own order, then the classes in the structure's.
    return _rows(
        db,
        f"{RULE_SELECT} ORDER BY r.jurisdiction_code NULLS FIRST, k.display_order, c.display_order, r.type_code NULLS FIRST, r.effective_from, r.id",
    )


def get_rule_row(db: Session, *, public_id: str) -> dict[str, Any] | None:
    return _first(db, f"{RULE_SELECT} WHERE r.rule_public_id = :public_id", {"public_id": public_id})


def find_rule_by_create_request_key(db: Session, *, create_request_key: str) -> dict[str, Any] | None:
    return _first(db, f"{RULE_SELECT} WHERE r.create_request_key = :key", {"key": create_request_key})


def insert_rule(db: Session, *, values: dict[str, Any]) -> int:
    columns = ", ".join(values)
    placeholders = ", ".join(f":{name}" for name in values)
    return int(db.execute(text(f"INSERT INTO eligibility_rule ({columns}) VALUES ({placeholders}) RETURNING id"), values).scalar_one())


def end_rule(db: Session, *, rule_id: int, effective_to: date, reason: str, user_public_id: str, at: datetime) -> int:
    return db.execute(
        text(
            "UPDATE eligibility_rule SET effective_to = :effective_to, end_reason = :reason, ended_by = :user, ended_at = :at "
            "WHERE id = :rule_id AND effective_to IS NULL"
        ),
        {"effective_to": effective_to, "reason": reason, "user": user_public_id, "at": at, "rule_id": rule_id},
    ).rowcount


# --- Certificates -----------------------------------------------------------------------------------------

CERTIFICATE_SELECT = """
    SELECT c.id, c.certificate_public_id, c.equipment_asset_public_id, c.kind_code, c.certificate_number, c.issued_by,
           c.issued_on, c.valid_from, c.valid_until, c.valid_in_code, c.registered_as_code, c.certificate_status_code,
           c.create_request_key, c.recorded_by, recorder.display_name AS recorded_by_display_name, c.recorded_at,
           c.withdrawn_reason, c.withdrawn_by, withdrawer.display_name AS withdrawn_by_display_name, c.withdrawn_at
    FROM eligibility_certificate c
    LEFT JOIN app_user recorder ON recorder.public_id = c.recorded_by
    LEFT JOIN app_user withdrawer ON withdrawer.public_id = c.withdrawn_by
"""


def list_certificate_rows(db: Session, *, asset_public_ids: list[str] | None = None) -> list[dict[str, Any]]:
    if asset_public_ids is None:
        return _rows(db, f"{CERTIFICATE_SELECT} ORDER BY c.id")
    return _rows_in(db, f"{CERTIFICATE_SELECT} WHERE c.equipment_asset_public_id IN :ids ORDER BY c.id", asset_public_ids)


def get_certificate_row(db: Session, *, public_id: str) -> dict[str, Any] | None:
    return _first(db, f"{CERTIFICATE_SELECT} WHERE c.certificate_public_id = :public_id", {"public_id": public_id})


def lock_certificate_row(db: Session, *, public_id: str) -> dict[str, Any] | None:
    return _first(
        db,
        "SELECT id, certificate_public_id, equipment_asset_public_id, kind_code, certificate_status_code "
        "FROM eligibility_certificate WHERE certificate_public_id = :public_id FOR UPDATE",
        {"public_id": public_id},
    )


def find_certificate_by_create_request_key(db: Session, *, create_request_key: str) -> dict[str, Any] | None:
    return _first(db, f"{CERTIFICATE_SELECT} WHERE c.create_request_key = :key", {"key": create_request_key})


def insert_certificate(db: Session, *, values: dict[str, Any]) -> int:
    columns = ", ".join(values)
    placeholders = ", ".join(f":{name}" for name in values)
    return int(
        db.execute(text(f"INSERT INTO eligibility_certificate ({columns}) VALUES ({placeholders}) RETURNING id"), values).scalar_one()
    )


def withdraw_certificate(db: Session, *, certificate_id: int, reason: str, user_public_id: str, at: datetime) -> int:
    return db.execute(
        text(
            "UPDATE eligibility_certificate SET certificate_status_code = 'WITHDRAWN', withdrawn_reason = :reason, "
            "withdrawn_by = :user, withdrawn_at = :at WHERE id = :certificate_id AND certificate_status_code = 'RECORDED'"
        ),
        {"reason": reason, "user": user_public_id, "at": at, "certificate_id": certificate_id},
    ).rowcount


# --- "Not applicable" marks -------------------------------------------------------------------------------

MARK_SELECT = """
    SELECT m.id, m.mark_public_id, m.equipment_asset_public_id, m.kind_code, m.allowed_by_rule_id,
           r.rule_public_id AS allowed_by_rule_public_id, m.reason, m.until_date, m.recorded_on, m.mark_status_code,
           m.create_request_key, m.recorded_by, recorder.display_name AS recorded_by_display_name, m.recorded_at,
           m.withdrawn_reason, m.withdrawn_by, withdrawer.display_name AS withdrawn_by_display_name, m.withdrawn_at
    FROM eligibility_not_applicable m
    INNER JOIN eligibility_rule r ON r.id = m.allowed_by_rule_id
    LEFT JOIN app_user recorder ON recorder.public_id = m.recorded_by
    LEFT JOIN app_user withdrawer ON withdrawer.public_id = m.withdrawn_by
"""


def list_mark_rows(db: Session, *, asset_public_ids: list[str] | None = None) -> list[dict[str, Any]]:
    if asset_public_ids is None:
        return _rows(db, f"{MARK_SELECT} ORDER BY m.id")
    return _rows_in(db, f"{MARK_SELECT} WHERE m.equipment_asset_public_id IN :ids ORDER BY m.id", asset_public_ids)


def get_mark_row(db: Session, *, public_id: str) -> dict[str, Any] | None:
    return _first(db, f"{MARK_SELECT} WHERE m.mark_public_id = :public_id", {"public_id": public_id})


def lock_mark_row(db: Session, *, public_id: str) -> dict[str, Any] | None:
    return _first(
        db,
        "SELECT id, mark_public_id, equipment_asset_public_id, kind_code, mark_status_code "
        "FROM eligibility_not_applicable WHERE mark_public_id = :public_id FOR UPDATE",
        {"public_id": public_id},
    )


def find_mark_by_create_request_key(db: Session, *, create_request_key: str) -> dict[str, Any] | None:
    return _first(db, f"{MARK_SELECT} WHERE m.create_request_key = :key", {"key": create_request_key})


def find_mark_in_force(db: Session, *, asset_public_id: str, kind_code: str) -> dict[str, Any] | None:
    return _first(
        db,
        f"{MARK_SELECT} WHERE m.equipment_asset_public_id = :asset AND m.kind_code = :kind AND m.mark_status_code = 'IN_FORCE'",
        {"asset": asset_public_id, "kind": kind_code},
    )


def insert_mark(db: Session, *, values: dict[str, Any]) -> int:
    columns = ", ".join(values)
    placeholders = ", ".join(f":{name}" for name in values)
    return int(
        db.execute(text(f"INSERT INTO eligibility_not_applicable ({columns}) VALUES ({placeholders}) RETURNING id"), values).scalar_one()
    )


def withdraw_mark(db: Session, *, mark_id: int, reason: str, user_public_id: str, at: datetime) -> int:
    return db.execute(
        text(
            "UPDATE eligibility_not_applicable SET mark_status_code = 'WITHDRAWN', withdrawn_reason = :reason, "
            "withdrawn_by = :user, withdrawn_at = :at WHERE id = :mark_id AND mark_status_code = 'IN_FORCE'"
        ),
        {"reason": reason, "user": user_public_id, "at": at, "mark_id": mark_id},
    ).rowcount


# --- Decisions --------------------------------------------------------------------------------------------


def insert_decision(db: Session, *, values: dict[str, Any]) -> int:
    columns = ", ".join(values)
    placeholders = ", ".join(f":{name}" for name in values)
    return int(
        db.execute(text(f"INSERT INTO eligibility_decision ({columns}) VALUES ({placeholders}) RETURNING id"), values).scalar_one()
    )


def insert_decision_results(db: Session, *, decision_id: int, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    db.execute(
        text(
            """
            INSERT INTO eligibility_decision_result (
                decision_id, result_number, equipment_asset_public_id, kind_code, rule_id, rule_jurisdiction_code,
                certificate_id, mark_id, outcome_code, lapse_code, effect_code, cover_ends_on
            ) VALUES (
                :decision_id, :result_number, :equipment_asset_public_id, :kind_code, :rule_id, :rule_jurisdiction_code,
                :certificate_id, :mark_id, :outcome_code, :lapse_code, :effect_code, :cover_ends_on
            )
            """
        ),
        [{"decision_id": decision_id, **row} for row in rows],
    )


def list_decision_rows(db: Session, *, public_ids: list[str]) -> list[dict[str, Any]]:
    return _rows_in(db, "SELECT * FROM eligibility_decision WHERE decision_public_id IN :ids ORDER BY id", public_ids)


def list_result_rows_of_decisions(db: Session, *, decision_ids: list[int]) -> list[dict[str, Any]]:
    return _rows_in(
        db, "SELECT * FROM eligibility_decision_result WHERE decision_id IN :ids ORDER BY decision_id, result_number", decision_ids
    )


# --- Reminder settings and "seen" marks (ELG-2) ------------------------------------------------------------

SETTING_SELECT = """
    SELECT s.id, s.setting_public_id, s.reminder_kind_code, s.version_number, s.saved_by,
           saver.display_name AS saved_by_display_name, s.saved_at
    FROM eligibility_alert_setting s
    LEFT JOIN app_user saver ON saver.public_id = s.saved_by
"""


def list_setting_rows(db: Session) -> list[dict[str, Any]]:
    """Every version of every kind of reminder's setting, newest first within a kind."""
    return _rows(db, f"{SETTING_SELECT} ORDER BY s.reminder_kind_code, s.version_number DESC")


def first_setting_saved_at(db: Session, *, reminder_kind_code: str) -> datetime | None:
    """When a kind of reminder's first setting was saved: for the standard ones, when the package loaded them."""
    return db.execute(
        text("SELECT MIN(saved_at) FROM eligibility_alert_setting WHERE reminder_kind_code = :kind"), {"kind": reminder_kind_code}
    ).scalar()


def list_band_rows(db: Session, *, setting_ids: list[int]) -> list[dict[str, Any]]:
    return _rows_in(
        db,
        "SELECT setting_id, band_number, from_days_before, every_days FROM eligibility_alert_band "
        "WHERE setting_id IN :ids ORDER BY setting_id, band_number",
        setting_ids,
    )


def list_step_rows(db: Session, *, setting_ids: list[int]) -> list[dict[str, Any]]:
    return _rows_in(
        db,
        "SELECT setting_id, step_number, role_code, starts_code, from_days_before, channel_codes FROM eligibility_alert_step "
        "WHERE setting_id IN :ids ORDER BY setting_id, step_number",
        setting_ids,
    )


def insert_setting(
    db: Session, *, setting_public_id: str, reminder_kind_code: str, version_number: int, saved_by: str, saved_at: datetime
) -> int:
    return int(
        db.execute(
            text(
                "INSERT INTO eligibility_alert_setting (setting_public_id, reminder_kind_code, version_number, saved_by, saved_at) "
                "VALUES (:public_id, :kind, :version, :saved_by, :saved_at) RETURNING id"
            ),
            {"public_id": setting_public_id, "kind": reminder_kind_code, "version": version_number, "saved_by": saved_by, "saved_at": saved_at},
        ).scalar_one()
    )


def insert_bands(db: Session, *, setting_id: int, bands: list[tuple[int, int]]) -> None:
    db.execute(
        text(
            "INSERT INTO eligibility_alert_band (setting_id, band_number, from_days_before, every_days) "
            "VALUES (:setting_id, :band_number, :from_days_before, :every_days)"
        ),
        [
            {"setting_id": setting_id, "band_number": number, "from_days_before": start, "every_days": every}
            for number, (start, every) in enumerate(bands, 1)
        ],
    )


def insert_steps(db: Session, *, setting_id: int, steps: list[tuple[str, str, int | None, list[str]]]) -> None:
    db.execute(
        text(
            "INSERT INTO eligibility_alert_step (setting_id, step_number, role_code, starts_code, from_days_before, channel_codes) "
            "VALUES (:setting_id, :step_number, :role_code, :starts_code, :from_days_before, CAST(:channel_codes AS varchar[]))"
        ),
        [
            {
                "setting_id": setting_id,
                "step_number": number,
                "role_code": role_code,
                "starts_code": starts_code,
                "from_days_before": from_days_before,
                "channel_codes": channel_codes,
            }
            for number, (role_code, starts_code, from_days_before, channel_codes) in enumerate(steps, 1)
        ],
    )


def insert_acknowledgements(db: Session, *, rows: list[dict[str, Any]]) -> int:
    """One person's "seen" of each reminder on its reminder day. A mark already made changes nothing."""
    marked = 0
    for row in rows:
        marked += db.execute(
            text(
                """
                INSERT INTO eligibility_alert_acknowledgement (
                    reminder_key, reminder_kind_code, equipment_asset_public_id, subject_type, subject_public_id, kind_code,
                    reminder_date_on, reminder_on, seen_by, seen_at
                ) VALUES (
                    :reminder_key, :reminder_kind_code, :equipment_asset_public_id, :subject_type, :subject_public_id,
                    :kind_code, :reminder_date_on, :reminder_on, :seen_by, :seen_at
                )
                ON CONFLICT ON CONSTRAINT uq_eligibility_alert_acknowledgement DO NOTHING
                """
            ),
            row,
        ).rowcount
    return marked


def list_acknowledgement_rows(db: Session, *, reminder_keys: list[str]) -> list[dict[str, Any]]:
    return _rows_in(
        db,
        "SELECT a.reminder_key, a.reminder_on, a.seen_by, seer.display_name AS seen_by_display_name, a.seen_at "
        "FROM eligibility_alert_acknowledgement a LEFT JOIN app_user seer ON seer.public_id = a.seen_by "
        "WHERE a.reminder_key IN :ids ORDER BY a.seen_at, a.id",
        reminder_keys,
    )
