"""What more than one Equipment Reference concern uses (ERT-1): the module's errors, the write lock,
events, capability values, the context a report is read against, and writing a machine's derived facts.

Every write in the module takes one lock (`begin_write`) for its whole transaction, and every change to
anything a preview is computed from increases the change count, so a preview made before it is refused at
confirmation (design section 5, step 10).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.modules.authorization.contract import EQUIPMENT_IDENTITY_READ
from app.modules.authorization.service import has_permission
from app.modules.equipment_reference import repository as repo
from app.modules.equipment_reference.contract import (
    ALIAS_SOURCE_PLUM_CATEGORY,
    ASSET_KIND_MACHINE,
    ASSET_KIND_PART,
    ASSET_STATUS_ACTIVE,
    CORRECTION_FIELD_CATEGORY,
    CORRECTION_FIELD_MODEL,
    CORRECTION_FIELD_STATUS,
    EQUIPMENT_EVENT_PART_REMOVED,
    EQUIPMENT_REFERENCE_MODULE_NAME,
    IDENTITY_FIELDS,
    REASON_MAX_LENGTH,
    RECORD_TYPE_ASSET,
    REPORT_LEVEL_FLAG_CODES,
    VALUE_KIND_CHOICE,
    normalize_term,
)
from app.modules.equipment_reference.plum_report import (
    COMPARED_FACTS,
    CapabilityInfo,
    CategoryRule,
    ClassInfo,
    Correction,
    DerivedFacts,
    KnownAsset,
    ModelInfo,
    TransformContext,
    ValueRule,
    rederive_known,
)
from app.modules.equipment_reference.schemas import (
    CapabilityValueInput,
    CapabilityValueResponse,
    EquipmentClassResponse,
    EquipmentStructureResponse,
)
from app.modules.equipment_reference.service import (
    find_class,
    find_class_capability,
    get_equipment_structure,
    is_kit_class,
)
from app.modules.events.service import record_business_event
from app.modules.identity.schemas import AuthUser
from app.shared import business_time


class EquipmentNotFoundError(LookupError):
    pass


class EquipmentValidationError(ValueError):
    pass


class EquipmentConflictError(ValueError):
    """Someone changed the record after the caller read it, a preview is out of date, or a request key or
    report was already used."""


def now() -> datetime:
    return datetime.now(timezone.utc)


def clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def code(value: str | None) -> str | None:
    cleaned = clean(value)
    return cleaned.upper() if cleaned else None


def required_reason(value: str | None, *, what: str) -> str:
    reason = clean(value)
    if reason is None:
        raise EquipmentValidationError(f"Give the reason for {what}.")
    if len(reason) > REASON_MAX_LENGTH:
        raise EquipmentValidationError(f"Keep the reason to {REASON_MAX_LENGTH} characters.")
    return reason


def require_user(user_public_id: str | None) -> str:
    """Who acted is part of every record here; a route reaches the service only with a signed-in user, so
    this is the backstop, not the control."""
    if not user_public_id:
        raise EquipmentValidationError("The signed-in user could not be identified, so nothing was recorded.")
    return user_public_id


def begin_write(db: Session) -> None:
    """Take the module's write lock for the rest of the transaction."""
    repo.take_write_lock(db)


def record_event(
    db: Session,
    *,
    event_name: str,
    record_type: str,
    record_public_id: str,
    user_public_id: str | None,
    payload: dict[str, Any],
    reason: str,
    status_before: str | None = None,
    status_after: str | None = None,
) -> dict[str, Any]:
    """Payloads carry public ids, codes, versions, counts and dates only: no machine, engine or chassis
    number, no Plum value, no reason text (design section 11)."""
    event = record_business_event(
        db,
        event_name=event_name,
        source_module=EQUIPMENT_REFERENCE_MODULE_NAME,
        record_type=record_type,
        record_public_id=record_public_id,
        user_public_id=user_public_id,
        status_before=status_before,
        status_after=status_after,
        reason=reason,
        event_payload=payload,
    )
    return event.model_dump(mode="json")


# --- Capability values -----------------------------------------------------------------------------


@dataclass(frozen=True)
class CapabilityValue:
    capability_code: str
    value: Decimal | None
    choice_value: str | None
    reason: str | None = None


def normalize_capability_values(
    inputs: Iterable[CapabilityValueInput],
    equipment_class: EquipmentClassResponse,
    *,
    kept_codes: frozenset[str] = frozenset(),
    with_reason: bool = False,
) -> list[CapabilityValue]:
    """Check values against the class's capabilities: each applies to the class and is live (or was already
    saved with this record), fits its kind, is whole where it is counted, and is given once."""
    values: list[CapabilityValue] = []
    seen: set[str] = set()
    for item in inputs:
        capability_code = code(item.capability_code) or ""
        applies = find_class_capability(equipment_class, capability_code)
        if applies is None:
            raise EquipmentValidationError(
                f"{capability_code or 'That capability'} does not describe a {equipment_class.class_label}. Use only "
                "the capabilities listed for the class."
            )
        if capability_code not in kept_codes and not applies.is_active:
            raise EquipmentValidationError(f"{applies.capability_label} has been retired, so it cannot be given.")
        if capability_code in seen:
            raise EquipmentValidationError(f"{applies.capability_label} is given twice. Give each capability once.")
        seen.add(capability_code)
        if applies.value_kind_code == VALUE_KIND_CHOICE:
            choice = code(item.choice_value)
            if item.value is not None or choice is None or choice not in (applies.allowed_values or []):
                raise EquipmentValidationError(
                    f"Choose the {applies.capability_label.lower()} from its list: {', '.join(applies.allowed_values or [])}."
                )
            value, choice_value = None, choice
        else:
            unit = f" in {applies.unit_symbol}" if applies.unit_symbol else ""
            if item.choice_value is not None or item.value is None:
                raise EquipmentValidationError(f"Give the {applies.capability_label.lower()}{unit} as a number.")
            if applies.whole_numbers_only and item.value != item.value.to_integral_value():
                raise EquipmentValidationError(f"{applies.capability_label} is counted in whole numbers.")
            value, choice_value = item.value, None
        reason = None
        if with_reason:
            reason = required_reason(getattr(item, "reason", None), what=f"the machine's own {applies.capability_label.lower()}")
        values.append(CapabilityValue(capability_code, value, choice_value, reason))
    return values


def capability_responses(
    values: dict[str, tuple[Decimal | None, str | None]], equipment_class: EquipmentClassResponse | None
) -> list[CapabilityValueResponse]:
    """Values in the order the class lists its capabilities."""
    order = {item.capability_code: item.display_order for item in (equipment_class.capabilities if equipment_class else [])}
    responses: list[CapabilityValueResponse] = []
    for capability_code, (value, choice) in values.items():
        applies = find_class_capability(equipment_class, capability_code) if equipment_class else None
        responses.append(
            CapabilityValueResponse(
                capability_code=capability_code,
                capability_label=applies.capability_label if applies else capability_code,
                unit_code=applies.unit_code if applies else None,
                unit_symbol=applies.unit_symbol if applies else None,
                value_kind_code=applies.value_kind_code if applies else "MINIMUM",
                is_key=bool(applies and applies.is_key),
                value=value,
                choice_value=choice,
            )
        )
    responses.sort(key=lambda item: order.get(item.capability_code, 0))
    return responses


# --- Models, as the transformer and the screens read them ------------------------------------------


@dataclass(frozen=True)
class ModelRecords:
    by_public_id: dict[str, ModelInfo]
    id_by_public_id: dict[str, int]
    public_id_by_id: dict[int, str]


def load_models(db: Session) -> ModelRecords:
    rows = repo.list_model_rows(db)
    capabilities: dict[int, dict[str, Decimal | str]] = {}
    for row in repo.list_model_capability_rows(db):
        value = row["capability_value"] if row["capability_value"] is not None else row["choice_value"]
        capabilities.setdefault(int(row["equipment_model_id"]), {})[row["capability_code"]] = value
    by_public_id: dict[str, ModelInfo] = {}
    for row in rows:
        by_public_id[str(row["model_public_id"])] = ModelInfo(
            model_public_id=str(row["model_public_id"]),
            maker=row["maker"],
            model_name=row["model_name"],
            class_code=row["class_code"],
            type_code=row["type_code"],
            is_retired=bool(row["is_retired"]),
            capabilities=capabilities.get(int(row["id"]), {}),
        )
    return ModelRecords(
        by_public_id=by_public_id,
        id_by_public_id={str(row["model_public_id"]): int(row["id"]) for row in rows},
        public_id_by_id={int(row["id"]): str(row["model_public_id"]) for row in rows},
    )


def load_model_mappings(db: Session) -> dict[str, str]:
    """Plum model names, in the Python normalized form the transformer matches in, to a model public id."""
    return {normalize_term(row["source_name"]): str(row["model_public_id"]) for row in repo.list_model_mapping_rows(db)}


def load_category_rules(db: Session) -> dict[str, CategoryRule]:
    return {
        normalize_term(row["category_term"]): CategoryRule(
            normalized_category=normalize_term(row["category_term"]),
            class_code=row["class_code"],
            capability_code=row["capability_code"],
            plum_unit_code=row["plum_unit_code"],
            plausible_low=row["plausible_low"],
            plausible_high=row["plausible_high"],
            check_code=row["check_code"],
        )
        for row in repo.list_category_rule_rows(db)
    }


def load_value_rules(db: Session) -> tuple[ValueRule, ...]:
    return tuple(
        ValueRule(
            rule_public_id=str(row["rule_public_id"]),
            column_code=row["column_code"],
            plum_value=row["plum_value"],
            action_code=row["action_code"],
            result_number=row["result_number"],
            result_unit_code=row["result_unit_code"],
            result_class_code=row["result_class_code"],
            result_type_code=row["result_type_code"],
        )
        for row in repo.list_value_rule_rows(db, open_only=True)
    )


def known_assets(db: Session, models: ModelRecords, asset_rows: list[dict[str, Any]] | None = None) -> list[tuple[dict[str, Any], KnownAsset]]:
    """The Plum-bound assets, each with what a report is compared with: its facts, its own capability
    values, its open corrections, and what it is fitted to or carries."""
    rows = asset_rows if asset_rows is not None else repo.list_plum_bound_asset_rows(db)
    own: dict[int, dict[str, Decimal | str]] = {}
    for row in repo.list_all_asset_capability_rows(db):
        value = row["capability_value"] if row["capability_value"] is not None else row["choice_value"]
        own.setdefault(int(row["equipment_asset_id"]), {})[row["capability_code"]] = value
    corrections: dict[int, list[Correction]] = {}
    for row in repo.list_all_open_correction_rows(db):
        corrections.setdefault(int(row["equipment_asset_id"]), []).append(
            Correction(str(row["correction_public_id"]), row["field_code"], row["plum_value"], row["corrected_value"])
        )
    fitted_to: dict[int, str] = {}
    carries: dict[int, set[str]] = {}
    for row in repo.list_open_link_rows(db):
        fitted_to[int(row["child_asset_id"])] = str(row["parent_public_id"])
        carries.setdefault(int(row["parent_asset_id"]), set()).add(row["child_class_code"])
    result: list[tuple[dict[str, Any], KnownAsset]] = []
    for row in rows:
        asset_id = int(row["id"])
        result.append(
            (
                row,
                KnownAsset(
                    asset_public_id=str(row["asset_public_id"]),
                    asset_reference=row["asset_reference"],
                    machine_number=row["provider_key"] or row["machine_number"],
                    kind_code=row["asset_kind_code"],
                    class_code=row["class_code"],
                    type_code=row["type_code"],
                    model_public_id=str(row["model_public_id"]) if row["model_public_id"] else None,
                    engine_number=row["engine_number"],
                    chassis_number=row["chassis_number"],
                    commenced_year=row["commenced_year"],
                    owning_company=row["owning_company"],
                    status_code=row["asset_status_code"],
                    own_capabilities=own.get(asset_id, {}),
                    corrections=tuple(corrections.get(asset_id, [])),
                    fitted_to_public_id=fitted_to.get(asset_id),
                    fitted_part_class_codes=frozenset(carries.get(asset_id, set())),
                ),
            )
        )
    return result


def transform_context(
    db: Session,
    *,
    report_year: int,
    structure: EquipmentStructureResponse | None = None,
    models: ModelRecords | None = None,
    known: list[tuple[dict[str, Any], KnownAsset]] | None = None,
) -> TransformContext:
    """Everything a report is read against, as the platform holds it now."""
    structure = structure or get_equipment_structure(db)
    models = models or load_models(db)
    known = known if known is not None else known_assets(db, models)
    classes = {
        item.class_code: ClassInfo(
            class_code=item.class_code,
            class_label=item.class_label,
            kind_code=item.class_kind_code,
            business_line_codes=tuple(item.business_line_codes) if item.is_active else (),
            type_codes=frozenset(equipment_type.type_code for equipment_type in item.types),
            capability_codes=frozenset(capability.capability_code for capability in item.capabilities),
        )
        for item in structure.classes
    }
    return TransformContext(
        classes=classes,
        capabilities={item.capability_code: CapabilityInfo(item.capability_code, item.unit_code) for item in structure.capabilities},
        category_aliases={
            normalize_term(alias.term): (alias.class_code, alias.type_code)
            for alias in structure.aliases
            if alias.source_code == ALIAS_SOURCE_PLUM_CATEGORY and alias.is_active
        },
        part_fits=frozenset(
            (item.class_code, parent) for item in structure.classes for parent in item.fits_class_codes
        ),
        models=models.by_public_id,
        model_mappings=load_model_mappings(db),
        category_rules=load_category_rules(db),
        value_rules=load_value_rules(db),
        known_assets=tuple(asset for _, asset in known),
        report_year=report_year,
    )


# --- Labels ----------------------------------------------------------------------------------------


def corrected_value_label(
    field_code: str, value: str, structure: EquipmentStructureResponse, models: dict[str, ModelInfo]
) -> str:
    """A corrected value as the Fleet Admin reads it: a class or model by name, a status in words."""
    if field_code == CORRECTION_FIELD_CATEGORY:
        found = find_class(structure, value)
        return found.class_label if found else value
    if field_code == CORRECTION_FIELD_MODEL:
        model = models.get(value)
        return model.label if model else value
    if field_code == CORRECTION_FIELD_STATUS:
        return {"ACTIVE": "Active", "INACTIVE": "Inactive"}.get(value, value)
    return value


def can_see_identity_numbers(db: Session, user: AuthUser) -> bool:
    """Whether the signed-in user may see engine and chassis numbers: EQUIPMENT_IDENTITY_READ, Admin only
    for now (owner, 25 September 2026). Resolved here rather than in a route, which never reads roles, as
    the documents module resolves its own rights (documents/service.py)."""
    return has_permission(db, user.role_codes, EQUIPMENT_IDENTITY_READ)


def correction_values(
    item: dict[str, Any], structure: EquipmentStructureResponse, models: ModelRecords, *, show_identity: bool
) -> dict[str, Any]:
    """A correction's Plum value, corrected value and reason, as the caller may see them: an engine or
    chassis number's are withheld without EQUIPMENT_IDENTITY_READ (owner, 25 September 2026). The reason goes
    with the values: written by Admin, it may well repeat the numbers (independent review, round 2,
    ERT1-R2-002)."""
    if item["field_code"] in IDENTITY_FIELDS and not show_identity:
        return {"plum_value": None, "corrected_value": None, "corrected_value_label": None, "values_withheld": True, "reason": None}
    return {
        "reason": item["reason"],
        "plum_value": item["plum_value"],
        "corrected_value": item["corrected_value"],
        "corrected_value_label": corrected_value_label(item["field_code"], item["corrected_value"], structure, models.by_public_id),
        "values_withheld": False,
    }


# --- Fitting a part ------------------------------------------------------------------------------------


def check_can_fit(
    db: Session, machine_row: dict[str, Any], part_row: dict[str, Any], structure: EquipmentStructureResponse
) -> None:
    """The rules a pair keeps wherever it is confirmed - on a machine's page or with a report: a part whose
    class the structure fits, by a dated link, to the other's class - a machine's, or a part's within the
    depth setting (ERT-2) - fitted nowhere else, and one part of that class on each. Both must be active: a
    retired part is not fitted anew. Kit is never fitted: it is held for the crane models it fits (ERT-2)."""
    part_class = find_class(structure, part_row["class_code"])
    if part_row["asset_kind_code"] != ASSET_KIND_PART:
        raise EquipmentValidationError("Only a part can be fitted to a machine.")
    if is_kit_class(part_class) and not (part_class and part_class.fits_class_codes):
        raise EquipmentValidationError(
            "Kit is not fitted to a machine: it is held for the crane models it fits, and shared by every crane of them."
        )
    parent_takes_parts = machine_row["asset_kind_code"] == ASSET_KIND_MACHINE or any(
        machine_row["class_code"] in item.fits_class_codes for item in structure.classes
    )
    if not parent_takes_parts:
        raise EquipmentValidationError("Parts are fitted to a machine, and this is not one.")
    if machine_row["asset_status_code"] != ASSET_STATUS_ACTIVE:
        raise EquipmentValidationError("This machine is retired, so a part cannot be fitted to it.")
    if part_row["asset_status_code"] != ASSET_STATUS_ACTIVE:
        raise EquipmentValidationError("This part is retired, so it cannot be fitted.")
    if part_class is None or machine_row["class_code"] not in part_class.fits_class_codes:
        machine_class = find_class(structure, machine_row["class_code"])
        raise EquipmentValidationError(
            f"A {part_class.class_label.lower() if part_class else part_row['class_code']} is not fitted to a "
            f"{machine_class.class_label.lower() if machine_class else machine_row['class_code']}."
        )
    for link in repo.list_open_links_of(db, asset_id=int(part_row["id"])):
        if int(link["child_asset_id"]) == int(part_row["id"]):
            raise EquipmentValidationError("This part is already fitted to a machine. Remove it from that machine first.")
    for link in repo.list_open_links_of(db, asset_id=int(machine_row["id"])):
        if int(link["parent_asset_id"]) == int(machine_row["id"]) and link["child_class_code"] == part_row["class_code"]:
            raise EquipmentValidationError(f"This machine already has a {part_class.class_label.lower()} fitted. Remove it first.")
    # The depth setting (owner, Q9): the parent's level and everything that hangs below the part, together.
    depth = repo.current_component_depth(db)
    levels = repo.asset_level(db, asset_id=int(machine_row["id"])) + repo.subtree_height(db, asset_id=int(part_row["id"]))
    if levels > depth:
        raise EquipmentValidationError(
            f"Parts nest at most {depth} levels deep, the machine being the first; fitting this one would make {levels}."
        )


# --- Writing a machine's facts ------------------------------------------------------------------------

_FACT_COLUMNS = {
    "kind_code": "asset_kind_code",
    "class_code": "class_code",
    "type_code": "type_code",
    "engine_number": "engine_number",
    "chassis_number": "chassis_number",
    "commenced_year": "commenced_year",
    "owning_company": "owning_company",
    "status_code": "asset_status_code",
}


@dataclass(frozen=True)
class WrittenFacts:
    changed_facts: tuple[str, ...]
    closed_link_public_ids: tuple[str, ...]
    removed_capability_codes: tuple[str, ...]
    # The assets at the other end of the links a change of kind closed: they changed too.
    other_linked_asset_ids: tuple[int, ...] = ()


def write_derived_facts(
    db: Session,
    *,
    asset_id: int,
    current: KnownAsset,
    facts: DerivedFacts,
    models: ModelRecords,
    user_public_id: str | None,
    at: datetime,
    removal_date: date,
    reconcile_links: bool = True,
) -> WrittenFacts:
    """Make an asset's Plum facts, class, type and model what the transformer derived. After a change of
    kind or class, every link the asset is in is checked again by the rules a pair is fitted by - a machine
    and a part, of a class that fits it - and each that no longer holds is closed, dated `removal_date`, with
    its own event (independent review, round 2, ERT1-R2-003). A confirmed report passes
    `reconcile_links=False`: it closes the links its preview showed closing, before any row is written
    (ERT1-R3-001). A change of class removes the machine's own values the new class does not take.

    Versions are not moved here: the caller moves each asset's version on exactly once, after everything it
    changes on it (independent review, round 1, ERT1-R1-004)."""
    changed = tuple(name for name in COMPARED_FACTS if getattr(current, name) != getattr(facts, name))
    if not changed:
        return WrittenFacts((), (), ())
    closed: list[str] = []
    others: list[int] = []
    if reconcile_links and ("kind_code" in changed or "class_code" in changed):
        structure = get_equipment_structure(db)
        for link in repo.list_open_links_of(db, asset_id=asset_id):
            if _still_fits(link, asset_id=asset_id, facts=facts, structure=structure):
                continue
            close_fitted_link(
                db,
                link=link,
                removal_date=removal_date,
                because="KIND_CHANGED" if "kind_code" in changed else "CLASS_CHANGED",
                user_public_id=user_public_id,
                at=at,
            )
            closed.append(str(link["link_public_id"]))
            others.append(int(link["child_asset_id"]) if int(link["parent_asset_id"]) == asset_id else int(link["parent_asset_id"]))
    removed: list[str] = []
    if "class_code" in changed:
        removed = repo.delete_asset_capabilities_not_of_class(db, asset_id=asset_id, class_code=facts.class_code)
    values: dict[str, Any] = {_FACT_COLUMNS[name]: getattr(facts, name) for name in _FACT_COLUMNS}
    values["equipment_model_id"] = models.id_by_public_id.get(facts.model_public_id) if facts.model_public_id else None
    repo.update_asset(db, asset_id=asset_id, values=values, user_public_id=user_public_id, at=at, bump_version=False)
    return WrittenFacts(changed, tuple(closed), tuple(removed), tuple(others))


def close_fitted_link(
    db: Session, *, link: dict[str, Any], removal_date: date, because: str, user_public_id: str | None, at: datetime
) -> date:
    """Close a link the two ends of which no longer fit together, and record it on the machine. It is dated
    `removal_date` - the report's date, or today - but never before the day the part was fitted: an older
    report closes it on that day (independent review, round 3, ERT1-R3-005; ck_equipment_asset_link_removal).
    Returns the date used."""
    removed_on = max(removal_date, link["fitted_on"])
    repo.close_link(db, link_id=int(link["id"]), removed_on=removed_on, user_public_id=require_user(user_public_id), at=at)
    record_event(
        db,
        event_name=EQUIPMENT_EVENT_PART_REMOVED,
        record_type=RECORD_TYPE_ASSET,
        record_public_id=str(link["parent_public_id"]),
        user_public_id=user_public_id,
        payload={
            "link_public_id": str(link["link_public_id"]),
            "part_asset_public_id": str(link["child_public_id"]),
            "removed_on": removed_on.isoformat(),
            "because": because,
        },
        reason="A part was removed from its machine because the two no longer fit together.",
    )
    return removed_on


def _still_fits(link: dict[str, Any], *, asset_id: int, facts: DerivedFacts, structure: EquipmentStructureResponse) -> bool:
    """Whether a link still holds once the asset takes its new kind and class: the part end a part, and the
    part's class one the structure fits to the other end's class (the structural rules of `check_can_fit`;
    the other end is a machine, or a part within the depth setting)."""
    as_parent = int(link["parent_asset_id"]) == asset_id
    parent_class = facts.class_code if as_parent else link["parent_class_code"]
    part_kind, part_class = (link["child_kind_code"], link["child_class_code"]) if as_parent else (facts.kind_code, facts.class_code)
    part_info = find_class(structure, part_class)
    return part_kind == ASSET_KIND_PART and part_info is not None and parent_class in part_info.fits_class_codes


def bump_versions(db: Session, asset_ids: Iterable[int], *, user_public_id: str | None, at: datetime) -> None:
    """Move each asset's version on once: the record changed, so a draft made against the old one is stale."""
    for asset_id in sorted(set(asset_ids)):
        repo.update_asset(db, asset_id=asset_id, values={}, user_public_id=user_public_id, at=at)


@dataclass(frozen=True)
class Rederived:
    changed_facts: tuple[str, ...]
    closed_link_public_ids: tuple[str, ...]
    flags_changed: bool
    # Every asset this changed, the other ends of any closed links included.
    changed_asset_ids: tuple[int, ...]


def rederive_asset(db: Session, *, asset_id: int, public_id: str, user_public_id: str | None) -> Rederived:
    """Re-read one machine from the values its latest report gave, with its corrections and own values as
    they now stand, and with the models, mappings and rules as they now stand - what the next report would
    make of it - then write its facts and the flags its own row raises (flags a whole report raises are left
    as they are, apart from PART_NOT_FITTED, set again at once for it and for the other end of any link it
    left). Versions are not moved here: the caller moves them once, with `changed_asset_ids`. An asset with
    no Plum source has nothing to re-read."""
    row = repo.get_asset_row(db, public_id=public_id)
    if row is None or row["source_values"] is None:
        return Rederived((), (), False, ())
    models = load_models(db)
    (_, known), = known_assets(db, models, asset_rows=[row])
    report_year = row["facts_report_date"].year if row["facts_report_date"] else now().year
    ctx = transform_context(db, report_year=report_year, models=models, known=[])
    derived = rederive_known(row["source_values"], known, ctx)
    at = now()
    written = WrittenFacts((), (), ())
    if derived.facts is not None:
        written = write_derived_facts(
            db,
            asset_id=asset_id,
            current=known,
            facts=derived.facts,
            models=models,
            user_public_id=user_public_id,
            at=at,
            # Today where PBL works, as a fitting date is judged.
            removal_date=business_time.india_today(),
        )
    flags_changed = repo.set_asset_flags(
        db,
        asset_id=asset_id,
        flags={(flag.flag_code, flag.subject_code) for flag in derived.flags},
        keep_codes=REPORT_LEVEL_FLAG_CODES,
        import_id=None,
        at=at,
    )
    refitted = repo.sync_part_not_fitted(db, asset_ids={asset_id, *written.other_linked_asset_ids}, at=at)
    flags_changed = flags_changed or asset_id in refitted
    changed_ids = ((asset_id,) if written.changed_facts or flags_changed else ()) + written.other_linked_asset_ids
    changed_ids += tuple(sorted(refitted - set(changed_ids)))
    return Rederived(written.changed_facts, written.closed_link_public_ids, flags_changed, changed_ids)
