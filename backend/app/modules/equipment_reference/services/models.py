"""Models - makers' models with their rated capabilities - and the mapping of Plum's model names to them
(ERT-1 design, Q4 and section 4). Both are the Fleet Admin's.

A machine's capabilities are read from its model when they are asked for, never copied onto the machine,
so correcting a model's rating corrects every machine of it. A model's class cannot change while machines
use it; a retired model keeps its machines and mappings but cannot be newly mapped.

A kit model (ERT-2) is a model of a kind of kit. It names the crane models it fits, one or more (owner,
Q12), and its pieces are held for every machine of them. It is the platform's, never Plum's: no Plum model
name is mapped to one. A machine model that kit fits cannot change class while the fit stands.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.equipment_reference import repository as repo
from app.modules.equipment_reference.contract import (
    EQUIPMENT_EVENT_ASSET_CHANGED,
    EQUIPMENT_EVENT_MODEL_CHANGED,
    EQUIPMENT_EVENT_MODEL_MAPPED,
    EQUIPMENT_EVENT_MODEL_RECORDED,
    PROVIDER_PLUM,
    RECORD_TYPE_ASSET,
    RECORD_TYPE_MODEL,
    RECORD_TYPE_MODEL_MAPPING,
    model_mapping_public_id,
)
from app.modules.equipment_reference.schemas import (
    EquipmentModelActionResponse,
    EquipmentModelCreate,
    EquipmentModelFields,
    EquipmentModelResponse,
    EquipmentModelUpdate,
    EquipmentStructureResponse,
    ModelMappingActionResponse,
    ModelMappingInput,
    ModelReference,
)
from app.modules.equipment_reference.service import find_class, find_type, get_equipment_structure, is_kit_class
from app.modules.equipment_reference.services.common import (
    CapabilityValue,
    EquipmentConflictError,
    EquipmentNotFoundError,
    EquipmentValidationError,
    begin_write,
    bump_versions,
    capability_responses,
    clean,
    code,
    normalize_capability_values,
    now,
    record_event,
    rederive_asset,
)
from app.shared.request_keys import is_same_request, request_fingerprint
from app.shared.transactions import rollback_on_error


def _model_responses(db: Session, rows: list[dict[str, Any]], structure: EquipmentStructureResponse) -> list[EquipmentModelResponse]:
    capabilities: dict[int, dict[str, tuple[Any, Any]]] = {}
    for row in repo.list_model_capability_rows(db, model_ids=[int(row["id"]) for row in rows]):
        capabilities.setdefault(int(row["equipment_model_id"]), {})[row["capability_code"]] = (
            row["capability_value"],
            row["choice_value"],
        )
    names: dict[int, list[str]] = {}
    for row in repo.list_model_mapping_rows(db):
        names.setdefault(int(row["model_id"]), []).append(row["source_name"])
    # A kit model's crane models, each with whether any active machine of it is left.
    fits: dict[int, list[dict[str, Any]]] = {}
    for row in repo.list_model_fit_rows(db, model_ids=[int(row["id"]) for row in rows]):
        fits.setdefault(int(row["kit_model_id"]), []).append(row)
    responses: list[EquipmentModelResponse] = []
    for row in rows:
        equipment_class = find_class(structure, row["class_code"])
        equipment_type = find_type(equipment_class, row["type_code"]) if equipment_class and row["type_code"] else None
        kit = is_kit_class(equipment_class)
        model_fits = fits.get(int(row["id"]), [])
        responses.append(
            EquipmentModelResponse(
                model_public_id=row["model_public_id"],
                maker=row["maker"],
                model_name=row["model_name"],
                label=f"{row['maker']} {row['model_name']}",
                class_code=row["class_code"],
                class_label=equipment_class.class_label if equipment_class else row["class_code"],
                class_kind_code=equipment_class.class_kind_code if equipment_class else "MACHINE",
                type_code=row["type_code"],
                type_label=equipment_type.type_label if equipment_type else None,
                maker_part_number=row["maker_part_number"],
                capabilities=capability_responses(capabilities.get(int(row["id"]), {}), equipment_class),
                mapped_names=sorted(names.get(int(row["id"]), [])),
                machine_count=int(row["asset_count"]),
                is_kit=kit,
                fits_models=[
                    ModelReference(model_public_id=item["crane_model_public_id"], label=item["crane_model_label"])
                    for item in model_fits
                ],
                pieces_held=int(row["pieces_held"]),
                fits_no_active_crane=kit and bool(model_fits) and all(int(item["crane_active_unit_count"]) == 0 for item in model_fits),
                active_unit_count=int(row["active_unit_count"]),
                model_version=int(row["model_version"]),
                is_retired=bool(row["is_retired"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        )
    return responses


def list_models(db: Session) -> list[EquipmentModelResponse]:
    return _model_responses(db, repo.list_model_rows(db), get_equipment_structure(db))


def get_model(db: Session, public_id: UUID | str, *, structure: EquipmentStructureResponse | None = None) -> EquipmentModelResponse:
    row = repo.get_model_row(db, public_id=str(public_id))
    if row is None:
        raise EquipmentNotFoundError("Model not found.")
    return _model_responses(db, [row], structure or get_equipment_structure(db))[0]


def _normalize_model(
    payload: EquipmentModelFields,
    structure: EquipmentStructureResponse,
    *,
    current: EquipmentModelResponse | None = None,
) -> tuple[dict[str, Any], list[CapabilityValue]]:
    maker, model_name = clean(payload.maker), clean(payload.model_name)
    if maker is None or model_name is None:
        raise EquipmentValidationError("Give the model's maker and its name.")
    class_code = code(payload.class_code) or ""
    equipment_class = find_class(structure, class_code)
    if equipment_class is None:
        raise EquipmentValidationError(f"{class_code or 'That'} is not an equipment class in the structure.")
    keeps_class = current is not None and current.class_code == class_code
    if not keeps_class and not equipment_class.is_active:
        raise EquipmentValidationError(f"The class {equipment_class.class_label} has been retired, so it cannot be chosen.")
    type_code = code(payload.type_code)
    if type_code is not None:
        equipment_type = find_type(equipment_class, type_code)
        if equipment_type is None:
            raise EquipmentValidationError(f"{type_code} is not a type of {equipment_class.class_label}.")
        keeps_type = keeps_class and current is not None and current.type_code == type_code
        if not keeps_type and not equipment_type.is_active:
            raise EquipmentValidationError(f"The type {equipment_type.type_label} has been retired, so it cannot be chosen.")
    kept = frozenset(item.capability_code for item in current.capabilities) if current and keeps_class else frozenset()
    values = normalize_capability_values(payload.capabilities, equipment_class, kept_codes=kept)
    fields = {
        "maker": maker,
        "model_name": model_name,
        "class_code": class_code,
        "type_code": type_code,
        "maker_part_number": clean(payload.maker_part_number),
    }
    return fields, values


def _resolve_fits(
    db: Session,
    payload: EquipmentModelFields,
    fields: dict[str, Any],
    structure: EquipmentStructureResponse,
    *,
    current: EquipmentModelResponse | None = None,
) -> list[dict[str, Any]]:
    """The crane models a kit model fits: one or more, each a recorded model whose class this kind of kit is
    kit for, none given twice, and none newly chosen once retired (owner, Q12). Any other model fits
    nothing."""
    equipment_class = find_class(structure, fields["class_code"])
    wanted = [str(item) for item in payload.fits_model_public_ids]
    if not is_kit_class(equipment_class):
        if wanted:
            raise EquipmentValidationError("Only a model of a kind of kit fits crane models.")
        return []
    assert equipment_class is not None
    if not wanted:
        raise EquipmentValidationError(f"Choose the crane models this {equipment_class.class_label.lower()} fits: at least one.")
    if len(set(wanted)) != len(wanted):
        raise EquipmentValidationError("A crane model is chosen twice. Choose each once.")
    kept = {str(item.model_public_id) for item in current.fits_models} if current else set()
    rows: list[dict[str, Any]] = []
    for public_id in wanted:
        row = repo.get_model_row(db, public_id=public_id)
        if row is None:
            raise EquipmentNotFoundError("A crane model chosen was not found.")
        label = f"{row['maker']} {row['model_name']}"
        if current is not None and str(row["model_public_id"]) == str(current.model_public_id):
            raise EquipmentValidationError("A model cannot fit itself.")
        if row["class_code"] not in equipment_class.kit_for_class_codes:
            raise EquipmentValidationError(f"{label} is not a model {equipment_class.class_label.lower()} is kit for.")
        if row["is_retired"] and public_id not in kept:
            raise EquipmentValidationError(f"{label} is retired, so kit cannot be newly fitted to it.")
        rows.append(row)
    return rows


def _write_fits(db: Session, *, model_id: int, class_code: str, crane_rows: list[dict[str, Any]], user_public_id: str | None) -> None:
    repo.delete_model_fits(db, kit_model_id=model_id)
    for row in crane_rows:
        repo.insert_model_fit(
            db,
            kit_model_id=model_id,
            kit_class_code=class_code,
            crane_model_id=int(row["id"]),
            crane_class_code=row["class_code"],
            user_public_id=user_public_id,
        )


def _write_capabilities(db: Session, *, model_id: int, class_code: str, values: list[CapabilityValue]) -> None:
    repo.delete_model_capabilities(db, model_id=model_id)
    for value in values:
        repo.insert_model_capability(
            db,
            model_id=model_id,
            class_code=class_code,
            capability_code=value.capability_code,
            value=value.value,
            choice=value.choice_value,
        )


def _event_payload(
    model: EquipmentModelResponse, changed_fields: list[str], *, previous_fits: list[str] | None = None
) -> dict[str, Any]:
    """Public ids and codes only: a kit model's crane models, and which of them this change added and removed."""
    fits = [str(item.model_public_id) for item in model.fits_models]
    before = previous_fits if previous_fits is not None else []
    payload: dict[str, Any] = {
        "model_public_id": str(model.model_public_id),
        "class_code": model.class_code,
        "type_code": model.type_code,
        "model_version": model.model_version,
        "is_retired": model.is_retired,
        "capability_codes": [item.capability_code for item in model.capabilities],
        "changed_fields": changed_fields,
    }
    if model.is_kit:
        payload["fits_model_public_ids"] = fits
        payload["fits_added"] = sorted(set(fits) - set(before))
        payload["fits_removed"] = sorted(set(before) - set(fits))
    return payload


def _refuse_duplicate(db: Session, fields: dict[str, Any], structure: EquipmentStructureResponse, *, except_public_id: str | None) -> None:
    existing = repo.find_model_by_key(db, maker=fields["maker"], model_name=fields["model_name"], class_code=fields["class_code"])
    if existing is not None and str(existing["model_public_id"]) != except_public_id:
        equipment_class = find_class(structure, fields["class_code"])
        raise EquipmentConflictError(
            f"{fields['maker']} {fields['model_name']} is already recorded as a "
            f"{equipment_class.class_label if equipment_class else fields['class_code']} model."
        )


MODEL_KEY_USED = (
    "This form was already used to record a model, so this save was not recorded. Reload the page to see the model "
    "it recorded, and change it there."
)


def _replayed_model(db: Session, existing: dict[str, Any], fingerprint: str) -> EquipmentModelActionResponse:
    """The model a request key made, returned again with no event - only to the very same request. Any other request
    with the key is refused, never answered with a model it did not ask for (TB-1 TB1-102 part b, 8A's rule)."""
    if not is_same_request(existing["create_request_fingerprint"], fingerprint):
        raise EquipmentConflictError(MODEL_KEY_USED)
    return EquipmentModelActionResponse(model=get_model(db, existing["model_public_id"]), event=None, replayed=True)


def create_model(db: Session, *, payload: EquipmentModelCreate, user_public_id: str | None) -> EquipmentModelActionResponse:
    key = str(payload.create_request_key)
    fingerprint = request_fingerprint(payload)
    existing = repo.find_model_by_create_request_key(db, create_request_key=key)
    if existing is not None:
        return _replayed_model(db, existing, fingerprint)
    public_id = str(uuid4())
    try:
        with rollback_on_error(db):
            begin_write(db)
            # Checked again under the lock: a second submission waiting on it finds the first's model.
            replayed = repo.find_model_by_create_request_key(db, create_request_key=key)
            if replayed is not None:
                db.rollback()
                return _replayed_model(db, replayed, fingerprint)
            structure = get_equipment_structure(db)
            fields, values = _normalize_model(payload, structure)
            crane_rows = _resolve_fits(db, payload, fields, structure)
            _refuse_duplicate(db, fields, structure, except_public_id=None)
            model_id = repo.insert_model(
                db,
                values={
                    **fields,
                    "model_public_id": public_id,
                    "create_request_key": key,
                    "create_request_fingerprint": fingerprint,
                    "created_by": user_public_id,
                    "updated_by": user_public_id,
                },
            )
            _write_capabilities(db, model_id=model_id, class_code=fields["class_code"], values=values)
            _write_fits(db, model_id=model_id, class_code=fields["class_code"], crane_rows=crane_rows, user_public_id=user_public_id)
            repo.bump_change_number(db)
            model = get_model(db, public_id, structure=structure)
            recorded = ["maker", "model_name", "class_code", "type_code", "capabilities"]
            if model.maker_part_number:
                recorded.append("maker_part_number")
            if model.is_kit:
                recorded.append("fits_models")
            event = record_event(
                db,
                event_name=EQUIPMENT_EVENT_MODEL_RECORDED,
                record_type=RECORD_TYPE_MODEL,
                record_public_id=public_id,
                user_public_id=user_public_id,
                payload=_event_payload(model, recorded),
                reason="Equipment model recorded.",
            )
            db.commit()
    except IntegrityError as exc:
        # Two submissions of one key raced; the other committed first. Replay it, or refuse another request.
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        if constraint != "uq_equipment_model_create_request_key":
            raise
        existing = repo.find_model_by_create_request_key(db, create_request_key=key)
        if existing is None:
            raise
        return _replayed_model(db, existing, fingerprint)
    return EquipmentModelActionResponse(model=model, event=event)


def _rederive_machines_of(db: Session, *, model_id: int, model_public_id: str, user_public_id: str | None) -> None:
    """A model's type and ratings are what its machines are read against: re-read each machine now, so a
    rating the report no longer differs from - or newly differs from - is flagged at once rather than at the
    next import (independent review, round 1, ERT1-R1-007). A machine whose facts changed records why. Every
    machine of the model moves its version on - what it shows (its model, its ratings) comes from the model
    - and so does any asset a re-reading changed."""
    changed: set[int] = set()
    for row in repo.list_asset_keys_using_model(db, model_id=model_id):
        asset_id, asset_public_id = int(row["id"]), str(row["asset_public_id"])
        result = rederive_asset(db, asset_id=asset_id, public_id=asset_public_id, user_public_id=user_public_id)
        changed.add(asset_id)
        changed.update(result.changed_asset_ids)
        if result.changed_facts:
            record_event(
                db,
                event_name=EQUIPMENT_EVENT_ASSET_CHANGED,
                record_type=RECORD_TYPE_ASSET,
                record_public_id=asset_public_id,
                user_public_id=user_public_id,
                payload={
                    "model_public_id": model_public_id,
                    "changed_facts": list(result.changed_facts),
                    "closed_link_public_ids": list(result.closed_link_public_ids),
                },
                reason="Machine's facts changed with its model.",
            )
    bump_versions(db, changed, user_public_id=user_public_id, at=now())


def update_model(
    db: Session, *, public_id: UUID, payload: EquipmentModelUpdate, user_public_id: str | None
) -> EquipmentModelActionResponse:
    """Whole replacement of a model and its ratings, guarded by the version the Fleet Admin read. An
    identical save records nothing."""
    with rollback_on_error(db):
        begin_write(db)
        structure = get_equipment_structure(db)
        current = get_model(db, public_id, structure=structure)
        if current.model_version != payload.expected_model_version:
            raise EquipmentConflictError("Someone else changed this model after you opened it. Reload to see their version.")
        fields, values = _normalize_model(payload, structure, current=current)
        class_changes = fields["class_code"] != current.class_code
        if class_changes and current.machine_count > 0:
            raise EquipmentValidationError(
                f"{current.machine_count} record{'s' if current.machine_count != 1 else ''} use this model, so its "
                "class cannot change. Record a new model and map the name to it."
            )
        row = repo.get_model_row(db, public_id=str(public_id))
        assert row is not None
        model_id = int(row["id"])
        if class_changes and repo.count_fits_to_crane_model(db, model_id=model_id) > 0:
            raise EquipmentValidationError(
                "Kit is recorded as fitting this model, so its class cannot change. Take this model off those kit "
                "models first."
            )
        # No Plum model name is mapped to a kit model, so a mapped model does not become one (ERT2-R3-001).
        if class_changes and current.mapped_names and is_kit_class(find_class(structure, fields["class_code"])):
            raise EquipmentValidationError(
                "Plum model names are mapped to this model, so it cannot become a kind of kit: kit is recorded on "
                "the platform, not read from Plum's report. Record the kit model as a new model."
            )
        crane_rows = _resolve_fits(db, payload, fields, structure, current=current)
        _refuse_duplicate(db, fields, structure, except_public_id=str(public_id))
        changed = [
            name
            for name in ("maker", "model_name", "class_code", "type_code", "maker_part_number")
            if getattr(current, name) != fields[name]
        ]
        stored = sorted((item.capability_code, item.value, item.choice_value) for item in current.capabilities)
        if stored != sorted((value.capability_code, value.value, value.choice_value) for value in values):
            changed.append("capabilities")
        previous_fits = [str(item.model_public_id) for item in current.fits_models]
        if sorted(previous_fits) != sorted(str(item["model_public_id"]) for item in crane_rows):
            changed.append("fits_models")
        if current.is_retired != payload.is_retired:
            changed.append("is_retired")
        if not changed:
            db.rollback()
            return EquipmentModelActionResponse(model=current, event=None)
        # Ratings and fits go first: they are keyed to the model's class, which may be changing.
        repo.delete_model_capabilities(db, model_id=model_id)
        repo.delete_model_fits(db, kit_model_id=model_id)
        updated = repo.update_model(
            db,
            model_id=model_id,
            expected_version=payload.expected_model_version,
            values={**fields, "is_retired": payload.is_retired},
            user_public_id=user_public_id,
            at=now(),
        )
        if updated != 1:
            raise EquipmentConflictError("Someone else changed this model after you opened it. Reload to see their version.")
        _write_capabilities(db, model_id=model_id, class_code=fields["class_code"], values=values)
        _write_fits(db, model_id=model_id, class_code=fields["class_code"], crane_rows=crane_rows, user_public_id=user_public_id)
        _rederive_machines_of(db, model_id=model_id, model_public_id=str(public_id), user_public_id=user_public_id)
        repo.bump_change_number(db)
        model = get_model(db, public_id, structure=structure)
        event = record_event(
            db,
            event_name=EQUIPMENT_EVENT_MODEL_CHANGED,
            record_type=RECORD_TYPE_MODEL,
            record_public_id=str(public_id),
            user_public_id=user_public_id,
            payload=_event_payload(model, changed, previous_fits=previous_fits),
            reason="Equipment model changed.",
        )
        db.commit()
    return EquipmentModelActionResponse(model=model, event=event)


def map_model_name(db: Session, *, payload: ModelMappingInput, user_public_id: str | None) -> ModelMappingActionResponse:
    """Map a Plum model name to a model once; every later import uses it (design Q4). With no model, the
    mapping is removed. Takes effect on the next preview: nothing published changes here."""
    source_name = clean(payload.source_name)
    if source_name is None:
        raise EquipmentValidationError("Give the model name as Plum records it.")
    # Stored with every run of whitespace as one space, so the database's normalized form (which it
    # compares for uniqueness) and the transformer's (which it matches in) can never disagree.
    source_name = " ".join(source_name.split())
    with rollback_on_error(db):
        begin_write(db)
        existing = repo.find_model_mapping(db, source_name=source_name)
        previous = str(existing["model_public_id"]) if existing else None
        target: dict[str, Any] | None = None
        if payload.model_public_id is not None:
            target = repo.get_model_row(db, public_id=str(payload.model_public_id))
            if target is None:
                raise EquipmentNotFoundError("Model not found.")
        wanted = str(target["model_public_id"]) if target else None
        if wanted == previous:
            db.rollback()
            return ModelMappingActionResponse(source_name=source_name, model_public_id=wanted, event=None)
        if target is not None and target["is_retired"]:
            raise EquipmentValidationError(
                f"{target['maker']} {target['model_name']} is retired, so a model name cannot be newly mapped to it."
            )
        if target is not None and is_kit_class(find_class(get_equipment_structure(db), target["class_code"])):
            raise EquipmentValidationError(
                "Kit is recorded on the platform, not read from Plum's report, so no Plum model name is mapped to a kit "
                "model."
            )
        at = now()
        if target is None:
            assert existing is not None
            repo.delete_model_mapping(db, mapping_id=int(existing["id"]))
        elif existing is None:
            repo.insert_model_mapping(db, source_name=source_name, model_id=int(target["id"]), user_public_id=user_public_id, at=at)
        else:
            repo.update_model_mapping(db, mapping_id=int(existing["id"]), model_id=int(target["id"]), user_public_id=user_public_id, at=at)
        repo.bump_change_number(db)
        event = record_event(
            db,
            event_name=EQUIPMENT_EVENT_MODEL_MAPPED,
            # Recorded on the mapping itself, not on either model: a mapping is its own record, and a
            # test run's mapping to someone else's model must not leave its history on that model.
            record_type=RECORD_TYPE_MODEL_MAPPING,
            record_public_id=model_mapping_public_id(PROVIDER_PLUM, source_name),
            user_public_id=user_public_id,
            payload={"provider_code": PROVIDER_PLUM, "model_public_id": wanted, "previous_model_public_id": previous},
            reason="Plum model name mapped." if wanted else "Plum model name mapping removed.",
        )
        db.commit()
    return ModelMappingActionResponse(source_name=source_name, model_public_id=wanted, event=event)
