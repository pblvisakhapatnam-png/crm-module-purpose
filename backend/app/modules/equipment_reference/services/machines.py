"""Machines and their fitted parts (ERT-1 design, sections 4, 5A, 5B and 7).

Reading: a machine carries Plum's facts as of the report they came from, the platform's own facts, its
class, type and model, its capabilities (its own value where the Fleet Admin set one, otherwise its
model's), its fitted parts, its flags and its corrections.

Writing, all by the Fleet Admin and each guarded by the version the caller read:

- details Plum does not hold (serial number, year of manufacture) - the platform's, never overwritten by
  an import;
- a machine's own capability values, each with a reason;
- a correction of one Plum field, which applies at once - the machine is re-read from the values its last
  report gave, with the correction - and on every later import until Plum agrees;
- fitting a part to a machine, and removing it, by dated link.

No route here changes a Plum fact except through a recorded correction.

Engine and chassis numbers are confidential (owner, 25 September 2026): every read withholds them, and the
values of any correction to them, unless the caller holds EQUIPMENT_IDENTITY_READ (`show_identity`).

Detachable kit (ERT-2) is recorded here too, because every kit write returns a machine page: the Fleet
Admin adds pieces of a kit model - several alike, one record each, or a counted set in one record - which
are held for every machine of the crane models the kit model fits, never linked to one (owner, Q6). A
piece's details and own ratings use the machine routes. A piece is retired with the day and the reason; a
counted set also by retiring some of its pieces, which is the only way it shrinks, so every piece that
leaves is dated and explained - what the Fixed Assets module will read when it comes (owner, 26
September 2026).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.equipment_reference import repository as repo
from app.modules.equipment_reference.contract import (
    ASSET_KIND_MACHINE,
    ASSET_KIND_PART,
    ASSET_STATUS_ACTIVE,
    ASSET_STATUS_CODES,
    ASSET_STATUS_RETIRED,
    CLASS_KIND_MACHINE,
    CLOSED_BY_FLEET_ADMIN,
    CLOSED_SUPERSEDED,
    CORRECTION_FIELD_CAPACITY,
    CORRECTION_FIELD_CATEGORY,
    CORRECTION_FIELD_COMMENCED_YEAR,
    CORRECTION_FIELD_MODEL,
    CORRECTION_FIELD_STATUS,
    CORRECTION_FIELDS,
    DATA_QUALITY_PART_NOT_FITTED,
    EARLIEST_YEAR,
    EQUIPMENT_EVENT_ASSET_REGISTERED,
    EQUIPMENT_EVENT_ASSET_RETIRED,
    EQUIPMENT_EVENT_CORRECTION_CLOSED,
    EQUIPMENT_EVENT_CORRECTION_RECORDED,
    EQUIPMENT_EVENT_MACHINE_CAPABILITY_SET,
    EQUIPMENT_EVENT_MACHINE_DETAILS_SET,
    EQUIPMENT_EVENT_PART_FITTED,
    EQUIPMENT_EVENT_PART_REMOVED,
    ORIGIN_PLATFORM,
    RECORD_TYPE_ASSET,
    RETIREMENT_OTHER,
    RETIREMENT_REASON_CODES,
    STATUS_OPEN,
    TEXT_VALUE_MAX_LENGTH,
    TRACKING_COUNTED,
    TRACKING_SINGLE,
    normalize_term,
)
from app.modules.equipment_reference.ports import KitListingSource, kit_listing_source
from app.modules.equipment_reference.plum_report import (
    model_key_of,
    parse_number,
    plum_value_for_correction,
    row_from_values,
)
from app.modules.equipment_reference.schemas import (
    AssetReference,
    EquipmentStructureResponse,
    FitPartInput,
    KitAddInput,
    KitAddResponse,
    KitHeldResponse,
    KitRetireInput,
    MachineActionResponse,
    MachineCapabilitiesInput,
    MachineCapabilityResponse,
    MachineCorrectionCloseInput,
    MachineCorrectionInput,
    MachineCorrectionResponse,
    MachineDetailsInput,
    MachineFlagResponse,
    MachineLinkResponse,
    MachineResponse,
    MachineSummaryResponse,
    ModelReference,
    PlumSourceWords,
    RemovePartInput,
)
from app.modules.equipment_reference.service import (
    AllocationAsset,
    AllocationCapability,
    find_class,
    find_type,
    get_equipment_structure,
    is_kit_class,
    key_capability,
)
from app.modules.equipment_reference.services.common import (
    EquipmentConflictError,
    EquipmentNotFoundError,
    EquipmentValidationError,
    ModelRecords,
    begin_write,
    bump_versions,
    check_can_fit,
    clean,
    code,
    correction_values,
    load_models,
    normalize_capability_values,
    now,
    record_event,
    required_reason,
    require_user,
    rederive_asset,
)
from app.shared import business_time
from app.shared.request_keys import is_same_request, request_fingerprint
from app.shared.transactions import rollback_on_error

STALE_MACHINE = "Someone else changed this machine after you opened it. Reload to see their version."
STALE_KIT_MODEL = "Someone else changed this kit model after you opened the page. Reload to see their version."
KIT_KEY_USED = (
    "This form was already used to add kit, so this save was not recorded. Reload the page to see the kit it added."
)


# --- Reading ---------------------------------------------------------------------------------------


def _effective_capabilities(
    equipment_class: Any, own: dict[str, dict[str, Any]], model_values: dict[str, Any]
) -> list[MachineCapabilityResponse]:
    """Every capability of the class: the machine's own value where the Fleet Admin set one, otherwise its
    model's rating, otherwise none."""
    responses: list[MachineCapabilityResponse] = []
    for capability in equipment_class.capabilities if equipment_class else []:
        mine = own.get(capability.capability_code)
        rated = model_values.get(capability.capability_code)
        if mine is not None:
            value, choice, source = mine["capability_value"], mine["choice_value"], "OWN"
        elif rated is not None:
            value, choice, source = (rated, None, "MODEL") if isinstance(rated, Decimal) else (None, rated, "MODEL")
        else:
            value, choice, source = None, None, "NONE"
        responses.append(
            MachineCapabilityResponse(
                capability_code=capability.capability_code,
                capability_label=capability.capability_label,
                unit_code=capability.unit_code,
                unit_symbol=capability.unit_symbol,
                value_kind_code=capability.value_kind_code,
                is_key=capability.is_key,
                value=value,
                choice_value=choice,
                source_code=source,
                reason=mine["reason"] if mine else None,
                set_by_display_name=mine["set_by_display_name"] if mine else None,
                set_at=mine["set_at"] if mine else None,
            )
        )
    return responses


def _reference(row: dict[str, Any], prefix: str) -> AssetReference:
    return AssetReference(
        asset_public_id=row[f"{prefix}_public_id"],
        asset_reference=row[f"{prefix}_reference"],
        machine_number=row[f"{prefix}_machine_number"],
        class_code=row[f"{prefix}_class_code"],
        asset_version=int(row[f"{prefix}_asset_version"]),
    )


def _link(row: dict[str, Any]) -> MachineLinkResponse:
    return MachineLinkResponse(
        link_public_id=row["link_public_id"],
        machine=_reference(row, "parent"),
        part=_reference(row, "child"),
        fitted_on=row["fitted_on"],
        removed_on=row["removed_on"],
    )


def _plum_words(values: dict[str, Any] | None) -> PlumSourceWords | None:
    if not values:
        return None
    row = row_from_values(0, values)
    return PlumSourceWords(category=row.category, model_name=model_key_of(row), capacity=row.capacity or row.load_capacity)


def _key_value(equipment_class: Any, model_values: dict[str, Any], own: dict[str, dict[str, Any]] | None = None) -> Any:
    """The key capability as shown in a list: the record's own value or its model's rating, or None."""
    capabilities = _effective_capabilities(equipment_class, own or {}, model_values)
    key = key_capability(equipment_class) if equipment_class else None
    found = next((item for item in capabilities if key and item.capability_code == key.capability_code), None)
    return found if found and found.source_code != "NONE" else None


def _details_missing(row: dict[str, Any], equipment_class: Any) -> bool:
    """A machine without its serial number or year of manufacture, or a piece of kit tracked one by one
    without its own number - repository.DETAILS_TO_COMPLETE says the same in SQL."""
    if row["asset_kind_code"] == ASSET_KIND_MACHINE:
        return row["serial_number"] is None or row["year_of_manufacture"] is None
    return (
        row["origin_code"] == ORIGIN_PLATFORM
        and row["serial_number"] is None
        and equipment_class is not None
        and equipment_class.tracking_code == TRACKING_SINGLE
    )


def _fit_references(rows: list[dict[str, Any]]) -> dict[int, list[ModelReference]]:
    fits: dict[int, list[ModelReference]] = {}
    for item in rows:
        fits.setdefault(int(item["kit_model_id"]), []).append(
            ModelReference(model_public_id=item["crane_model_public_id"], label=item["crane_model_label"])
        )
    return fits


def _kit_held(
    db: Session, row: dict[str, Any], *, structure: EquipmentStructureResponse, models: ModelRecords
) -> tuple[list[KitHeldResponse], int | None]:
    """For a machine: the kit held for its model - every kit model that fits it, with the pieces held - and
    how many active machines of the model share it. Nothing for a part, or a machine with no model yet."""
    if row["asset_kind_code"] != ASSET_KIND_MACHINE or row["equipment_model_id"] is None:
        return [], None
    crane_model = repo.get_model_row(db, public_id=str(row["model_public_id"]))
    held_rows = repo.list_kit_held_rows(db, crane_model_id=int(row["equipment_model_id"]))
    fits = _fit_references(repo.list_model_fit_rows(db, model_ids=[int(item["kit_model_id"]) for item in held_rows]))
    held: list[KitHeldResponse] = []
    for item in held_rows:
        kit_class = find_class(structure, item["class_code"])
        kit_type = find_type(kit_class, item["type_code"]) if kit_class and item["type_code"] else None
        kit_model = models.by_public_id.get(str(item["kit_model_public_id"]))
        held.append(
            KitHeldResponse(
                kit_model_public_id=item["kit_model_public_id"],
                label=f"{item['maker']} {item['model_name']}",
                class_code=item["class_code"],
                class_label=kit_class.class_label if kit_class else item["class_code"],
                type_code=item["type_code"],
                type_label=kit_type.type_label if kit_type else None,
                tracking_code=kit_class.tracking_code if kit_class else TRACKING_SINGLE,
                key_capability=_key_value(kit_class, kit_model.capabilities if kit_model else {}),
                pieces_held=int(item["pieces_held"]),
                records_held=int(item["records_held"]),
                fits_models=fits.get(int(item["kit_model_id"]), []),
            )
        )
    return held, int(crane_model["active_unit_count"]) if crane_model else None


def _build(
    db: Session,
    rows: list[dict[str, Any]],
    *,
    structure: EquipmentStructureResponse,
    models: ModelRecords,
    full: bool,
    show_identity: bool = False,
) -> list[MachineResponse] | list[MachineSummaryResponse]:
    """One serializer for the list and the page: flags, own values and (for the page) corrections and links
    are read in one statement each for all the rows. Engine and chassis numbers, and the values of any
    correction to them, are withheld unless `show_identity` (EQUIPMENT_IDENTITY_READ): withholding is the
    default, so a caller that forgets the flag shows less, never more."""
    ids = [int(row["id"]) for row in rows]
    flags: dict[int, list[dict[str, Any]]] = {}
    for flag in repo.list_asset_flag_rows(db, asset_ids=ids):
        flags.setdefault(int(flag["equipment_asset_id"]), []).append(flag)
    own: dict[int, dict[str, dict[str, Any]]] = {}
    for item in repo.list_asset_capability_rows(db, asset_ids=ids):
        own.setdefault(int(item["equipment_asset_id"]), {})[item["capability_code"]] = item
    corrections: dict[int, list[dict[str, Any]]] = {}
    links: dict[int, list[dict[str, Any]]] = {}
    if full:
        for item in repo.list_asset_correction_rows(db, asset_ids=ids, open_only=False):
            corrections.setdefault(int(item["equipment_asset_id"]), []).append(item)
        for item in repo.list_asset_link_rows(db, asset_ids=ids):
            for asset_id in {int(item["parent_asset_id"]), int(item["child_asset_id"])} & set(ids):
                links.setdefault(asset_id, []).append(item)

    responses: list[Any] = []
    for row in rows:
        asset_id = int(row["id"])
        equipment_class = find_class(structure, row["class_code"])
        equipment_type = find_type(equipment_class, row["type_code"]) if equipment_class and row["type_code"] else None
        model = models.by_public_id.get(str(row["model_public_id"])) if row["model_public_id"] else None
        capabilities = _effective_capabilities(equipment_class, own.get(asset_id, {}), model.capabilities if model else {})
        summary: dict[str, Any] = {
            "asset_public_id": row["asset_public_id"],
            "asset_reference": row["asset_reference"],
            "asset_kind_code": row["asset_kind_code"],
            "origin_code": row["origin_code"],
            "machine_number": row["machine_number"],
            "quantity": int(row["quantity"]),
            "class_code": row["class_code"],
            "class_label": equipment_class.class_label if equipment_class else row["class_code"],
            "type_code": row["type_code"],
            "type_label": equipment_type.type_label if equipment_type else None,
            "model_public_id": row["model_public_id"],
            "model_label": model.label if model else None,
            "key_capability": _key_value(equipment_class, model.capabilities if model else {}, own.get(asset_id, {})),
            "asset_status_code": row["asset_status_code"],
            "flag_codes": sorted({flag["flag_code"] for flag in flags.get(asset_id, [])}),
            "details_missing": _details_missing(row, equipment_class),
            "facts_report_date": row["facts_report_date"],
            "asset_version": int(row["asset_version"]),
        }
        if not full:
            responses.append(MachineSummaryResponse(**summary))
            continue
        asset_links = links.get(asset_id, [])
        open_parts = [_link(item) for item in asset_links if int(item["parent_asset_id"]) == asset_id and item["removed_on"] is None]
        fitted_to = next(
            (_link(item) for item in asset_links if int(item["child_asset_id"]) == asset_id and item["removed_on"] is None),
            None,
        )
        asset_corrections = sorted(
            corrections.get(asset_id, []), key=lambda item: (item["correction_status_code"] != STATUS_OPEN, -item["recorded_at"].timestamp())
        )
        kit, model_active_units = _kit_held(db, row, structure=structure, models=models)
        piece_fits: list[ModelReference] = []
        if row["origin_code"] == ORIGIN_PLATFORM and row["equipment_model_id"] is not None:
            piece_fits = _fit_references(repo.list_model_fit_rows(db, model_ids=[int(row["equipment_model_id"])])).get(
                int(row["equipment_model_id"]), []
            )
        responses.append(
            MachineResponse(
                **summary,
                engine_number=row["engine_number"] if show_identity else None,
                chassis_number=row["chassis_number"] if show_identity else None,
                identity_numbers_withheld=not show_identity,
                commenced_year=row["commenced_year"],
                owning_company=row["owning_company"],
                serial_number=row["serial_number"],
                year_of_manufacture=row["year_of_manufacture"],
                capabilities=capabilities,
                flags=[
                    MachineFlagResponse(
                        flag_code=flag["flag_code"],
                        subject_code=flag["subject_code"],
                        raised_at=flag["raised_at"],
                        raised_by_import_public_id=flag["raised_by_import_public_id"],
                    )
                    for flag in flags.get(asset_id, [])
                ],
                corrections=[
                    MachineCorrectionResponse(
                        correction_public_id=item["correction_public_id"],
                        field_code=item["field_code"],
                        correction_status_code=item["correction_status_code"],
                        closed_reason_code=item["closed_reason_code"],
                        closed_by_display_name=item["closed_by_display_name"],
                        closed_at=item["closed_at"],
                        recorded_by_display_name=item["recorded_by_display_name"],
                        recorded_at=item["recorded_at"],
                        **correction_values(item, structure, models, show_identity=show_identity),
                    )
                    for item in asset_corrections
                ],
                fitted_parts=open_parts,
                fitted_to=fitted_to,
                link_history=[_link(item) for item in asset_links if item["removed_on"] is not None],
                plum=_plum_words(row["source_values"]),
                reconciliation_status_code=row["reconciliation_status_code"],
                last_import_public_id=row["last_import_public_id"],
                kit=kit,
                model_active_unit_count=model_active_units,
                fits_models=piece_fits,
                retired_on=row["retired_on"],
                retirement_reason_code=row["retirement_reason_code"],
                retirement_note=row["retirement_note"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        )
    return responses


def list_machines(
    db: Session,
    *,
    kind_code: str | None = None,
    class_code: str | None = None,
    type_code: str | None = None,
    status_code: str | None = None,
    flagged_only: bool = False,
    details_to_complete: bool = False,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
    kit_model_public_id: UUID | str | None = None,
    fits_model_public_id: UUID | str | None = None,
) -> list[MachineSummaryResponse]:
    """Machines, parts and pieces of kit. `kit_model_public_id` lists the pieces of one kit model;
    `fits_model_public_id` the kit held for one machine model (ERT-2)."""
    kind = code(kind_code)
    if kind is not None and kind not in (ASSET_KIND_MACHINE, ASSET_KIND_PART):
        raise EquipmentValidationError("Kind must be Machine or Part.")
    status = code(status_code)
    if status is not None and status not in ASSET_STATUS_CODES:
        raise EquipmentValidationError("Status must be Active or Retired.")
    rows = repo.list_asset_rows(
        db,
        kind_code=kind,
        class_code=code(class_code),
        type_code=code(type_code),
        status_code=status,
        flagged_only=flagged_only,
        details_to_complete=details_to_complete,
        search=clean(search),
        limit=limit,
        offset=offset,
        kit_model_public_id=str(kit_model_public_id) if kit_model_public_id else None,
        fits_model_public_id=str(fits_model_public_id) if fits_model_public_id else None,
    )
    return _build(db, rows, structure=get_equipment_structure(db), models=load_models(db), full=False)  # type: ignore[return-value]


def get_machine(db: Session, public_id: UUID | str, *, show_identity: bool = False) -> MachineResponse:
    """One machine. Engine and chassis numbers only with `show_identity` (the caller holds
    EQUIPMENT_IDENTITY_READ)."""
    row = repo.get_asset_row(db, public_id=str(public_id))
    if row is None:
        raise EquipmentNotFoundError("Machine not found.")
    return _build(  # type: ignore[return-value]
        db, [row], structure=get_equipment_structure(db), models=load_models(db), full=True, show_identity=show_identity
    )[0]


_ALL_ROWS = 100_000


def allocation_assets(
    db: Session,
    *,
    kind_code: str | None = None,
    class_code: str | None = None,
    status_code: str | None = None,
    public_id: str | None = None,
    fits_model_public_id: str | None = None,
) -> list[AllocationAsset]:
    """Machines or pieces of kit as allocation reads them (8A core, through service.py): one statement each for
    the rows, their own values and their flags, with the model ratings loaded once."""
    if public_id is not None:
        row = repo.get_asset_row(db, public_id=public_id)
        rows = [row] if row is not None else []
    else:
        rows = repo.list_asset_rows(
            db,
            kind_code=kind_code,
            class_code=class_code,
            type_code=None,
            status_code=status_code,
            flagged_only=False,
            details_to_complete=False,
            search=None,
            limit=_ALL_ROWS,
            offset=0,
            fits_model_public_id=fits_model_public_id,
        )
    if not rows:
        return []
    structure = get_equipment_structure(db)
    models = load_models(db)
    ids = [int(row["id"]) for row in rows]
    own: dict[int, dict[str, dict[str, Any]]] = {}
    for item in repo.list_asset_capability_rows(db, asset_ids=ids):
        own.setdefault(int(item["equipment_asset_id"]), {})[item["capability_code"]] = item
    flags: dict[int, set[str]] = {}
    for flag in repo.list_asset_flag_rows(db, asset_ids=ids):
        flags.setdefault(int(flag["equipment_asset_id"]), set()).add(flag["flag_code"])
    assets: list[AllocationAsset] = []
    for row in rows:
        asset_id = int(row["id"])
        equipment_class = find_class(structure, row["class_code"])
        equipment_type = find_type(equipment_class, row["type_code"]) if equipment_class and row["type_code"] else None
        model = models.by_public_id.get(str(row["model_public_id"])) if row["model_public_id"] else None
        capabilities = _effective_capabilities(equipment_class, own.get(asset_id, {}), model.capabilities if model else {})
        assets.append(
            AllocationAsset(
                asset_public_id=str(row["asset_public_id"]),
                asset_reference=row["asset_reference"],
                asset_kind_code=row["asset_kind_code"],
                origin_code=row["origin_code"],
                machine_number=row["machine_number"],
                serial_number=row["serial_number"],
                class_code=row["class_code"],
                class_label=equipment_class.class_label if equipment_class else row["class_code"],
                type_code=row["type_code"],
                type_label=equipment_type.type_label if equipment_type else None,
                model_public_id=str(row["model_public_id"]) if row["model_public_id"] else None,
                model_label=model.label if model else None,
                asset_status_code=row["asset_status_code"],
                asset_version=int(row["asset_version"]),
                quantity=int(row["quantity"]),
                tracking_code=equipment_class.tracking_code if equipment_class else TRACKING_SINGLE,
                capabilities=tuple(
                    AllocationCapability(
                        capability_code=item.capability_code,
                        capability_label=item.capability_label,
                        unit_symbol=item.unit_symbol,
                        value_kind_code=item.value_kind_code,
                        is_key=item.is_key,
                        value=item.value,
                        choice_value=item.choice_value,
                    )
                    for item in capabilities
                    if item.source_code != "NONE"
                ),
                flag_codes=tuple(sorted(flags.get(asset_id, set()))),
            )
        )
    return assets


# --- Writing ---------------------------------------------------------------------------------------


def _locked(db: Session, public_id: UUID | str, expected_version: int) -> dict[str, Any]:
    locked = repo.lock_asset_row(db, public_id=str(public_id))
    if locked is None:
        raise EquipmentNotFoundError("Machine not found.")
    if int(locked["asset_version"]) != expected_version:
        raise EquipmentConflictError(STALE_MACHINE)
    return locked


def _asset_event(
    db: Session, *, event_name: str, machine: MachineResponse, user_public_id: str | None, payload: dict[str, Any], reason: str
) -> dict[str, Any]:
    return record_event(
        db,
        event_name=event_name,
        record_type=RECORD_TYPE_ASSET,
        record_public_id=str(machine.asset_public_id),
        user_public_id=user_public_id,
        payload={"asset_reference": machine.asset_reference, "asset_version": machine.asset_version, **payload},
        reason=reason,
        status_after=machine.asset_status_code,
    )


def _check_year_of_manufacture(year: int | None) -> None:
    # A machine or piece is not made in a year still to come; this year is judged where PBL works (owner's
    # screen check, 27 September 2026 - ERT-1 had allowed next year, with no recorded reason).
    this_year = business_time.india_today().year
    if year is not None and year > this_year:
        raise EquipmentValidationError(f"The year of manufacture cannot be later than {this_year}.")


def _kit_detail_values(
    db: Session, *, current: MachineResponse, payload: MachineDetailsInput, serial: str | None
) -> tuple[dict[str, Any], dict[str, Any]]:
    """A piece of kit's own facts beyond its number and year: a counted set's quantity, raised only - a set
    shrinks by retiring the pieces that left, with the reason - and another model of the same kind. Returns
    the columns to write and what the event says of them."""
    equipment_class = find_class(get_equipment_structure(db), current.class_code)
    tracking = equipment_class.tracking_code if equipment_class else TRACKING_SINGLE
    if serial is not None and tracking == TRACKING_COUNTED:
        raise EquipmentValidationError("A counted set has no number of its own: its pieces are counted, not named.")
    values: dict[str, Any] = {}
    said: dict[str, Any] = {}
    retired = current.asset_status_code == ASSET_STATUS_RETIRED
    if payload.quantity is not None and payload.quantity != current.quantity:
        if retired:
            raise EquipmentValidationError("This piece is retired, so its count cannot change.")
        if tracking != TRACKING_COUNTED:
            raise EquipmentValidationError(f"A {current.class_label.lower()} is tracked one by one: each record holds one piece.")
        if payload.quantity < current.quantity:
            raise EquipmentValidationError(
                "A counted set shrinks only by retiring the pieces that left, with the reason and the day. Use Retire."
            )
        values["quantity"] = payload.quantity
        said.update(quantity_before=current.quantity, quantity_after=payload.quantity)
    if payload.model_public_id is not None and str(payload.model_public_id) != str(current.model_public_id):
        if retired:
            raise EquipmentValidationError("This piece is retired, so its model cannot change.")
        model = repo.get_model_row(db, public_id=str(payload.model_public_id))
        if model is None:
            raise EquipmentNotFoundError("Model not found.")
        if model["class_code"] != current.class_code:
            raise EquipmentValidationError(f"Choose a model of {current.class_label.lower()}: a piece keeps its kind.")
        if model["is_retired"]:
            raise EquipmentValidationError(f"{model['maker']} {model['model_name']} is retired, so a piece cannot be newly given it.")
        values["equipment_model_id"] = int(model["id"])
        if model["type_code"] != current.type_code:
            # The type follows the model, as a machine's does (ERT-1 refinement 2).
            values["type_code"] = model["type_code"]
        said.update(model_public_id_before=str(current.model_public_id), model_public_id_after=str(model["model_public_id"]))
    return values, said


def set_machine_details(
    db: Session, *, public_id: UUID, payload: MachineDetailsInput, user_public_id: str | None, show_identity: bool = False
) -> MachineActionResponse:
    """Facts Plum does not hold, entered by the Fleet Admin (design section 5A). The transformer never
    writes them. Details do not change what a preview computes, so they leave previews current. For a piece
    of kit (ERT-2), also a counted set's quantity and its model."""
    serial = clean(payload.serial_number)
    year = payload.year_of_manufacture
    _check_year_of_manufacture(year)
    with rollback_on_error(db):
        begin_write(db)
        locked = _locked(db, public_id, payload.expected_asset_version)
        current = get_machine(db, public_id, show_identity=show_identity)
        kit_values: dict[str, Any] = {}
        said: dict[str, Any] = {}
        if locked["origin_code"] == ORIGIN_PLATFORM:
            kit_values, said = _kit_detail_values(db, current=current, payload=payload, serial=serial)
        elif payload.quantity is not None or payload.model_public_id is not None:
            raise EquipmentValidationError(
                "Only a piece of kit has a count or a model of its own here. A machine's model is its Plum model name's "
                "mapping, or a correction."
            )
        changed = [
            name
            for name, value in (("serial_number", serial), ("year_of_manufacture", year))
            if getattr(current, name) != value
        ] + [{"equipment_model_id": "model", "type_code": "type"}.get(name, name) for name in kit_values]
        if not changed:
            db.rollback()
            return MachineActionResponse(machine=current, event=None)
        repo.update_asset(
            db,
            asset_id=int(locked["id"]),
            values={"serial_number": serial, "year_of_manufacture": year, **kit_values},
            user_public_id=user_public_id,
            at=now(),
            expected_version=payload.expected_asset_version,
        )
        machine = get_machine(db, public_id, show_identity=show_identity)
        event = _asset_event(
            db,
            event_name=EQUIPMENT_EVENT_MACHINE_DETAILS_SET,
            machine=machine,
            user_public_id=user_public_id,
            payload={"changed_fields": changed, **said},
            reason="Machine details entered on the platform." if not kit_values else "Kit details changed on the platform.",
        )
        db.commit()
    return MachineActionResponse(machine=machine, event=event)


def set_machine_capabilities(
    db: Session, *, public_id: UUID, payload: MachineCapabilitiesInput, user_public_id: str | None, show_identity: bool = False
) -> MachineActionResponse:
    """The Fleet Admin's own values for one machine - a crane de-rated after repair, say - each with its
    reason, as a whole. A capability left out takes its model's rating again. A piece of kit may hold its own
    values too, where its kind has capabilities - a hook block de-rated after an examination (ERT-2)."""
    actor = require_user(user_public_id)
    with rollback_on_error(db):
        begin_write(db)
        locked = _locked(db, public_id, payload.expected_asset_version)
        if locked["asset_kind_code"] != ASSET_KIND_MACHINE and locked["origin_code"] != ORIGIN_PLATFORM:
            raise EquipmentValidationError("A part has no capabilities of its own: they belong to the machine it is fitted to.")
        structure = get_equipment_structure(db)
        equipment_class = find_class(structure, locked["class_code"])
        assert equipment_class is not None
        current = get_machine(db, public_id, show_identity=show_identity)
        own_now = {item.capability_code: item for item in current.capabilities if item.source_code == "OWN"}
        values = normalize_capability_values(
            payload.capabilities, equipment_class, kept_codes=frozenset(own_now), with_reason=True
        )
        stored = sorted((code_, item.value, item.choice_value, item.reason) for code_, item in own_now.items())
        wanted = sorted((value.capability_code, value.value, value.choice_value, value.reason) for value in values)
        if stored == wanted:
            db.rollback()
            return MachineActionResponse(machine=current, event=None)
        at = now()
        repo.delete_asset_capabilities(db, asset_id=int(locked["id"]))
        for value in values:
            repo.insert_asset_capability(
                db,
                asset_id=int(locked["id"]),
                class_code=locked["class_code"],
                capability_code=value.capability_code,
                value=value.value,
                choice=value.choice_value,
                reason=value.reason or "",
                user_public_id=actor,
                at=at,
            )
        repo.update_asset(
            db,
            asset_id=int(locked["id"]),
            values={},
            user_public_id=user_public_id,
            at=at,
            expected_version=payload.expected_asset_version,
        )
        # The capacity check compares Plum's figure with these values first, so the machine's own row is
        # checked again now, not at the next report (independent review, round 1, ERT1-R1-007). Its version
        # has moved on above; only an asset at the other end of a link a re-reading closed moves here.
        rederived = rederive_asset(db, asset_id=int(locked["id"]), public_id=str(public_id), user_public_id=actor)
        bump_versions(db, set(rederived.changed_asset_ids) - {int(locked["id"])}, user_public_id=actor, at=at)
        if locked["origin_code"] != ORIGIN_PLATFORM:
            # A piece of kit is in no report, so its own values change nothing a preview is computed from.
            repo.bump_change_number(db)
        machine = get_machine(db, public_id, show_identity=show_identity)
        event = _asset_event(
            db,
            event_name=EQUIPMENT_EVENT_MACHINE_CAPABILITY_SET,
            machine=machine,
            user_public_id=user_public_id,
            payload={
                "own_capability_codes": sorted(value.capability_code for value in values),
                "removed_capability_codes": sorted(set(own_now) - {value.capability_code for value in values}),
            },
            reason="Machine's own capability values set.",
        )
        db.commit()
    return MachineActionResponse(machine=machine, event=event)


def _validated_correction(
    field_code: str, value: str, structure: EquipmentStructureResponse, models: ModelRecords
) -> str:
    """The corrected value in the form the transformer reads it: a class code, a model public id, a year,
    ACTIVE or INACTIVE, a plain figure, or text."""
    if field_code == CORRECTION_FIELD_CATEGORY:
        equipment_class = find_class(structure, code(value))
        if equipment_class is None or equipment_class.class_kind_code != CLASS_KIND_MACHINE or not equipment_class.is_active:
            raise EquipmentValidationError("Choose the class of machine this is.")
        return equipment_class.class_code
    if field_code == CORRECTION_FIELD_MODEL:
        model = models.by_public_id.get(value.strip().lower())
        if model is None:
            raise EquipmentValidationError("Choose a recorded model.")
        if model.is_retired:
            raise EquipmentValidationError(f"{model.label} is retired, so a machine cannot be newly given it.")
        if is_kit_class(find_class(structure, model.class_code)):
            raise EquipmentValidationError(f"{model.label} is a kit model: kit is recorded on the platform, never read from Plum.")
        return model.model_public_id
    if field_code == CORRECTION_FIELD_COMMENCED_YEAR:
        year = value.strip()
        if not (len(year) == 4 and year.isdigit() and EARLIEST_YEAR <= int(year) <= now().year + 1):
            raise EquipmentValidationError(f"Give the commenced year as four digits, from {EARLIEST_YEAR} to {now().year + 1}.")
        return year
    if field_code == CORRECTION_FIELD_STATUS:
        status = code(value)
        if status not in ("ACTIVE", "INACTIVE"):
            raise EquipmentValidationError("Status must be Active or Inactive.")
        return status
    if field_code == CORRECTION_FIELD_CAPACITY:
        figure = parse_number(value)
        if figure is None or figure <= 0 or figure.as_tuple().exponent < -3 or figure >= Decimal("1000000000"):
            raise EquipmentValidationError(
                "Give the capacity as a plain number in the unit Plum's category uses, with up to three decimals."
            )
        return str(figure)
    text = clean(value)
    if text is None or len(text) > TEXT_VALUE_MAX_LENGTH:
        raise EquipmentValidationError(f"Give the correct value, up to {TEXT_VALUE_MAX_LENGTH} characters.")
    return text


def _rederive(db: Session, *, asset_id: int, public_id: str, user_public_id: str | None) -> tuple[list[str], tuple[str, ...]]:
    """After a correction is recorded or closed: re-read the machine, then move its version on once - its
    record changed whatever the re-reading found - and the version of any asset at the other end of a link
    that closed. Returns the facts changed and the links closed."""
    result = rederive_asset(db, asset_id=asset_id, public_id=public_id, user_public_id=user_public_id)
    bump_versions(db, {asset_id, *result.changed_asset_ids}, user_public_id=user_public_id, at=now())
    return list(result.changed_facts), result.closed_link_public_ids


def record_correction(
    db: Session, *, public_id: UUID, payload: MachineCorrectionInput, user_public_id: str | None, show_identity: bool = False
) -> MachineActionResponse:
    """Correct one Plum field of one machine (design section 5B). It applies now and on every import,
    closes itself when Plum takes the corrected value, and is flagged when Plum changes to a third. A newer
    correction of the same field replaces the open one. The machine number cannot be corrected."""
    actor = require_user(user_public_id)
    field_code = code(payload.field_code) or ""
    if field_code not in CORRECTION_FIELDS:
        raise EquipmentValidationError(
            "That field cannot be corrected. The machine number is the key Plum and the platform share; a "
            "renumbered machine is flagged instead."
        )
    reason = required_reason(payload.reason, what="the correction")
    with rollback_on_error(db):
        begin_write(db)
        locked = _locked(db, public_id, payload.expected_asset_version)
        row = repo.get_asset_row(db, public_id=str(public_id))
        assert row is not None
        if row["source_values"] is None:
            raise EquipmentValidationError("This machine did not come from Plum, so there is no Plum value to correct.")
        structure = get_equipment_structure(db)
        models = load_models(db)
        corrected = _validated_correction(field_code, payload.corrected_value, structure, models)
        plum_value = plum_value_for_correction(row_from_values(0, row["source_values"]), field_code)
        if _plum_already_holds(field_code, plum_value, corrected):
            raise EquipmentValidationError("Plum already holds this value, so there is nothing to correct.")
        at = now()
        superseded = repo.find_open_correction(db, asset_id=int(locked["id"]), field_code=field_code)
        if superseded is not None:
            repo.close_correction(
                db, correction_id=int(superseded["id"]), reason_code=CLOSED_SUPERSEDED, user_public_id=actor, import_id=None, at=at
            )
        correction_public_id = str(uuid4())
        repo.insert_correction(
            db,
            values={
                "correction_public_id": correction_public_id,
                "equipment_asset_id": int(locked["id"]),
                "field_code": field_code,
                "plum_value": plum_value,
                "corrected_value": corrected,
                "reason": reason,
                "correction_status_code": STATUS_OPEN,
                "recorded_by": actor,
                "recorded_at": at,
            },
        )
        changed, closed = _rederive(
            db, asset_id=int(locked["id"]), public_id=str(public_id), user_public_id=actor
        )
        repo.bump_change_number(db)
        machine = get_machine(db, public_id, show_identity=show_identity)
        event = _asset_event(
            db,
            event_name=EQUIPMENT_EVENT_CORRECTION_RECORDED,
            machine=machine,
            user_public_id=actor,
            payload={
                "correction_public_id": correction_public_id,
                "field_code": field_code,
                "superseded_correction_public_id": str(superseded["correction_public_id"]) if superseded else None,
                "changed_facts": changed,
                "closed_link_public_ids": list(closed),
            },
            reason="Plum value corrected for one machine.",
        )
        db.commit()
    return MachineActionResponse(machine=machine, event=event)


def _plum_already_holds(field_code: str, plum_value: str | None, corrected: str) -> bool:
    if plum_value is None:
        return False
    if field_code == CORRECTION_FIELD_CAPACITY:
        return parse_number(plum_value) == parse_number(corrected)
    if field_code in (CORRECTION_FIELD_CATEGORY, CORRECTION_FIELD_MODEL):
        # Plum holds words, the correction a class or model: never the same thing.
        return False
    return normalize_term(plum_value) == normalize_term(corrected)


def close_correction(
    db: Session,
    *,
    public_id: UUID,
    correction_public_id: UUID,
    payload: MachineCorrectionCloseInput,
    user_public_id: str | None,
    show_identity: bool = False,
) -> MachineActionResponse:
    """The Fleet Admin closes a correction: the machine is read as Plum gives it again."""
    actor = require_user(user_public_id)
    with rollback_on_error(db):
        begin_write(db)
        locked = _locked(db, public_id, payload.expected_asset_version)
        correction = repo.get_correction_row(db, asset_id=int(locked["id"]), public_id=str(correction_public_id))
        if correction is None:
            raise EquipmentNotFoundError("Correction not found on this machine.")
        if correction["correction_status_code"] != STATUS_OPEN:
            raise EquipmentValidationError("This correction is already closed.")
        repo.close_correction(
            db, correction_id=int(correction["id"]), reason_code=CLOSED_BY_FLEET_ADMIN, user_public_id=actor, import_id=None, at=now()
        )
        changed, closed = _rederive(
            db, asset_id=int(locked["id"]), public_id=str(public_id), user_public_id=actor
        )
        repo.bump_change_number(db)
        machine = get_machine(db, public_id, show_identity=show_identity)
        event = _asset_event(
            db,
            event_name=EQUIPMENT_EVENT_CORRECTION_CLOSED,
            machine=machine,
            user_public_id=actor,
            payload={
                "correction_public_id": str(correction_public_id),
                "field_code": correction["field_code"],
                "closed_reason_code": CLOSED_BY_FLEET_ADMIN,
                "changed_facts": changed,
                "closed_link_public_ids": list(closed),
            },
            reason="Correction closed by the Fleet Admin.",
        )
        db.commit()
    return MachineActionResponse(machine=machine, event=event)


def _locked_part(db: Session, public_id: UUID, expected_version: int) -> dict[str, Any]:
    """The part a fit or removal changes, locked and guarded by the version the caller read, as the
    machine is (independent review, round 1, ERT1-R1-003)."""
    part_row = repo.lock_asset_row(db, public_id=str(public_id))
    if part_row is None:
        raise EquipmentNotFoundError("Part not found.")
    if int(part_row["asset_version"]) != expected_version:
        raise EquipmentConflictError("Someone else changed this part after you opened it. Reload to see their version.")
    return part_row


def _check_fit_date(value: date, *, what: str) -> None:
    # Today where PBL works, as the report date is judged.
    if value > business_time.india_today():
        raise EquipmentValidationError(f"The date {what} cannot be in the future.")


def fit_part(
    db: Session, *, public_id: UUID, payload: FitPartInput, user_public_id: str | None, show_identity: bool = False
) -> MachineActionResponse:
    """Fit a part to a machine - confirm a crane and its carrier as one machine (design Q6)."""
    actor = require_user(user_public_id)
    _check_fit_date(payload.fitted_on, what="it was fitted on")
    with rollback_on_error(db):
        begin_write(db)
        machine_row = _locked(db, public_id, payload.expected_asset_version)
        part_row = _locked_part(db, payload.part_public_id, payload.expected_part_version)
        structure = get_equipment_structure(db)
        check_can_fit(db, machine_row, part_row, structure)
        # A fitting never begins before the part's last removal, or the machine's last part of that class
        # came off: the history would show one part on two machines at once (ERT1-R4-004).
        earliest = repo.earliest_fitting_date(
            db, part_id=int(part_row["id"]), machine_id=int(machine_row["id"]), part_class_code=part_row["class_code"]
        )
        if earliest is not None and payload.fitted_on < earliest:
            raise EquipmentValidationError(
                f"It cannot be fitted before {earliest.isoformat()}: the part, or this machine's part of that kind, "
                "was removed on that day."
            )
        at = now()
        link_public_id = str(uuid4())
        repo.insert_link(
            db,
            public_id=link_public_id,
            parent_asset_id=int(machine_row["id"]),
            child_asset_id=int(part_row["id"]),
            fitted_on=payload.fitted_on,
            user_public_id=actor,
            at=at,
        )
        repo.delete_asset_flag(db, asset_id=int(part_row["id"]), flag_code=DATA_QUALITY_PART_NOT_FITTED)
        repo.update_asset(db, asset_id=int(machine_row["id"]), values={}, user_public_id=actor, at=at)
        repo.update_asset(db, asset_id=int(part_row["id"]), values={}, user_public_id=actor, at=at)
        repo.bump_change_number(db)
        machine = get_machine(db, public_id, show_identity=show_identity)
        event = _asset_event(
            db,
            event_name=EQUIPMENT_EVENT_PART_FITTED,
            machine=machine,
            user_public_id=actor,
            payload={
                "link_public_id": link_public_id,
                "part_asset_public_id": str(payload.part_public_id),
                "part_class_code": part_row["class_code"],
                "fitted_on": payload.fitted_on.isoformat(),
            },
            reason="Part fitted to a machine.",
        )
        db.commit()
    return MachineActionResponse(machine=machine, event=event)


def remove_part(
    db: Session,
    *,
    public_id: UUID,
    part_public_id: UUID,
    payload: RemovePartInput,
    user_public_id: str | None,
    show_identity: bool = False,
) -> MachineActionResponse:
    """Remove a part from its machine. The link keeps its history; the part is flagged as not fitted."""
    actor = require_user(user_public_id)
    _check_fit_date(payload.removed_on, what="it was removed on")
    with rollback_on_error(db):
        begin_write(db)
        machine_row = _locked(db, public_id, payload.expected_asset_version)
        part_row = _locked_part(db, part_public_id, payload.expected_part_version)
        link = next(
            (
                item
                for item in repo.list_open_links_of(db, asset_id=int(machine_row["id"]))
                if int(item["parent_asset_id"]) == int(machine_row["id"]) and int(item["child_asset_id"]) == int(part_row["id"])
            ),
            None,
        )
        if link is None:
            raise EquipmentValidationError("This part is not fitted to this machine.")
        if payload.removed_on < link["fitted_on"]:
            raise EquipmentValidationError("A part cannot be removed before the date it was fitted.")
        at = now()
        repo.close_link(db, link_id=int(link["id"]), removed_on=payload.removed_on, user_public_id=actor, at=at)
        repo.insert_asset_flag(
            db, asset_id=int(part_row["id"]), flag_code=DATA_QUALITY_PART_NOT_FITTED, subject_code="", import_id=None, at=at
        )
        repo.update_asset(db, asset_id=int(machine_row["id"]), values={}, user_public_id=actor, at=at)
        repo.update_asset(db, asset_id=int(part_row["id"]), values={}, user_public_id=actor, at=at)
        repo.bump_change_number(db)
        machine = get_machine(db, public_id, show_identity=show_identity)
        event = _asset_event(
            db,
            event_name=EQUIPMENT_EVENT_PART_REMOVED,
            machine=machine,
            user_public_id=actor,
            payload={
                "link_public_id": str(link["link_public_id"]),
                "part_asset_public_id": str(part_public_id),
                "removed_on": payload.removed_on.isoformat(),
            },
            reason="Part removed from a machine.",
        )
        db.commit()
    return MachineActionResponse(machine=machine, event=event)


# --- Detachable kit (ERT-2) --------------------------------------------------------------------------


def _summaries(db: Session, rows: list[dict[str, Any]]) -> list[MachineSummaryResponse]:
    return _build(db, rows, structure=get_equipment_structure(db), models=load_models(db), full=False)  # type: ignore[return-value]


def _replayed_lot(db: Session, rows: list[dict[str, Any]], key: str, fingerprint: str) -> KitAddResponse:
    """A repeated "add kit" returns the first lot and records nothing - only for the very same request, its kit model,
    count, number and year as sent included. Any other request with the key is refused, never answered with a lot it
    did not ask for (TB-1 TB1-102 part b, 8A's rule; it replaces ERT-2's comparison of the kit model alone). The
    fingerprint is the request as it was sent, so a piece later moved to another model does not change it
    (ERT2-R2-001)."""
    if not is_same_request(repo.get_create_request_fingerprint(db, create_request_key=key), fingerprint):
        raise EquipmentConflictError(KIT_KEY_USED)
    return KitAddResponse(pieces=_summaries(db, rows), replayed=True)


def add_kit(db: Session, *, payload: KitAddInput, user_public_id: str | None) -> KitAddResponse:
    """Pieces of one kit model, held for every machine of the crane models it fits (owner, Q6). A kind tracked
    one by one gets `count` records of one piece each - "add several alike" - and a counted kind one record of
    `count` pieces (Q3). Each request is one lot, recorded together: the same request with the same key again
    returns what the first made (ADR-023), and the key with any other request is refused. A piece is in no report,
    so this changes nothing a preview is computed from."""
    actor = require_user(user_public_id)
    key = str(payload.create_request_key)
    fingerprint = request_fingerprint(payload)
    existing = repo.list_assets_by_create_request_key(db, create_request_key=key)
    if existing:
        return _replayed_lot(db, existing, key, fingerprint)
    serial = clean(payload.serial_number)
    _check_year_of_manufacture(payload.year_of_manufacture)
    try:
        with rollback_on_error(db):
            begin_write(db)
            # Checked again under the lock: a second submission waiting on it finds the first's pieces.
            replayed = repo.list_assets_by_create_request_key(db, create_request_key=key)
            if replayed:
                db.rollback()
                return _replayed_lot(db, replayed, key, fingerprint)
            # The page it was added from, as that page showed it (ERT2-R1-001).
            machine = repo.lock_asset_row(db, public_id=str(payload.machine_public_id))
            if machine is None:
                raise EquipmentNotFoundError("Machine not found.")
            if int(machine["asset_version"]) != payload.expected_asset_version:
                raise EquipmentConflictError(STALE_MACHINE)
            model = repo.get_model_row(db, public_id=str(payload.kit_model_public_id))
            if model is None:
                raise EquipmentNotFoundError("Kit model not found.")
            if int(model["model_version"]) != payload.expected_model_version:
                raise EquipmentConflictError(STALE_KIT_MODEL)
            label = f"{model['maker']} {model['model_name']}"
            kit_class = find_class(get_equipment_structure(db), model["class_code"])
            if kit_class is None or not is_kit_class(kit_class):
                raise EquipmentValidationError(
                    f"{label} is not a kit model. Only kit is recorded on the platform: machines come from Plum's report."
                )
            if model["is_retired"]:
                raise EquipmentValidationError(f"{label} is retired, so pieces of it cannot be newly added.")
            fitted_models = {
                int(row["crane_model_id"])
                for row in repo.list_model_fit_rows(db, model_ids=[int(model["id"])])
                if int(row["kit_model_id"]) == int(model["id"])
            }
            if machine["equipment_model_id"] is None or int(machine["equipment_model_id"]) not in fitted_models:
                raise EquipmentValidationError(f"{label} does not fit this machine's model, so it is not added to its kit.")
            counted = kit_class.tracking_code == TRACKING_COUNTED
            if serial is not None and (counted or payload.count != 1):
                raise EquipmentValidationError(
                    "A piece's own number is given one piece at a time, and a counted set has none. Add the pieces, "
                    "then give each its number on its own page."
                )
            quantities = [payload.count] if counted else [1] * payload.count
            for position, quantity in enumerate(quantities, 1):
                repo.insert_asset(
                    db,
                    values={
                        "asset_public_id": str(uuid4()),
                        "asset_kind_code": ASSET_KIND_PART,
                        "origin_code": ORIGIN_PLATFORM,
                        "class_code": model["class_code"],
                        "type_code": model["type_code"],
                        "equipment_model_id": int(model["id"]),
                        "machine_number": None,
                        "asset_status_code": ASSET_STATUS_ACTIVE,
                        "serial_number": serial,
                        "year_of_manufacture": payload.year_of_manufacture,
                        "quantity": quantity,
                        "create_request_key": key,
                        "create_request_position": position,
                        "create_request_model_id": int(model["id"]),
                        "create_request_fingerprint": fingerprint,
                        "created_by": actor,
                        "updated_by": actor,
                    },
                )
            pieces = _summaries(db, repo.list_assets_by_create_request_key(db, create_request_key=key))
            events = [
                record_event(
                    db,
                    event_name=EQUIPMENT_EVENT_ASSET_REGISTERED,
                    record_type=RECORD_TYPE_ASSET,
                    record_public_id=str(piece.asset_public_id),
                    user_public_id=actor,
                    payload={
                        "asset_reference": piece.asset_reference,
                        "asset_version": piece.asset_version,
                        "origin_code": ORIGIN_PLATFORM,
                        "class_code": piece.class_code,
                        "model_public_id": str(model["model_public_id"]),
                        "quantity": piece.quantity,
                        "records_in_lot": len(pieces),
                    },
                    reason="Kit recorded on the platform.",
                    status_after=piece.asset_status_code,
                )
                for piece in pieces
            ]
            db.commit()
    except IntegrityError as exc:
        # Two submissions of one key raced; the other committed first. Replay it, or refuse another request.
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        if constraint != "uq_equipment_asset_create_request":
            raise
        existing = repo.list_assets_by_create_request_key(db, create_request_key=key)
        if not existing:
            raise
        return _replayed_lot(db, existing, key, fingerprint)
    return KitAddResponse(pieces=pieces, events=events)


def _refuse_shrinking_below_its_trips(
    db: Session, listings: KitListingSource, *, piece_public_id: str, remaining: int
) -> None:
    """A counted set may not shrink below what its trips list at once from today on (TB-1 finding TB1-307, 4 October
    2026): those listings are changed first. Retiring a whole set or piece stays allowed - its allocations then show it
    as retired and need replacing or freeing (8A design, from RMR-001)."""
    today = business_time.india_today()
    listed = listings.listed_from(db, piece_public_id=piece_public_id, from_day=today)
    if listed.most_at_once > remaining:
        raise EquipmentValidationError(
            f"Trips list {listed.most_at_once} of this set at once from today ({', '.join(listed.allocation_references)}), "
            f"so it cannot go down to {remaining}. List fewer on those trips first, or retire fewer pieces."
        )


def retire_piece(
    db: Session, *, public_id: UUID, payload: KitRetireInput, user_public_id: str | None, show_identity: bool = False
) -> MachineActionResponse:
    """Retire a piece of kit with the day and the reason - scrapped, lost, sold, recorded by mistake, or other
    with a note (owner, Q8 and Q14). From a counted set, `count` of its pieces may go: the set stays, smaller,
    and the event says how many left and why - the only way a set shrinks, so the Fixed Assets module will find
    every disposal dated and explained. A retired piece is never deleted and cannot be added to again; retiring
    it again returns it unchanged. Plum's machines retire only by Plum's report."""
    actor = require_user(user_public_id)
    reason_code = code(payload.reason_code) or ""
    if reason_code not in RETIREMENT_REASON_CODES:
        raise EquipmentValidationError("Choose why it was retired: scrapped, lost, sold, recorded by mistake, or other.")
    note = clean(payload.note)
    if reason_code == RETIREMENT_OTHER and note is None:
        raise EquipmentValidationError("Say why in the note: it is required with Other.")
    _check_fit_date(payload.retired_on, what="it was retired on")
    with rollback_on_error(db):
        # Resource Assignments' lock first, then this module's, then the piece's row (TB-1 finding TB1-307): the order
        # Eligibility's "seen" marks already take (allocations, then equipment), and the only one that cannot deadlock
        # with listing kit, which takes Resource Assignments' lock and then, through its foreign key, a share lock on
        # the piece's row.
        listings = kit_listing_source()
        listings.hold(db)
        begin_write(db)
        locked = repo.lock_asset_row(db, public_id=str(public_id))
        if locked is None:
            raise EquipmentNotFoundError("Machine not found.")
        if locked["origin_code"] != ORIGIN_PLATFORM:
            raise EquipmentValidationError("Plum retires this machine; correct its status if Plum is wrong.")
        if locked["asset_status_code"] == ASSET_STATUS_RETIRED:
            db.rollback()
            return MachineActionResponse(machine=get_machine(db, public_id, show_identity=show_identity), event=None)
        if int(locked["asset_version"]) != payload.expected_asset_version:
            raise EquipmentConflictError(STALE_MACHINE)
        held = int(locked["quantity"])
        count = payload.count if payload.count is not None else held
        if not 1 <= count <= held:
            raise EquipmentValidationError(f"This record holds {held} piece{'s' if held != 1 else ''}: retire between 1 and {held}.")
        whole = count == held
        if not whole:
            _refuse_shrinking_below_its_trips(db, listings, piece_public_id=str(public_id), remaining=held - count)
        values: dict[str, Any] = (
            {
                "asset_status_code": ASSET_STATUS_RETIRED,
                "retired_on": payload.retired_on,
                "retirement_reason_code": reason_code,
                "retirement_note": note,
            }
            if whole
            else {"quantity": held - count}
        )
        repo.update_asset(
            db,
            asset_id=int(locked["id"]),
            values=values,
            user_public_id=actor,
            at=now(),
            expected_version=payload.expected_asset_version,
        )
        machine = get_machine(db, public_id, show_identity=show_identity)
        event = _asset_event(
            db,
            event_name=EQUIPMENT_EVENT_ASSET_RETIRED,
            machine=machine,
            user_public_id=actor,
            payload={
                "reason_code": reason_code,
                "retired_on": payload.retired_on.isoformat(),
                "quantity_retired": count,
                "quantity_after": 0 if whole else held - count,
                "whole": whole,
            },
            # The note is free text: it goes in the event's reason, never its payload (design section 10).
            reason=note or ("Kit retired." if whole else "Pieces retired from a counted set."),
        )
        db.commit()
    return MachineActionResponse(machine=machine, event=event)


