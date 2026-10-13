"""How Plum's values are read: the Fleet Admin's value rules, the list of corrections to send to Plum, and
what Plum's capacity figure means in each category (ERT-1 design, sections 5B and 6).

Engine and chassis numbers are confidential (owner, 25 September 2026): a rule or correction of those
fields shows its values only to a holder of EQUIPMENT_IDENTITY_READ; others see that it exists.

A value rule reads one value wherever it appears in a column - "230 KG" in the capacity column is 230
kilograms; "PULLER" names a ballast tractor, not a figure; "select" means nothing was entered. It takes
effect on the next preview, and stays open until the Fleet Admin closes it: an export may be partial, so a
report that happens not to carry the value does not close it. The list to send to Plum says, for each open
rule, how many rows of the latest confirmed report still carry the value.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.modules.equipment_reference import repository as repo
from app.modules.equipment_reference.contract import (
    CAPACITY_ONLY_ACTIONS,
    CLASS_KIND_MACHINE,
    CLOSED_BY_FLEET_ADMIN,
    CLOSED_SUPERSEDED,
    EQUIPMENT_EVENT_VALUE_RULE_CLOSED,
    EQUIPMENT_EVENT_VALUE_RULE_RECORDED,
    EQUIPMENT_UNITS_BY_CODE,
    IDENTITY_FIELDS,
    RECORD_TYPE_VALUE_RULE,
    STATUS_OPEN,
    VALUE_RULE_ACTIONS,
    VALUE_RULE_COLUMNS,
    VALUE_RULE_REASSIGN_TO_TYPE,
    VALUE_RULE_SPLIT_NUMBER_AND_UNIT,
)
from app.modules.equipment_reference.schemas import (
    CategoryRuleResponse,
    CorrectionToSendResponse,
    CorrectionsToSendResponse,
    ValueRuleActionResponse,
    ValueRuleInput,
    ValueRuleResponse,
)
from app.modules.equipment_reference.service import find_class, find_class_capability, find_type, get_equipment_structure
from app.modules.equipment_reference.services.common import (
    EquipmentNotFoundError,
    EquipmentValidationError,
    begin_write,
    clean,
    code,
    correction_values,
    load_models,
    now,
    record_event,
    required_reason,
    require_user,
)
from app.shared.transactions import rollback_on_error


def _rule_response(
    row: dict[str, Any], *, latest_import_id: int | None, db: Session, show_identity: bool
) -> ValueRuleResponse:
    # A value in the engine or chassis number column is withheld without EQUIPMENT_IDENTITY_READ, and so is
    # the reason, which may repeat it (ERT1-R2-002).
    withheld = row["column_code"] in IDENTITY_FIELDS and not show_identity
    in_latest = None
    if latest_import_id is not None and row["rule_status_code"] == STATUS_OPEN:
        in_latest = repo.count_value_in_import(
            db, import_id=latest_import_id, column_code=row["column_code"], plum_value=row["plum_value"]
        )
    return ValueRuleResponse(
        rule_public_id=row["rule_public_id"],
        column_code=row["column_code"],
        plum_value=None if withheld else row["plum_value"],
        value_withheld=withheld,
        action_code=row["action_code"],
        result_number=row["result_number"],
        result_unit_code=row["result_unit_code"],
        result_class_code=row["result_class_code"],
        result_type_code=row["result_type_code"],
        reason=None if withheld else row["reason"],
        rule_status_code=row["rule_status_code"],
        closed_reason_code=row["closed_reason_code"],
        closed_by_display_name=row["closed_by_display_name"],
        closed_at=row["closed_at"],
        recorded_during_import_public_id=row["recorded_during_import_public_id"],
        recorded_by_display_name=row["recorded_by_display_name"],
        recorded_at=row["recorded_at"],
        rows_in_latest_report=in_latest,
    )


def _latest_import_id(db: Session) -> int | None:
    latest = repo.latest_published_import(db)
    return int(latest["id"]) if latest else None


def list_value_rules(db: Session, *, open_only: bool = False, show_identity: bool = False) -> list[ValueRuleResponse]:
    latest = _latest_import_id(db)
    return [
        _rule_response(row, latest_import_id=latest, db=db, show_identity=show_identity)
        for row in repo.list_value_rule_rows(db, open_only=open_only)
    ]


def _get_rule(db: Session, public_id: str, *, show_identity: bool) -> ValueRuleResponse:
    row = repo.get_value_rule_row(db, public_id=public_id)
    if row is None:
        raise EquipmentNotFoundError("Value rule not found.")
    return _rule_response(row, latest_import_id=_latest_import_id(db), db=db, show_identity=show_identity)


def _normalize_rule(payload: ValueRuleInput) -> dict[str, Any]:
    column = code(payload.column_code)
    if column not in VALUE_RULE_COLUMNS:
        raise EquipmentValidationError("A value rule reads the capacity, commenced year, engine or chassis number, or owner.")
    action = code(payload.action_code)
    if action not in VALUE_RULE_ACTIONS:
        raise EquipmentValidationError("Say how the value is read: a number and its unit, a type, or not a value.")
    if action in CAPACITY_ONLY_ACTIONS and column != "CAPACITY":
        raise EquipmentValidationError("Only the capacity figure can be split into a number and unit, or read as a type.")
    plum_value = clean(payload.plum_value)
    if plum_value is None:
        raise EquipmentValidationError("Give the value as Plum records it.")
    # One space for every run of whitespace, so the database's uniqueness and the transformer's matching
    # compare the same form.
    plum_value = " ".join(plum_value.split())
    values: dict[str, Any] = {
        "column_code": column,
        "plum_value": plum_value,
        "action_code": action,
        "result_number": None,
        "result_unit_code": None,
        "result_class_code": None,
        "result_type_code": None,
    }
    if action == VALUE_RULE_SPLIT_NUMBER_AND_UNIT:
        unit = code(payload.result_unit_code)
        if payload.result_number is None or unit not in EQUIPMENT_UNITS_BY_CODE:
            raise EquipmentValidationError("Give the number the value holds and its unit.")
        if payload.result_class_code is not None or payload.result_type_code is not None:
            raise EquipmentValidationError("A number and unit names no type.")
        values["result_number"], values["result_unit_code"] = payload.result_number, unit
    elif action == VALUE_RULE_REASSIGN_TO_TYPE:
        if payload.result_number is not None or payload.result_unit_code is not None:
            raise EquipmentValidationError("A value read as a type holds no number.")
        values["result_class_code"], values["result_type_code"] = code(payload.result_class_code), code(payload.result_type_code)
    elif any(item is not None for item in (payload.result_number, payload.result_unit_code, payload.result_class_code, payload.result_type_code)):
        raise EquipmentValidationError("A value that means nothing was entered is read as nothing: give no number, unit or type.")
    return values


def _check_type(db: Session, values: dict[str, Any]) -> None:
    if values["action_code"] != VALUE_RULE_REASSIGN_TO_TYPE:
        return
    structure = get_equipment_structure(db)
    equipment_class = find_class(structure, values["result_class_code"])
    if equipment_class is None or equipment_class.class_kind_code != CLASS_KIND_MACHINE or not equipment_class.is_active:
        raise EquipmentValidationError("Choose the class of machine the value names.")
    equipment_type = find_type(equipment_class, values["result_type_code"])
    if equipment_type is None or not equipment_type.is_active:
        raise EquipmentValidationError(f"Choose a type of {equipment_class.class_label} the value names.")


def _event_payload(rule: ValueRuleResponse, superseded: str | None = None) -> dict[str, Any]:
    return {
        "rule_public_id": str(rule.rule_public_id),
        "column_code": rule.column_code,
        "action_code": rule.action_code,
        "result_unit_code": rule.result_unit_code,
        "result_class_code": rule.result_class_code,
        "result_type_code": rule.result_type_code,
        "rule_status_code": rule.rule_status_code,
        "closed_reason_code": rule.closed_reason_code,
        "superseded_rule_public_id": superseded,
        "recorded_during_import_public_id": (
            str(rule.recorded_during_import_public_id) if rule.recorded_during_import_public_id else None
        ),
    }


def record_value_rule(
    db: Session, *, payload: ValueRuleInput, user_public_id: str | None, show_identity: bool = False
) -> ValueRuleActionResponse:
    """Record how a Plum value is read. A rule for the same value in the same column replaces the open one;
    the same rule again records nothing."""
    actor = require_user(user_public_id)
    values = _normalize_rule(payload)
    reason = required_reason(payload.reason, what="reading the value this way")
    with rollback_on_error(db):
        begin_write(db)
        _check_type(db, values)
        import_id = None
        if payload.import_public_id is not None:
            found = repo.get_import_row(db, public_id=str(payload.import_public_id))
            if found is None:
                raise EquipmentNotFoundError("Import not found.")
            import_id = int(found["id"])
        existing = repo.find_open_value_rule(db, column_code=values["column_code"], plum_value=values["plum_value"])
        if existing is not None and all(existing[key] == values[key] for key in values if key != "plum_value") and existing["reason"] == reason:
            db.rollback()
            return ValueRuleActionResponse(rule=_get_rule(db, str(existing["rule_public_id"]), show_identity=show_identity), event=None)
        at = now()
        if existing is not None:
            repo.close_value_rule(db, rule_id=int(existing["id"]), reason_code=CLOSED_SUPERSEDED, user_public_id=actor, at=at)
        public_id = str(uuid4())
        repo.insert_value_rule(
            db,
            values={
                **values,
                "rule_public_id": public_id,
                "reason": reason,
                "rule_status_code": STATUS_OPEN,
                "recorded_during_import_id": import_id,
                "recorded_by": actor,
                "recorded_at": at,
            },
        )
        repo.bump_change_number(db)
        rule = _get_rule(db, public_id, show_identity=show_identity)
        event = record_event(
            db,
            event_name=EQUIPMENT_EVENT_VALUE_RULE_RECORDED,
            record_type=RECORD_TYPE_VALUE_RULE,
            record_public_id=public_id,
            user_public_id=actor,
            payload=_event_payload(rule, str(existing["rule_public_id"]) if existing else None),
            reason="How a Plum value is read recorded.",
            status_after=STATUS_OPEN,
        )
        db.commit()
    return ValueRuleActionResponse(rule=rule, event=event)


def close_value_rule(
    db: Session, *, public_id: UUID, user_public_id: str | None, show_identity: bool = False
) -> ValueRuleActionResponse:
    actor = require_user(user_public_id)
    with rollback_on_error(db):
        begin_write(db)
        row = repo.get_value_rule_row(db, public_id=str(public_id))
        if row is None:
            raise EquipmentNotFoundError("Value rule not found.")
        if row["rule_status_code"] != STATUS_OPEN:
            raise EquipmentValidationError("This rule is already closed.")
        repo.close_value_rule(db, rule_id=int(row["id"]), reason_code=CLOSED_BY_FLEET_ADMIN, user_public_id=actor, at=now())
        repo.bump_change_number(db)
        rule = _get_rule(db, str(public_id), show_identity=show_identity)
        event = record_event(
            db,
            event_name=EQUIPMENT_EVENT_VALUE_RULE_CLOSED,
            record_type=RECORD_TYPE_VALUE_RULE,
            record_public_id=str(public_id),
            user_public_id=actor,
            payload=_event_payload(rule),
            reason="Value rule closed by the Fleet Admin.",
            status_before=STATUS_OPEN,
            status_after=rule.rule_status_code,
        )
        db.commit()
    return ValueRuleActionResponse(rule=rule, event=event)


def corrections_to_send(db: Session, *, show_identity: bool = False) -> CorrectionsToSendResponse:
    """Every open value rule and machine correction: what to ask Plum to fix at source (ADR-037, route A).
    Always current: a correction Plum agrees with closes itself on the next confirmed report."""
    structure = get_equipment_structure(db)
    models = load_models(db)
    return CorrectionsToSendResponse(
        value_rules=list_value_rules(db, open_only=True, show_identity=show_identity),
        corrections=[
            CorrectionToSendResponse(
                correction_public_id=row["correction_public_id"],
                asset_public_id=row["asset_public_id"],
                asset_reference=row["asset_reference"],
                machine_number=row["machine_number"],
                field_code=row["field_code"],
                **correction_values(row, structure, models, show_identity=show_identity),
                recorded_by_display_name=row["recorded_by_display_name"],
                recorded_at=row["recorded_at"],
                plum_changed=bool(row["plum_changed"]),
            )
            for row in repo.list_open_corrections_to_send(db)
        ],
    )


def list_category_rules(db: Session) -> list[CategoryRuleResponse]:
    """What Plum's capacity figure is taken to mean in each category, for the check (design section 6)."""
    structure = get_equipment_structure(db)
    responses: list[CategoryRuleResponse] = []
    for row in repo.list_category_rule_rows(db):
        equipment_class = find_class(structure, row["class_code"])
        capability = find_class_capability(equipment_class, row["capability_code"]) if equipment_class and row["capability_code"] else None
        responses.append(
            CategoryRuleResponse(
                category=row["category_term"],
                class_code=row["class_code"],
                class_label=equipment_class.class_label if equipment_class else row["class_code"],
                check_code=row["check_code"],
                capability_code=row["capability_code"],
                capability_label=capability.capability_label if capability else None,
                plum_unit_code=row["plum_unit_code"],
                plausible_low=row["plausible_low"],
                plausible_high=row["plausible_high"],
            )
        )
    return responses
