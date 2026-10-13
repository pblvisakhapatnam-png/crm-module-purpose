"""Reading the Equipment Reference, and the lookups its consumers need (ADR-037, WRR-001).

Consumers read the structure only through this module. `get_equipment_structure` returns it whole;
the small helpers below answer the questions a consumer asks of it - is this class usable here, does
this type belong to it, does this capability apply - so that no consumer re-derives those rules from
the tables.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.modules.equipment_reference.contract import (
    ASSET_STATUS_ACTIVE,
    EQUIPMENT_UNITS,
    EQUIPMENT_UNITS_BY_CODE,
    FIT_KIND_KIT,
    normalize_term,
)
from app.modules.equipment_reference.repository import (
    current_component_depth,
    list_alias_rows,
    list_asset_fact_rows,
    list_capability_rows,
    list_class_business_line_rows,
    list_class_capability_rows,
    list_class_rows,
    list_open_fitted_link_pairs,
    list_part_fit_rows,
    list_taxonomy_version_rows,
    list_type_rows,
    take_write_lock,
)
from app.modules.equipment_reference.schemas import (
    EquipmentCapabilityResponse,
    EquipmentClassCapabilityResponse,
    EquipmentClassResponse,
    EquipmentStructureResponse,
    EquipmentTaxonomyVersionResponse,
    EquipmentTermAliasResponse,
    EquipmentTypeResponse,
    EquipmentUnitResponse,
)


def _is_active(row: dict) -> bool:
    return row.get("retired_in_version") is None


def get_equipment_structure(db: Session) -> EquipmentStructureResponse:
    versions = list_taxonomy_version_rows(db)
    if not versions:
        # The migration loads version 1, so this means the database is not the one the code expects.
        raise RuntimeError("The equipment structure has no version loaded.")

    capabilities = {row["capability_code"]: row for row in list_capability_rows(db)}
    lines_by_class: dict[str, list[str]] = {}
    for row in list_class_business_line_rows(db):
        if _is_active(row):
            lines_by_class.setdefault(row["class_code"], []).append(row["business_line_code"])
    types_by_class: dict[str, list[EquipmentTypeResponse]] = {}
    for row in list_type_rows(db):
        types_by_class.setdefault(row["class_code"], []).append(
            EquipmentTypeResponse(
                type_code=row["type_code"],
                type_label=row["type_label"],
                display_order=row["display_order"],
                introduced_in_version=row["introduced_in_version"],
                retired_in_version=row["retired_in_version"],
                is_active=_is_active(row),
            )
        )
    # A part class lists the classes it may be fitted to (structure version 2, ERT-1), and a kind of kit the
    # machine classes it is kit for (version 3, ERT-2). The two are kept apart: kit is never fitted.
    fits_by_class: dict[str, list[str]] = {}
    kit_for_by_class: dict[str, list[str]] = {}
    for row in list_part_fit_rows(db):
        if _is_active(row):
            target = kit_for_by_class if row["fit_kind_code"] == FIT_KIND_KIT else fits_by_class
            target.setdefault(row["part_class_code"], []).append(row["parent_class_code"])
    capabilities_by_class: dict[str, list[EquipmentClassCapabilityResponse]] = {}
    for row in list_class_capability_rows(db):
        capability = capabilities[row["capability_code"]]
        unit = EQUIPMENT_UNITS_BY_CODE.get(capability["unit_code"]) if capability["unit_code"] else None
        capabilities_by_class.setdefault(row["class_code"], []).append(
            EquipmentClassCapabilityResponse(
                capability_code=row["capability_code"],
                capability_label=capability["capability_label"],
                unit_code=capability["unit_code"],
                unit_symbol=unit.unit_symbol if unit else None,
                whole_numbers_only=bool(unit and unit.whole_numbers_only),
                value_kind_code=capability["value_kind_code"],
                allowed_values=list(capability["allowed_values"]) if capability["allowed_values"] else None,
                is_key=bool(row["is_key"]),
                display_order=row["display_order"],
                # Usable only while both the capability and its link to this class are live.
                is_active=_is_active(row) and _is_active(capability),
            )
        )

    current = max(versions, key=lambda row: int(row["version_number"]))
    return EquipmentStructureResponse(
        taxonomy_version=int(current["version_number"]),
        component_depth=int(current["component_depth"]),
        versions=[EquipmentTaxonomyVersionResponse(**row) for row in versions],
        units=[EquipmentUnitResponse(**unit.__dict__) for unit in EQUIPMENT_UNITS],
        classes=[
            EquipmentClassResponse(
                class_code=row["class_code"],
                class_label=row["class_label"],
                class_kind_code=row["class_kind_code"],
                tracking_code=row["tracking_code"],
                fits_class_codes=fits_by_class.get(row["class_code"], []),
                kit_for_class_codes=kit_for_by_class.get(row["class_code"], []),
                display_order=row["display_order"],
                business_line_codes=lines_by_class.get(row["class_code"], []),
                introduced_in_version=row["introduced_in_version"],
                retired_in_version=row["retired_in_version"],
                is_active=_is_active(row),
                types=types_by_class.get(row["class_code"], []),
                capabilities=capabilities_by_class.get(row["class_code"], []),
            )
            for row in list_class_rows(db)
        ],
        capabilities=[
            EquipmentCapabilityResponse(
                capability_code=row["capability_code"],
                capability_label=row["capability_label"],
                unit_code=row["unit_code"],
                value_kind_code=row["value_kind_code"],
                allowed_values=list(row["allowed_values"]) if row["allowed_values"] else None,
                introduced_in_version=row["introduced_in_version"],
                retired_in_version=row["retired_in_version"],
                is_active=_is_active(row),
            )
            for row in capabilities.values()
        ],
        aliases=[
            EquipmentTermAliasResponse(
                term=row["term"],
                normalized_term=row["normalized_term"],
                source_code=row["source_code"],
                class_code=row["class_code"],
                type_code=row["type_code"],
                is_active=_is_active(row),
            )
            for row in list_alias_rows(db)
        ],
    )


# --- Lookups ---------------------------------------------------------------------------------------


def find_class(structure: EquipmentStructureResponse, class_code: str | None) -> EquipmentClassResponse | None:
    return next((item for item in structure.classes if item.class_code == class_code), None)


def find_type(equipment_class: EquipmentClassResponse, type_code: str | None) -> EquipmentTypeResponse | None:
    return next((item for item in equipment_class.types if item.type_code == type_code), None)


def find_class_capability(
    equipment_class: EquipmentClassResponse, capability_code: str | None
) -> EquipmentClassCapabilityResponse | None:
    return next((item for item in equipment_class.capabilities if item.capability_code == capability_code), None)


def key_capability(equipment_class: EquipmentClassResponse) -> EquipmentClassCapabilityResponse | None:
    """The live capability planners compare first, or None where the class has none (a generator)."""
    return next((item for item in equipment_class.capabilities if item.is_key and item.is_active), None)


def class_is_usable_by(equipment_class: EquipmentClassResponse, business_line_code: str) -> bool:
    return equipment_class.is_active and business_line_code in equipment_class.business_line_codes


def is_kit_class(equipment_class: EquipmentClassResponse | None) -> bool:
    """A kind of kit: kit for some machine class, held for the models it fits and never fitted (ERT-2)."""
    return bool(equipment_class and equipment_class.kit_for_class_codes)


# --- Assets with their fitted parts (ELG-1) -------------------------------------------------------------


@dataclass(frozen=True)
class AssetFacts:
    """An asset as a consumer needs it: its identity, what it is and whether it is in use. A piece of kit has
    no machine number; its own number (`serial_number`) is what is marked on it (ERT-2, Q5)."""

    asset_public_id: str
    asset_reference: str
    asset_kind_code: str
    origin_code: str
    class_code: str
    type_code: str | None
    machine_number: str | None
    serial_number: str | None
    asset_status_code: str
    asset_version: int
    # The day the asset was added to the Equipment Master, in Asia/Kolkata: when its papers became needed (ELG-2).
    added_on: date


@dataclass(frozen=True)
class AssetWithFittedParts:
    asset: AssetFacts
    # Every part fitted below it through open fitted links, down to the depth setting, each with the public id
    # of the asset it is fitted to, nearest first.
    fitted_parts: tuple[tuple[AssetFacts, str], ...]
    # The asset it is itself fitted to, if any.
    fitted_to: AssetFacts | None


def _asset_facts(row: dict) -> AssetFacts:
    return AssetFacts(**{field: row[field] for field in AssetFacts.__dataclass_fields__})


def _with_fitted_parts(
    asset: AssetFacts, facts: dict[str, AssetFacts], children: dict[str, list[str]], parents: dict[str, str], depth: int
) -> AssetWithFittedParts:
    fitted: list[tuple[AssetFacts, str]] = []
    level = [asset.asset_public_id]
    # A tree no deeper than the depth setting: its links were each checked against it when made (ERT-2).
    for _ in range(max(depth - 1, 0)):
        level = [child for parent in level for child in children.get(parent, [])]
        fitted.extend((facts[child], parents[child]) for child in level if child in facts)
        if not level:
            break
    parent = parents.get(asset.asset_public_id)
    return AssetWithFittedParts(asset, tuple(fitted), facts.get(parent) if parent else None)


def _link_maps(db: Session) -> tuple[dict[str, list[str]], dict[str, str]]:
    children: dict[str, list[str]] = {}
    parents: dict[str, str] = {}
    for row in list_open_fitted_link_pairs(db):
        children.setdefault(row["parent_public_id"], []).append(row["child_public_id"])
        parents[row["child_public_id"]] = row["parent_public_id"]
    return children, parents


def get_asset_with_fitted_parts(db: Session, public_id: str) -> AssetWithFittedParts | None:
    """One asset - a machine, a fitted part or a piece of kit - with the parts fitted below it and what it is
    fitted to. Eligibility judges a machine with its fitted parts (ELG-1, section 6)."""
    children, parents = _link_maps(db)
    wanted = {public_id, *children.get(public_id, [])}
    # The whole chain below, however deep, and the asset above.
    frontier = list(children.get(public_id, []))
    while frontier:
        frontier = [child for parent in frontier for child in children.get(parent, []) if child not in wanted]
        wanted.update(frontier)
    if public_id in parents:
        wanted.add(parents[public_id])
    facts = {row["asset_public_id"]: _asset_facts(row) for row in list_asset_fact_rows(db, public_ids=sorted(wanted))}
    if public_id not in facts:
        return None
    return _with_fitted_parts(facts[public_id], facts, children, parents, current_component_depth(db))


def hold_equipment_writes(db: Session) -> None:
    """Take this module's write lock in the caller's transaction, without writing: Eligibility marks its reminders
    seen under it, so an asset retired, or a part fitted or removed, meanwhile is seen - or waits (ELG-2). Every write
    here takes the same lock; none takes another module's after it."""
    take_write_lock(db)


def list_active_assets_with_fitted_parts(db: Session) -> list[AssetWithFittedParts]:
    """Every active asset, each with the parts fitted below it: what Eligibility's renewal list is worked out
    over. A fitted part appears on its own too, and below its machine."""
    children, parents = _link_maps(db)
    facts = {row["asset_public_id"]: _asset_facts(row) for row in list_asset_fact_rows(db)}
    depth = current_component_depth(db)
    return [
        _with_fitted_parts(asset, facts, children, parents, depth)
        for asset in facts.values()
        if asset.asset_status_code == ASSET_STATUS_ACTIVE
    ]


# --- Machines and kit for allocation (8A core) ----------------------------------------------------------------


@dataclass(frozen=True)
class AllocationCapability:
    """One capability of a machine or piece, with the value it has: its own value where the Fleet Admin set one,
    otherwise its model's rating (ERT-1)."""

    capability_code: str
    capability_label: str
    unit_symbol: str | None
    value_kind_code: str
    is_key: bool
    value: Decimal | None
    choice_value: str | None


@dataclass(frozen=True)
class AllocationAsset:
    """A machine or a piece of kit as allocation needs it: identity, kind, model, status, version and the
    capabilities that have a value. A capability with no value is left out: unknown is never a value."""

    asset_public_id: str
    asset_reference: str
    asset_kind_code: str
    origin_code: str
    machine_number: str | None
    serial_number: str | None
    class_code: str
    class_label: str
    type_code: str | None
    type_label: str | None
    model_public_id: str | None
    model_label: str | None
    asset_status_code: str
    asset_version: int
    quantity: int
    tracking_code: str
    capabilities: tuple[AllocationCapability, ...]
    flag_codes: tuple[str, ...]

    def capability(self, capability_code: str) -> AllocationCapability | None:
        return next((item for item in self.capabilities if item.capability_code == capability_code), None)

    def key_capability(self) -> AllocationCapability | None:
        return next((item for item in self.capabilities if item.is_key), None)


def machines_for_allocation(db: Session, *, class_code: str) -> list[AllocationAsset]:
    """Every active machine of a class, with its capabilities: what a requirement's machines are found among."""
    # services/ builds on this module, so it is imported where it is used rather than at the top.
    from app.modules.equipment_reference.services.machines import allocation_assets

    return allocation_assets(db, kind_code="MACHINE", class_code=class_code, status_code=ASSET_STATUS_ACTIVE)


def allocation_asset(db: Session, public_id: str) -> AllocationAsset | None:
    """One machine or piece of kit, whatever its status; None when there is no such asset."""
    from app.modules.equipment_reference.services.machines import allocation_assets

    found = allocation_assets(db, public_id=public_id)
    return found[0] if found else None


def kit_for_machine(db: Session, machine_public_id: str) -> list[AllocationAsset]:
    """The active pieces of every kit model that fits the machine's model (ERT-2): what may go to site with it.
    Nothing for a machine with no model yet."""
    from app.modules.equipment_reference.services.machines import allocation_assets

    machine = allocation_asset(db, machine_public_id)
    if machine is None or machine.model_public_id is None:
        return []
    return allocation_assets(db, fits_model_public_id=machine.model_public_id, status_code=ASSET_STATUS_ACTIVE)


def asset_references(db: Session, public_ids: list[str]) -> dict[str, str]:
    """Each asset's `EQ-` reference by its public id, for consumers naming what a record is about (8A core)."""
    if not public_ids:
        return {}
    return {row["asset_public_id"]: row["asset_reference"] for row in list_asset_fact_rows(db, public_ids=sorted(set(public_ids)))}


@dataclass(frozen=True)
class EquipmentSuggestion:
    class_code: str
    type_code: str | None
    # The word that matched, as written in the structure: a class label or an alias term.
    matched_term: str


def suggest_equipment_class(
    structure: EquipmentStructureResponse, value: str | None, *, business_line_code: str
) -> EquipmentSuggestion | None:
    """A class, and a type where the word names one, for free text such as a line's category ("Crane").

    Only a live class the business line uses is suggested. A whole match on a class label or alias wins;
    failing that, a class label or alias appearing as whole words inside the text ("250MT Crane") is
    used, but only when every such match points at the same class - two candidates is no suggestion.
    A type is suggested only when every match agrees on it. Advice only: the user chooses.
    """
    normalized = normalize_term(value)
    if not normalized:
        return None

    usable = {item.class_code: item for item in structure.classes if class_is_usable_by(item, business_line_code)}
    candidates: list[tuple[str, str, str | None, str]] = [
        (normalize_term(item.class_label), item.class_code, None, item.class_label) for item in usable.values()
    ]
    candidates.extend(
        (alias.normalized_term, alias.class_code, alias.type_code, alias.term)
        for alias in structure.aliases
        if alias.is_active and alias.class_code in usable
    )

    exact = [candidate for candidate in candidates if candidate[0] == normalized]
    if exact:
        return _agreed_suggestion(exact, usable)
    contained = [
        candidate for candidate in candidates if re.search(rf"(?<![A-Z0-9]){re.escape(candidate[0])}(?![A-Z0-9])", normalized)
    ]
    return _agreed_suggestion(contained, usable) if contained else None


def _agreed_suggestion(
    matches: list[tuple[str, str, str | None, str]], usable: dict[str, EquipmentClassResponse]
) -> EquipmentSuggestion | None:
    class_codes = {match[1] for match in matches}
    if len(class_codes) != 1:
        return None
    class_code = class_codes.pop()
    type_codes = {match[2] for match in matches}
    type_code = type_codes.pop() if len(type_codes) == 1 else None
    if type_code is not None:
        equipment_type = find_type(usable[class_code], type_code)
        if equipment_type is None or not equipment_type.is_active:
            type_code = None
    return EquipmentSuggestion(class_code=class_code, type_code=type_code, matched_term=matches[0][3])
