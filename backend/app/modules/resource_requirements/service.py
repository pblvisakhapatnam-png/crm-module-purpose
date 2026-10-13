"""Resource Requirements: record, change and cancel what a Work Order line needs on site (WRR-001).

Design: docs/agent/slices/wrr-001-resource-requirement-foundation.md. In short:

- A requirement belongs to one Work Order line; a line may have several (Q7). Nothing is created
  automatically, and a line without one is not reported as missing (Q1).
- It asks for a number of units over a period. Each unit is one item - an equipment class, an optional
  type and the least capabilities - taken from the platform's Equipment Reference; exactly one item in
  this slice (Q15), and only a class Hiring deploys.
- Its dates must sit inside the contract (and outside its gaps) and inside the line's own dates when
  saved. A bound not recorded is never treated as broken. Afterwards a change to the contract only
  raises a warning (Q8).
- Crew numbers start from the Work Order's Part 4 numbers in force when the requirement starts, and a
  difference is shown, never refused (Q4). They are never pay terms.
- Work Order facts are read live through the `work_orders` service - never its repository or tables -
  and no rate, amount or commercial term is copied (WRR-001).
- 8A core: which units are covered by machines held for a requirement is Assignment's to know, read through
  `ports.AssignmentPort`, which Assignment registers; this module never imports it. The status follows it -
  OPEN, PARTLY_FULFILLED, FULFILLED - and cancelling a requirement frees its held machines through the same
  port, in the cancellation's transaction (WRR-001).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.equipment_reference.schemas import EquipmentClassResponse, EquipmentStructureResponse
from app.modules.equipment_reference.service import (
    class_is_usable_by,
    find_class,
    find_class_capability,
    find_type,
    get_equipment_structure,
    key_capability,
    suggest_equipment_class,
)
from app.modules.events.service import record_business_event
from app.modules.resource_requirements.contract import (
    ITEMS_PER_REQUIREMENT_THIS_SLICE,
    NEEDS_MACHINES_STATUS_CODES,
    PRIORITY_CODES,
    PRIORITY_NORMAL,
    REQUIREMENT_BUSINESS_LINE,
    REQUIREMENT_COMPARED_FIELDS,
    REQUIREMENT_LIVE_STATUS_CODES,
    REQUIREMENT_STATUS_CANCELLED,
    REQUIREMENT_STATUS_CODES,
    REQUIREMENT_STATUS_FULFILLED,
    REQUIREMENT_STATUS_OPEN,
    REQUIREMENT_STATUS_PARTLY_FULFILLED,
    RESOURCE_REQUIREMENT_EVENT_CANCELLED,
    RESOURCE_REQUIREMENT_EVENT_CREATED,
    RESOURCE_REQUIREMENT_EVENT_FULFILMENT_CHANGED,
    RESOURCE_REQUIREMENT_EVENT_UPDATED,
    STATUS_FILTER_NEEDS_MACHINES,
    RESOURCE_REQUIREMENT_MODULE_NAME,
    RESOURCE_REQUIREMENT_RECORD_TYPE,
    WARNING_CREW_DIFFERS_FROM_WORK_ORDER,
    WARNING_KEY_CAPABILITY_NOT_STATED,
    WARNING_OUTSIDE_CONTRACT,
    WARNING_SITE_NOT_RECORDED,
)
from app.modules.resource_requirements.repository import (
    cancel_requirement,
    count_requirements_for_line,
    delete_items,
    find_requirement_by_create_request_key,
    get_requirement_row,
    insert_item,
    insert_item_capability,
    insert_requirement,
    list_item_capability_rows,
    list_item_rows,
    list_requirement_rows,
    lock_open_ended_live_rows_of_work_order,
    lock_requirement_row,
    set_requirement_status,
    update_requirement,
)
from app.modules.resource_requirements.ports import Coverage, NO_COVERAGE, RequirementToCover, assignment_port
from app.modules.resource_requirements.schemas import (
    ResourceRequirementActionResponse,
    ResourceRequirementCancel,
    ResourceRequirementCapabilityResponse,
    ResourceRequirementContractGap,
    ResourceRequirementCreate,
    ResourceRequirementDefaultsResponse,
    ResourceRequirementFields,
    ResourceRequirementItemInput,
    ResourceRequirementItemResponse,
    ResourceRequirementLineFacts,
    ResourceRequirementResponse,
    ResourceRequirementSite,
    ResourceRequirementSuggestedValues,
    ResourceRequirementUpdate,
)
from app.modules.work_orders.contract import (
    WORK_ORDER_LINE_BILLING_TERM_NONE,
    WORK_ORDER_LINE_CREW_STATED,
    WORK_ORDER_LINE_SHIFTS_PER_DAY,
    WORK_ORDER_STATUS_CLOSED,
)
from app.modules.work_orders.contract_period_rules import (
    CONTRACT_DATE_OUTSIDE_OUTCOMES,
    ContractGap,
    classify_date_against_contract,
    date_outside_contract_message,
    format_contract_date,
)
from app.modules.work_orders.schemas import (
    WorkOrderContractPeriodResponse,
    WorkOrderLineBillingTermPeriodResponse,
    WorkOrderLineBillingTermsResponse,
    WorkOrderLineDetailResponse,
    WorkOrderLineReference,
    WorkOrderLineResponse,
)
from app.modules.work_orders.service import (
    WorkOrderLineNotFoundError,
    get_work_order,
    get_work_order_contract_period,
    get_work_order_line_reference,
    list_work_order_billing_terms,
    list_work_order_line_details,
    hold_work_order_status,
    list_work_order_lines,
    register_end_dates_listener,
)
from app.shared.request_keys import is_same_request, request_fingerprint
from app.shared.transactions import rollback_on_error


class ResourceRequirementNotFoundError(LookupError):
    pass


class ResourceRequirementLineNotFoundError(LookupError):
    """The Work Order line named does not exist, or is not on the Work Order named with it."""


class ResourceRequirementValidationError(ValueError):
    pass


class ResourceRequirementConflictError(ValueError):
    """Someone else changed the requirement after the caller read it, or a request key was reused."""


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _code(value: str | None) -> str | None:
    cleaned = _clean(value)
    return cleaned.upper() if cleaned else None


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --- The Work Order, read through its own service --------------------------------------------------


@dataclass(frozen=True)
class _WorkOrderView:
    """Everything a requirement needs from one Work Order, read once per request."""

    status_code: str
    lines: dict[str, WorkOrderLineResponse]
    details: dict[str, WorkOrderLineDetailResponse]
    terms: dict[str, WorkOrderLineBillingTermsResponse]
    contract: WorkOrderContractPeriodResponse


def _read_work_order(db: Session, work_order_public_id: UUID | str) -> _WorkOrderView:
    public_id = UUID(str(work_order_public_id))
    work_order = get_work_order(db, public_id)
    return _WorkOrderView(
        status_code=work_order.work_order_status_code,
        lines={str(line.public_id): line for line in list_work_order_lines(db, public_id)},
        details={str(item.work_order_line_public_id): item for item in list_work_order_line_details(db, public_id)},
        terms={str(item.work_order_line_public_id): item for item in list_work_order_billing_terms(db, public_id)},
        contract=get_work_order_contract_period(db, public_id),
    )


def _terms_in_force(
    terms: WorkOrderLineBillingTermsResponse | None, on: date | None
) -> WorkOrderLineBillingTermPeriodResponse | None:
    """The line's billing-terms period in force on a date: the latest one started by then (period 1 has
    no date of its own - it starts with the contract). With no date, the period in force today."""
    if terms is None or not terms.periods:
        return None
    if on is None:
        return next((period for period in terms.periods if period.period_number == terms.current_period_number), None)
    in_force: WorkOrderLineBillingTermPeriodResponse | None = None
    for period in sorted(terms.periods, key=lambda item: item.period_number):
        if period.effective_from is None or period.effective_from <= on:
            in_force = period
    return in_force


def _line_facts(view: _WorkOrderView, line_public_id: str, on: date | None) -> ResourceRequirementLineFacts:
    line = view.lines[line_public_id]
    detail = view.details.get(line_public_id)
    period = _terms_in_force(view.terms.get(line_public_id), on)
    site = detail.site_address if detail else None
    return ResourceRequirementLineFacts(
        work_order_status_code=view.status_code,
        scope_description=line.scope_description,
        equipment_service_category=line.equipment_service_category,
        quantity=line.quantity,
        uom=line.uom,
        site=(
            ResourceRequirementSite(
                public_id=site.public_id,
                address_line1=site.address_line1,
                city=site.city,
                state=site.state,
                postal_code=site.postal_code,
            )
            if site
            else None
        ),
        line_start_date=detail.line_start_date if detail else None,
        line_end_date=detail.line_end_date if detail else None,
        contract_start_date=view.contract.contract_start_date,
        contract_end_basis_code=view.contract.contract_end_basis_code,
        contract_end_date=view.contract.contract_end_date,
        contract_gaps=[
            ResourceRequirementContractGap(
                first_day=gap.first_day, last_day=gap.last_day, extension_sequence_no=gap.extension_sequence_no
            )
            for gap in view.contract.gaps
        ],
        billing_terms_period_number=period.period_number if period else None,
        billing_uom_code=period.billing_uom_code if period else None,
        # Slice 7D Part 5: how many shifts a day the Work Order states, where it was "night shift charged";
        # none when it states none ("not in the Work Order") or it is not recorded yet.
        shifts_per_day=WORK_ORDER_LINE_SHIFTS_PER_DAY.get(period.shift_pattern_code) if period is not None else None,
        work_order_crew_code=period.crew_code if period else None,
        work_order_crew_operators=period.crew_operators_per_unit if period else None,
        work_order_crew_helpers=period.crew_helpers_per_unit if period else None,
        site_central_government=detail.site_central_government if detail else None,
    )


def requirement_planned_end(required_to: date | None, facts: ResourceRequirementLineFacts) -> date | None:
    """The last day a requirement's machines are needed (8A core): its own end, else its line's, else the
    contract's fixed end; None when nothing bounds it (a contract until the work is complete, or not recorded)."""
    return required_to or facts.line_end_date or facts.contract_end_date


def _contract_gaps(facts: ResourceRequirementLineFacts) -> tuple[ContractGap, ...]:
    """The contract's gaps in the form the Slice 7D Part 3 rules take."""
    return tuple(
        ContractGap(first_day=gap.first_day, last_day=gap.last_day, extension_sequence_no=gap.extension_sequence_no)
        for gap in facts.contract_gaps
    )


def _work_order_crew(facts: ResourceRequirementLineFacts) -> tuple[int, int] | None:
    """The Work Order's operators and helpers, or None where its crew term is not answered. Equipment
    only (NONE) is an answer: no crew. A stated crew with a number still blank is not an answer yet -
    Part 4 reports that number missing - so it is never read as zero."""
    if facts.work_order_crew_code == WORK_ORDER_LINE_BILLING_TERM_NONE:
        return 0, 0
    if (
        facts.work_order_crew_code == WORK_ORDER_LINE_CREW_STATED
        and facts.work_order_crew_operators is not None
        and facts.work_order_crew_helpers is not None
    ):
        return facts.work_order_crew_operators, facts.work_order_crew_helpers
    return None


# --- Validation ------------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Capability:
    capability_code: str
    minimum_value: Decimal | None
    choice_value: str | None


@dataclass(frozen=True)
class _Item:
    equipment_class_code: str
    equipment_type_code: str | None
    equipment_specification: str | None
    capabilities: tuple[_Capability, ...]

    def comparable(self) -> tuple[Any, ...]:
        return (
            self.equipment_class_code,
            self.equipment_type_code,
            self.equipment_specification,
            tuple(sorted((cap.capability_code, cap.minimum_value, cap.choice_value) for cap in self.capabilities)),
        )


def _normalize_items(
    items: list[ResourceRequirementItemInput],
    structure: EquipmentStructureResponse,
    *,
    kept: _Item | None = None,
) -> list[_Item]:
    """Check the items against the Equipment Reference and return storable values.

    `kept` is the item already saved on a requirement being changed. A class, type or capability retired
    since it was saved may stay on it - anything saved with a retired code keeps it (design section 4) -
    but may not be newly chosen.
    """
    if not items:
        raise ResourceRequirementValidationError(
            "Say what equipment is needed: a requirement asks for one kind of equipment."
        )
    if len(items) > ITEMS_PER_REQUIREMENT_THIS_SLICE:
        raise ResourceRequirementValidationError(
            "A requirement asks for one kind of equipment. Record another requirement on the line for a "
            "second kind."
        )
    return [_normalize_item(item, structure, kept=kept) for item in items]


def _normalize_item(
    item: ResourceRequirementItemInput, structure: EquipmentStructureResponse, *, kept: _Item | None
) -> _Item:
    class_code = _code(item.equipment_class_code) or ""
    equipment_class = find_class(structure, class_code)
    if equipment_class is None:
        raise ResourceRequirementValidationError(f"{class_code or 'That'} is not an equipment class in the structure.")
    keeps_class = kept is not None and kept.equipment_class_code == class_code
    if not keeps_class and not equipment_class.is_active:
        raise ResourceRequirementValidationError(
            f"The class {equipment_class.class_label} has been retired, so it cannot be chosen for a requirement."
        )
    if not keeps_class and not class_is_usable_by(equipment_class, REQUIREMENT_BUSINESS_LINE):
        raise ResourceRequirementValidationError(
            f"{equipment_class.class_label} is not equipment Hiring provides, so a Work Order requirement cannot "
            "ask for it."
        )

    type_code = _code(item.equipment_type_code)
    if type_code is not None:
        equipment_type = find_type(equipment_class, type_code)
        if equipment_type is None:
            raise ResourceRequirementValidationError(
                f"{type_code} is not a type of {equipment_class.class_label}."
            )
        keeps_type = keeps_class and kept is not None and kept.equipment_type_code == type_code
        if not keeps_type and not equipment_type.is_active:
            raise ResourceRequirementValidationError(
                f"The type {equipment_type.type_label} has been retired, so it cannot be chosen for a requirement."
            )

    kept_capabilities = {cap.capability_code for cap in kept.capabilities} if keeps_class and kept else set()
    capabilities: list[_Capability] = []
    seen: set[str] = set()
    for capability in item.capabilities:
        normalized = _normalize_capability(capability, equipment_class, kept_codes=kept_capabilities)
        if normalized.capability_code in seen:
            raise ResourceRequirementValidationError(
                f"{_capability_label(equipment_class, normalized.capability_code)} is given twice. Give each "
                "capability once."
            )
        seen.add(normalized.capability_code)
        capabilities.append(normalized)

    return _Item(
        equipment_class_code=class_code,
        equipment_type_code=type_code,
        equipment_specification=_clean(item.equipment_specification),
        capabilities=tuple(capabilities),
    )


def _capability_label(equipment_class: EquipmentClassResponse, capability_code: str) -> str:
    found = find_class_capability(equipment_class, capability_code)
    return found.capability_label if found else capability_code


def _normalize_capability(capability: Any, equipment_class: EquipmentClassResponse, *, kept_codes: set[str]) -> _Capability:
    code = _code(capability.capability_code) or ""
    applies = find_class_capability(equipment_class, code)
    if applies is None:
        raise ResourceRequirementValidationError(
            f"{code or 'That capability'} does not describe a {equipment_class.class_label}. Use only the "
            "capabilities listed for the class."
        )
    if code not in kept_codes and not applies.is_active:
        raise ResourceRequirementValidationError(
            f"{applies.capability_label} has been retired, so it cannot be stated for a requirement."
        )

    if applies.value_kind_code == "CHOICE":
        choice = _code(capability.choice_value)
        if capability.minimum_value is not None or choice is None:
            raise ResourceRequirementValidationError(
                f"Choose the {applies.capability_label.lower()} from its list: "
                f"{', '.join(applies.allowed_values or [])}."
            )
        if choice not in (applies.allowed_values or []):
            raise ResourceRequirementValidationError(
                f"{applies.capability_label} must be one of {', '.join(applies.allowed_values or [])}."
            )
        return _Capability(capability_code=code, minimum_value=None, choice_value=choice)

    unit = f" in {applies.unit_symbol}" if applies.unit_symbol else ""
    if capability.choice_value is not None or capability.minimum_value is None:
        raise ResourceRequirementValidationError(
            f"Give the least {applies.capability_label.lower()}{unit} as a number."
        )
    value = capability.minimum_value
    if applies.whole_numbers_only and value != value.to_integral_value():
        raise ResourceRequirementValidationError(f"{applies.capability_label} is counted in whole numbers.")
    return _Capability(capability_code=code, minimum_value=value, choice_value=None)


def _normalize_fields(
    payload: ResourceRequirementFields, structure: EquipmentStructureResponse, *, kept: _Item | None = None
) -> tuple[dict[str, Any], list[_Item]]:
    priority = _code(payload.priority_code) or PRIORITY_NORMAL
    if priority not in PRIORITY_CODES:
        raise ResourceRequirementValidationError("Priority must be Normal or Urgent.")
    if payload.required_to is not None and payload.required_to < payload.required_from:
        raise ResourceRequirementValidationError(
            f"This requirement cannot end on {format_contract_date(payload.required_to)}, "
            f"before it starts on {format_contract_date(payload.required_from)}."
        )
    values = {
        "units_required": payload.units_required,
        "required_from": payload.required_from,
        "required_to": payload.required_to,
        "crew_operators_required": payload.crew_operators_required,
        "crew_helpers_required": payload.crew_helpers_required,
        "crew_notes": _clean(payload.crew_notes),
        "priority_code": priority,
        "planning_notes": _clean(payload.planning_notes),
    }
    return values, _normalize_items(payload.items, structure, kept=kept)


def _check_dates_on_save(values: dict[str, Any], facts: ResourceRequirementLineFacts, *, line_number: int) -> None:
    """The dates must sit inside the contract, outside its gaps, and inside the line's own dates (Q8).

    Only a recorded bound can be broken: the rule answers NOT_DETERMINED where one is missing, and that
    is never a refusal. Each refusal names the dates, as Slice 7D Part 3's do.
    """
    gaps = _contract_gaps(facts)
    required_from: date = values["required_from"]
    required_to: date | None = values["required_to"]
    for value, subject in ((required_from, "This requirement starts on"), (required_to, "This requirement ends on")):
        if value is None:
            continue
        message = date_outside_contract_message(
            value,
            contract_start=facts.contract_start_date,
            contract_end=facts.contract_end_date,
            subject=subject,
            gaps=gaps,
        )
        if message is not None:
            raise ResourceRequirementValidationError(message)

    line_start, line_end = facts.line_start_date, facts.line_end_date
    if line_start is not None and required_from < line_start:
        raise ResourceRequirementValidationError(
            f"This requirement starts on {format_contract_date(required_from)}, "
            f"before line {line_number} starts on {format_contract_date(line_start)}."
        )
    if line_end is not None and required_from > line_end:
        raise ResourceRequirementValidationError(
            f"This requirement starts on {format_contract_date(required_from)}, "
            f"after line {line_number} ends on {format_contract_date(line_end)}."
        )
    if line_end is not None and required_to is not None and required_to > line_end:
        raise ResourceRequirementValidationError(
            f"This requirement ends on {format_contract_date(required_to)}, "
            f"after line {line_number} ends on {format_contract_date(line_end)}."
        )


def _hold_work_order_open(db: Session, work_order_public_id: UUID | str) -> None:
    """Every requirement write first takes the Work Order's row, shared, and reads its status there (8A core,
    independent review round 3, 8A-R3-001): a change to the Work Order - its closure included - waits for the write
    or is seen by it. The order every write keeps: Work Order, requirement, allocations, Eligibility."""
    _refuse_closed(hold_work_order_status(db, work_order_public_id))


def _work_order_of(db: Session, public_id: UUID | str) -> str:
    """A requirement's Work Order, read without a lock: it never changes, and its lock comes first."""
    row = get_requirement_row(db, public_id=str(public_id))
    if row is None:
        raise ResourceRequirementNotFoundError("Resource requirement not found.")
    return str(row["work_order_public_id"])


def _refuse_closed(status_code: str) -> None:
    if status_code == WORK_ORDER_STATUS_CLOSED:
        raise ResourceRequirementValidationError(
            "This Work Order is closed. Its resource requirements can no longer be recorded or changed."
        )


# --- Warnings --------------------------------------------------------------------------------------


def _dates_outside(response_dates: tuple[date, date | None], facts: ResourceRequirementLineFacts) -> bool:
    required_from, required_to = response_dates
    gaps = _contract_gaps(facts)
    for value in (required_from, required_to):
        if value is None:
            continue
        outcome = classify_date_against_contract(
            value, contract_start=facts.contract_start_date, contract_end=facts.contract_end_date, gaps=gaps
        )
        if outcome in CONTRACT_DATE_OUTSIDE_OUTCOMES:
            return True
    if facts.line_start_date is not None and required_from < facts.line_start_date:
        return True
    if facts.line_end_date is not None:
        if required_from > facts.line_end_date:
            return True
        if required_to is not None and required_to > facts.line_end_date:
            return True
    return False


def _warnings(
    *,
    status_code: str,
    dates: tuple[date, date | None],
    crew: tuple[int, int],
    items: list[ResourceRequirementItemResponse],
    facts: ResourceRequirementLineFacts,
    structure: EquipmentStructureResponse,
) -> list[str]:
    """What planning should look at, computed now. Not for a cancelled requirement, which needs no attention.
    Never a refusal."""
    if status_code == REQUIREMENT_STATUS_CANCELLED:
        return []
    warnings: list[str] = []
    if facts.site is None:
        warnings.append(WARNING_SITE_NOT_RECORDED)
    if _dates_outside(dates, facts):
        warnings.append(WARNING_OUTSIDE_CONTRACT)
    work_order_crew = _work_order_crew(facts)
    if work_order_crew is not None and work_order_crew != crew:
        warnings.append(WARNING_CREW_DIFFERS_FROM_WORK_ORDER)
    for item in items:
        equipment_class = find_class(structure, item.equipment_class_code)
        key = key_capability(equipment_class) if equipment_class else None
        stated = {capability.capability_code for capability in item.capabilities}
        if key is not None and key.capability_code not in stated:
            warnings.append(WARNING_KEY_CAPABILITY_NOT_STATED)
            break
    return warnings


# --- Reading requirements --------------------------------------------------------------------------


def _item_responses(
    item_rows: list[dict[str, Any]],
    capability_rows: dict[int, list[dict[str, Any]]],
    structure: EquipmentStructureResponse,
) -> list[ResourceRequirementItemResponse]:
    responses: list[ResourceRequirementItemResponse] = []
    for row in item_rows:
        equipment_class = find_class(structure, row["equipment_class_code"])
        equipment_type = (
            find_type(equipment_class, row["equipment_type_code"])
            if equipment_class and row["equipment_type_code"]
            else None
        )
        capabilities: list[ResourceRequirementCapabilityResponse] = []
        for capability_row in capability_rows.get(int(row["id"]), []):
            applies = find_class_capability(equipment_class, capability_row["capability_code"]) if equipment_class else None
            capabilities.append(
                ResourceRequirementCapabilityResponse(
                    capability_code=capability_row["capability_code"],
                    capability_label=applies.capability_label if applies else capability_row["capability_code"],
                    unit_code=applies.unit_code if applies else None,
                    unit_symbol=applies.unit_symbol if applies else None,
                    value_kind_code=applies.value_kind_code if applies else "MINIMUM",
                    is_key=bool(applies and applies.is_key),
                    minimum_value=capability_row["minimum_value"],
                    choice_value=capability_row["choice_value"],
                )
            )
        order = {item.capability_code: item.display_order for item in (equipment_class.capabilities if equipment_class else [])}
        capabilities.sort(key=lambda item: order.get(item.capability_code, 0))
        responses.append(
            ResourceRequirementItemResponse(
                item_number=row["item_number"],
                equipment_class_code=row["equipment_class_code"],
                equipment_class_label=equipment_class.class_label if equipment_class else row["equipment_class_code"],
                equipment_type_code=row["equipment_type_code"],
                equipment_type_label=equipment_type.type_label if equipment_type else None,
                equipment_specification=row["equipment_specification"],
                capabilities=capabilities,
            )
        )
    return responses


def _build_responses(
    db: Session,
    rows: list[dict[str, Any]],
    *,
    structure: EquipmentStructureResponse | None = None,
    views: dict[str, _WorkOrderView] | None = None,
) -> list[ResourceRequirementResponse]:
    """One serializer for every route. Items and capabilities are read in two statements for the whole
    page, and each Work Order is read once however many of its requirements the page holds."""
    if not rows:
        return []
    structure = structure or get_equipment_structure(db)
    views = views if views is not None else {}
    item_rows = list_item_rows(db, requirement_ids=[int(row["id"]) for row in rows])
    capability_rows: dict[int, list[dict[str, Any]]] = {}
    for capability_row in list_item_capability_rows(db, item_ids=[int(row["id"]) for row in item_rows]):
        capability_rows.setdefault(int(capability_row["resource_requirement_item_id"]), []).append(capability_row)
    items_by_requirement: dict[int, list[dict[str, Any]]] = {}
    for item_row in item_rows:
        items_by_requirement.setdefault(int(item_row["resource_requirement_id"]), []).append(item_row)

    facts_by_id: dict[int, ResourceRequirementLineFacts] = {}
    for row in rows:
        work_order_public_id = str(row["work_order_public_id"])
        if work_order_public_id not in views:
            views[work_order_public_id] = _read_work_order(db, work_order_public_id)
        facts_by_id[int(row["id"])] = _line_facts(
            views[work_order_public_id], str(row["work_order_line_public_id"]), row["required_from"]
        )
    coverage = _coverage(db, rows, facts_by_id)

    responses: list[ResourceRequirementResponse] = []
    for row in rows:
        facts = facts_by_id[int(row["id"])]
        covered = coverage.get(str(row["requirement_public_id"]), NO_COVERAGE)
        items = _item_responses(items_by_requirement.get(int(row["id"]), []), capability_rows, structure)
        responses.append(
            ResourceRequirementResponse(
                **{key: value for key, value in row.items() if key in ResourceRequirementResponse.model_fields},
                units_covered=covered.units_covered,
                units_remaining=max(int(row["units_required"]) - covered.units_covered, 0),
                covered_unit_numbers=list(covered.covered_unit_numbers),
                items=items,
                warnings=_warnings(
                    status_code=row["requirement_status_code"],
                    dates=(row["required_from"], row["required_to"]),
                    crew=(int(row["crew_operators_required"]), int(row["crew_helpers_required"])),
                    items=items,
                    facts=facts,
                    structure=structure,
                ),
                line=facts,
            )
        )
    return responses


def _coverage(
    db: Session, rows: list[dict[str, Any]], facts_by_id: dict[int, ResourceRequirementLineFacts]
) -> dict[str, Coverage]:
    """Each requirement's coverage by the machines held for it, from Assignment through the port, in one call
    for the whole page. A cancelled requirement holds none (its cancellation freed them)."""
    wanted = [
        RequirementToCover(
            requirement_public_id=str(row["requirement_public_id"]),
            units_required=int(row["units_required"]),
            required_from=row["required_from"],
            planned_end=requirement_planned_end(row["required_to"], facts_by_id[int(row["id"])]),
        )
        for row in rows
        if row["requirement_status_code"] != REQUIREMENT_STATUS_CANCELLED
    ]
    return assignment_port().coverage(db, wanted) if wanted else {}


def _fulfilment_status(units_required: int, covered: Coverage) -> str:
    """OPEN with no machine held on any unit; FULFILLED with every unit covered on every day; otherwise
    PARTLY_FULFILLED (8A core, section 6.5)."""
    if covered.units_with_machines == 0:
        return REQUIREMENT_STATUS_OPEN
    if covered.units_covered >= units_required:
        return REQUIREMENT_STATUS_FULFILLED
    return REQUIREMENT_STATUS_PARTLY_FULFILLED


def _get_response(db: Session, public_id: str, **kwargs: Any) -> ResourceRequirementResponse:
    row = get_requirement_row(db, public_id=public_id)
    if row is None:
        raise ResourceRequirementNotFoundError("Resource requirement not found.")
    return _build_responses(db, [row], **kwargs)[0]


def get_resource_requirement(db: Session, public_id: UUID) -> ResourceRequirementResponse:
    return _get_response(db, str(public_id))


def list_resource_requirements(
    db: Session,
    *,
    work_order_public_id: UUID | None = None,
    work_order_line_public_id: UUID | None = None,
    status_code: str | None = None,
    equipment_class_code: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ResourceRequirementResponse]:
    """The planning list: urgent first, then the earliest start, filterable by Work Order, line, status
    and equipment class. `NEEDS_MACHINES` is open and partly allocated together (8A core)."""
    status = _code(status_code)
    status_codes: tuple[str, ...] | None
    if status is None:
        status_codes = None
    elif status == STATUS_FILTER_NEEDS_MACHINES:
        status_codes = NEEDS_MACHINES_STATUS_CODES
    elif status in REQUIREMENT_STATUS_CODES:
        status_codes = (status,)
    else:
        raise ResourceRequirementValidationError(
            "Status must be Needs machines, Open, Partly allocated, Allocated or Cancelled."
        )
    rows = list_requirement_rows(
        db,
        work_order_public_id=str(work_order_public_id) if work_order_public_id else None,
        work_order_line_public_id=str(work_order_line_public_id) if work_order_line_public_id else None,
        status_codes=status_codes,
        equipment_class_code=_code(equipment_class_code),
        limit=limit,
        offset=offset,
    )
    return _build_responses(db, rows)


def _line_reference(db: Session, line_public_id: UUID) -> WorkOrderLineReference:
    try:
        return get_work_order_line_reference(db, line_public_id)
    except WorkOrderLineNotFoundError as exc:
        raise ResourceRequirementLineNotFoundError("Work Order line not found.") from exc


def get_resource_requirement_defaults(
    db: Session, *, work_order_line_public_id: UUID, required_from: date | None = None
) -> ResourceRequirementDefaultsResponse:
    """What a new requirement for a line starts from (design section 8).

    It starts on the line's own start date, else the contract's, unless the caller names a date; crew
    starts from the Work Order's Part 4 numbers in force then, and equipment only starts at zero. A class
    is suggested when the line's category text matches a class or an alias ("Crane" suggests Crane).
    """
    reference = _line_reference(db, work_order_line_public_id)
    view = _read_work_order(db, reference.work_order_public_id)
    line_public_id = str(reference.work_order_line_public_id)
    detail = view.details.get(line_public_id)
    start = required_from or (detail.line_start_date if detail else None) or view.contract.contract_start_date
    facts = _line_facts(view, line_public_id, start)
    crew = _work_order_crew(facts)
    structure = get_equipment_structure(db)
    suggestion = suggest_equipment_class(
        structure, reference.equipment_service_category, business_line_code=REQUIREMENT_BUSINESS_LINE
    )
    return ResourceRequirementDefaultsResponse(
        work_order_public_id=reference.work_order_public_id,
        work_order_code=reference.work_order_code,
        work_order_line_public_id=reference.work_order_line_public_id,
        work_order_line_number=reference.line_number,
        source_offer_line_public_id=reference.source_offer_line_public_id,
        account_public_id=reference.account_public_id,
        taxonomy_version=structure.taxonomy_version,
        line=facts,
        suggested=ResourceRequirementSuggestedValues(
            units_required=1,
            required_from=start,
            required_to=None,
            crew_operators_required=crew[0] if crew else None,
            crew_helpers_required=crew[1] if crew else None,
            priority_code=PRIORITY_NORMAL,
            equipment_class_code=suggestion.class_code if suggestion else None,
            equipment_type_code=suggestion.type_code if suggestion else None,
            equipment_class_matched_term=suggestion.matched_term if suggestion else None,
        ),
        existing_requirement_count=count_requirements_for_line(db, work_order_line_public_id=line_public_id),
    )


# --- Events ----------------------------------------------------------------------------------------


def _event_payload(response: ResourceRequirementResponse, changed_fields: list[str]) -> dict[str, Any]:
    """Codes, numbers, dates and public ids only: never the specification, the notes or a cancellation
    reason, and never an amount (design section 12)."""
    return {
        "requirement_reference": response.requirement_reference,
        "work_order_public_id": str(response.work_order_public_id),
        "work_order_line_public_id": str(response.work_order_line_public_id),
        "source_offer_line_public_id": (
            str(response.source_offer_line_public_id) if response.source_offer_line_public_id else None
        ),
        "site_address_public_id": str(response.line.site.public_id) if response.line.site else None,
        "requirement_version": response.requirement_version,
        "requirement_status_code": response.requirement_status_code,
        "units_required": response.units_required,
        "required_from": response.required_from.isoformat(),
        "required_to": response.required_to.isoformat() if response.required_to else None,
        "crew_operators_required": response.crew_operators_required,
        "crew_helpers_required": response.crew_helpers_required,
        "priority_code": response.priority_code,
        "taxonomy_version": response.taxonomy_version,
        "items": [
            {
                "item_number": item.item_number,
                "equipment_class_code": item.equipment_class_code,
                "equipment_type_code": item.equipment_type_code,
                "capabilities": [
                    {
                        "capability_code": capability.capability_code,
                        "value": (
                            str(capability.minimum_value)
                            if capability.minimum_value is not None
                            else capability.choice_value
                        ),
                    }
                    for capability in item.capabilities
                ],
            }
            for item in response.items
        ],
        "changed_fields": changed_fields,
    }


def _record_event(
    db: Session,
    *,
    event_name: str,
    response: ResourceRequirementResponse,
    changed_fields: list[str],
    status_before: str | None,
    reason: str,
    current_user_public_id: str | None,
) -> dict[str, Any]:
    event = record_business_event(
        db,
        event_name=event_name,
        source_module=RESOURCE_REQUIREMENT_MODULE_NAME,
        record_type=RESOURCE_REQUIREMENT_RECORD_TYPE,
        record_public_id=str(response.requirement_public_id),
        user_public_id=current_user_public_id,
        status_before=status_before,
        status_after=response.requirement_status_code,
        reason=reason,
        event_payload=_event_payload(response, changed_fields),
    )
    return event.model_dump()


# --- Writing ---------------------------------------------------------------------------------------


def _write_items(db: Session, *, requirement_id: int, items: list[_Item]) -> None:
    for number, item in enumerate(items, 1):
        item_id = insert_item(
            db,
            requirement_id=requirement_id,
            item_number=number,
            equipment_class_code=item.equipment_class_code,
            equipment_type_code=item.equipment_type_code,
            equipment_specification=item.equipment_specification,
        )
        for capability in item.capabilities:
            insert_item_capability(
                db,
                item_id=item_id,
                equipment_class_code=item.equipment_class_code,
                capability_code=capability.capability_code,
                minimum_value=capability.minimum_value,
                choice_value=capability.choice_value,
            )


def _stored_item(response: ResourceRequirementResponse) -> _Item | None:
    if not response.items:
        return None
    item = response.items[0]
    return _Item(
        equipment_class_code=item.equipment_class_code,
        equipment_type_code=item.equipment_type_code,
        equipment_specification=item.equipment_specification,
        capabilities=tuple(
            _Capability(
                capability_code=capability.capability_code,
                minimum_value=capability.minimum_value,
                choice_value=capability.choice_value,
            )
            for capability in item.capabilities
        ),
    )


def _changed_fields(
    current: ResourceRequirementResponse | None, values: dict[str, Any], items: list[_Item]
) -> list[str]:
    """What a save would change, in a fixed order. On a first save, every field given a value."""
    if current is None:
        return [field for field in REQUIREMENT_COMPARED_FIELDS if field == "items" or values.get(field) is not None]
    changed = [
        field
        for field in REQUIREMENT_COMPARED_FIELDS
        if field != "items" and getattr(current, field) != values[field]
    ]
    stored = _stored_item(current)
    if [item.comparable() for item in items] != ([stored.comparable()] if stored else []):
        changed.append("items")
    return changed


REQUIREMENT_KEY_USED = (
    "This form was already used to record a requirement, so this save was not recorded. Go back to the Work Order to "
    "see the requirement it recorded, and change it there."
)


def _replay(db: Session, existing: dict[str, Any], fingerprint: str) -> ResourceRequirementActionResponse:
    """A create repeated with the same request key returns the first requirement and records nothing - only for the
    very same request. Any other request with the key, on the same line or another, is refused rather than answered
    with a requirement it did not ask for (TB-1 TB1-102 part b, 8A's rule; it replaces WRR-001's comparison of the
    line alone)."""
    if not is_same_request(existing["create_request_fingerprint"], fingerprint):
        raise ResourceRequirementConflictError(REQUIREMENT_KEY_USED)
    return ResourceRequirementActionResponse(
        resource_requirement=_get_response(db, str(existing["requirement_public_id"])), event=None, replayed=True
    )


def create_resource_requirement(
    db: Session, *, payload: ResourceRequirementCreate, current_user_public_id: str | None
) -> ResourceRequirementActionResponse:
    create_request_key = str(payload.create_request_key)
    fingerprint = request_fingerprint(payload)
    reference = _line_reference(db, payload.work_order_line_public_id)
    if str(reference.work_order_public_id) != str(payload.work_order_public_id):
        # The same answer as an unknown line, so the response never confirms that a line exists elsewhere.
        raise ResourceRequirementLineNotFoundError("Work Order line not found on this Work Order.")
    line_public_id = str(reference.work_order_line_public_id)

    public_id = str(uuid4())
    try:
        with rollback_on_error(db):
            # The Work Order first (8A core, independent review round 4, 8A-R4-001): the replay, the closure and every
            # date check read it under its lock, so a Work Order change committed meanwhile is seen, never a copy read
            # before it. The line a Work Order owns never moves, so it is found before the lock.
            _hold_work_order_open(db, reference.work_order_public_id)
            existing = find_requirement_by_create_request_key(db, create_request_key=create_request_key)
            if existing is not None:
                db.rollback()
                return _replay(db, existing, fingerprint)
            structure = get_equipment_structure(db)
            values, items = _normalize_fields(payload, structure)
            view = _read_work_order(db, reference.work_order_public_id)
            _check_dates_on_save(
                values, _line_facts(view, line_public_id, values["required_from"]), line_number=reference.line_number
            )
            requirement_id = insert_requirement(
                db,
                values={
                    **values,
                    "requirement_public_id": public_id,
                    "work_order_line_id": reference.work_order_line_id,
                    "work_order_public_id": str(reference.work_order_public_id),
                    "work_order_code": reference.work_order_code,
                    "work_order_line_public_id": line_public_id,
                    "work_order_line_number": reference.line_number,
                    "source_offer_line_public_id": (
                        str(reference.source_offer_line_public_id) if reference.source_offer_line_public_id else None
                    ),
                    "account_public_id": str(reference.account_public_id) if reference.account_public_id else None,
                    "requirement_status_code": REQUIREMENT_STATUS_OPEN,
                    "taxonomy_version": structure.taxonomy_version,
                    "create_request_key": create_request_key,
                    "create_request_fingerprint": fingerprint,
                    "created_by": current_user_public_id,
                    "updated_by": current_user_public_id,
                },
            )
            _write_items(db, requirement_id=requirement_id, items=items)
            response = _get_response(db, public_id, structure=structure, views={str(reference.work_order_public_id): view})
            event = _record_event(
                db,
                event_name=RESOURCE_REQUIREMENT_EVENT_CREATED,
                response=response,
                changed_fields=_changed_fields(None, values, items),
                status_before=None,
                reason="Resource requirement recorded for a Work Order line.",
                current_user_public_id=current_user_public_id,
            )
            db.commit()
    except IntegrityError as exc:
        # Two submissions of one key raced: the other one committed first. Replay it, or refuse another request.
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        if constraint != "uq_resource_requirement_create_request_key":
            raise
        existing = find_requirement_by_create_request_key(db, create_request_key=create_request_key)
        if existing is None:
            raise
        return _replay(db, existing, fingerprint)

    return ResourceRequirementActionResponse(resource_requirement=response, event=event)


def _locked_live_requirement(db: Session, public_id: UUID, expected_version: int, *, action: str) -> dict[str, Any]:
    locked = lock_requirement_row(db, public_id=str(public_id))
    if locked is None:
        raise ResourceRequirementNotFoundError("Resource requirement not found.")
    if locked["requirement_status_code"] not in REQUIREMENT_LIVE_STATUS_CODES:
        raise ResourceRequirementValidationError(f"This requirement is cancelled, so it can no longer be {action}.")
    if int(locked["requirement_version"]) != expected_version:
        raise ResourceRequirementConflictError(
            "Someone else changed this requirement after you opened it. Reload to see their version."
        )
    return locked


def update_resource_requirement(
    db: Session, *, public_id: UUID, payload: ResourceRequirementUpdate, current_user_public_id: str | None
) -> ResourceRequirementActionResponse:
    """Whole replacement of a requirement that is not cancelled, and its item, guarded by the version the caller
    read. An identical save records nothing. Machines held for it never refuse a change (8A core, 6.5): one that
    no longer fits shows a warning on its allocation, and the status follows the new units and dates."""
    event: dict[str, Any] | None = None
    work_order_public_id = _work_order_of(db, public_id)
    with rollback_on_error(db):
        _hold_work_order_open(db, work_order_public_id)
        locked = _locked_live_requirement(db, public_id, payload.expected_requirement_version, action="changed")
        structure = get_equipment_structure(db)
        views: dict[str, _WorkOrderView] = {}
        current = _get_response(db, str(public_id), structure=structure, views=views)
        reference = _line_reference(db, current.work_order_line_public_id)
        _refuse_closed(reference.work_order_status_code)
        view = views[str(reference.work_order_public_id)]
        values, items = _normalize_fields(payload, structure, kept=_stored_item(current))
        _check_dates_on_save(
            values,
            _line_facts(view, str(reference.work_order_line_public_id), values["required_from"]),
            line_number=reference.line_number,
        )
        changed = _changed_fields(current, values, items)
        if not changed:
            db.rollback()
            return ResourceRequirementActionResponse(resource_requirement=current, event=None)

        updated = update_requirement(
            db,
            requirement_id=int(locked["id"]),
            expected_version=payload.expected_requirement_version,
            values={**values, "taxonomy_version": structure.taxonomy_version},
            current_user_public_id=current_user_public_id,
            updated_at=_now(),
        )
        if updated != 1:
            raise ResourceRequirementConflictError(
                "Someone else changed this requirement after you opened it. Reload to see their version."
            )
        delete_items(db, requirement_id=int(locked["id"]))
        _write_items(db, requirement_id=int(locked["id"]), items=items)
        # New units or dates can change which units are covered.
        _refresh_fulfilment(db, str(public_id), current_user_public_id=current_user_public_id)
        response = _get_response(
            db, str(public_id), structure=structure, views={str(reference.work_order_public_id): view}
        )
        # The edit itself changes no status: a move the new units or dates cause is ResourceRequirementFulfilmentChanged's,
        # recorded just above, so the audit shows each transition once (independent review, round 2, 8A-R2-003).
        event = _record_event(
            db,
            event_name=RESOURCE_REQUIREMENT_EVENT_UPDATED,
            response=response,
            changed_fields=changed,
            status_before=response.requirement_status_code,
            reason="Resource requirement changed.",
            current_user_public_id=current_user_public_id,
        )
        db.commit()
    return ResourceRequirementActionResponse(resource_requirement=response, event=event)


def cancel_resource_requirement(
    db: Session, *, public_id: UUID, payload: ResourceRequirementCancel, current_user_public_id: str | None
) -> ResourceRequirementActionResponse:
    """Cancel a requirement, with a reason. Final: kept, never deleted, never reopened. Every machine held for
    it is freed first, in the same transaction, through Assignment - its history kept (WRR-001: "Cancellation
    ... releases uncommitted reservations")."""
    reason = _clean(payload.cancellation_reason)
    if reason is None:
        raise ResourceRequirementValidationError("Give the reason the requirement is being cancelled.")
    if not current_user_public_id:
        # Who cancelled is part of the record (ck_resource_requirement_cancellation requires it); a route
        # only reaches here with an authenticated user, so this is the backstop, not the control.
        raise ResourceRequirementValidationError("The signed-in user could not be identified, so nothing was cancelled.")
    work_order_public_id = _work_order_of(db, public_id)
    with rollback_on_error(db):
        _hold_work_order_open(db, work_order_public_id)
        locked = _locked_live_requirement(db, public_id, payload.expected_requirement_version, action="cancelled")
        reference = _line_reference(db, UUID(str(locked["work_order_line_public_id"])))
        _refuse_closed(reference.work_order_status_code)
        # The Work Order's and the requirement's locks are held; the port takes Assignment's next - the order every
        # write keeps (6.12, as corrected in review round 3).
        machines_freed = assignment_port().release_for_cancelled_requirement(
            db, requirement_public_id=str(public_id), user_public_id=current_user_public_id
        )
        cancelled = cancel_requirement(
            db,
            requirement_id=int(locked["id"]),
            expected_version=payload.expected_requirement_version,
            reason=reason,
            current_user_public_id=current_user_public_id,
            cancelled_at=_now(),
        )
        if cancelled != 1:
            raise ResourceRequirementConflictError(
                "Someone else changed this requirement after you opened it. Reload to see their version."
            )
        response = _get_response(db, str(public_id))
        event = _record_event(
            db,
            event_name=RESOURCE_REQUIREMENT_EVENT_CANCELLED,
            response=response,
            changed_fields=["requirement_status_code"],
            status_before=str(locked["requirement_status_code"]),
            reason="Resource requirement cancelled.",
            current_user_public_id=current_user_public_id,
        )
        db.commit()
    return ResourceRequirementActionResponse(resource_requirement=response, event=event, machines_freed=machines_freed)


# --- For Resource Assignment (8A core) -------------------------------------------------------------------


def lock_resource_requirement(db: Session, public_id: UUID | str) -> str:
    """Take the requirement's row lock for an allocation's write - the first lock every such write takes
    (design section 6.12) - and return its status. The caller commits or rolls back."""
    locked = lock_requirement_row(db, public_id=str(public_id))
    if locked is None:
        raise ResourceRequirementNotFoundError("Resource requirement not found.")
    return str(locked["requirement_status_code"])


def refresh_requirement_fulfilment(db: Session, public_id: UUID | str, *, current_user_public_id: str | None) -> str:
    """After Assignment holds, replaces or frees a machine: set the requirement's status from its coverage, in the
    caller's transaction, recording ResourceRequirementFulfilmentChanged when it moves. The caller holds the
    requirement's row lock (`lock_resource_requirement`). Returns the status."""
    return _refresh_fulfilment(db, str(public_id), current_user_public_id=current_user_public_id)


def _refresh_fulfilment(db: Session, public_id: str, *, current_user_public_id: str | None) -> str:
    row = get_requirement_row(db, public_id=public_id)
    if row is None:
        raise ResourceRequirementNotFoundError("Resource requirement not found.")
    before = str(row["requirement_status_code"])
    if before == REQUIREMENT_STATUS_CANCELLED:
        return before
    work_order_public_id = str(row["work_order_public_id"])
    facts = _line_facts(_read_work_order(db, work_order_public_id), str(row["work_order_line_public_id"]), row["required_from"])
    # The status stored here must be worked out from committed allocations: Resource Assignment's lock first, after
    # the Work Order's and this requirement's, so an allocation write in progress - a direct one included - is waited
    # for, never read half done (independent review, 8A-FA-001).
    assignment_port().hold(db)
    covered = _coverage(db, [row], {int(row["id"]): facts}).get(public_id, NO_COVERAGE)
    after = _fulfilment_status(int(row["units_required"]), covered)
    if after == before:
        return before
    set_requirement_status(db, requirement_id=int(row["id"]), status_code=after)
    units_required = int(row["units_required"])
    record_business_event(
        db,
        event_name=RESOURCE_REQUIREMENT_EVENT_FULFILMENT_CHANGED,
        source_module=RESOURCE_REQUIREMENT_MODULE_NAME,
        record_type=RESOURCE_REQUIREMENT_RECORD_TYPE,
        record_public_id=public_id,
        user_public_id=current_user_public_id,
        status_before=before,
        status_after=after,
        reason="The machines held for the requirement changed.",
        event_payload={
            "requirement_reference": row["requirement_reference"],
            "work_order_public_id": work_order_public_id,
            "work_order_line_public_id": str(row["work_order_line_public_id"]),
            "requirement_status_code": after,
            "units_required": units_required,
            "units_covered": covered.units_covered,
            "units_remaining": max(units_required - covered.units_covered, 0),
        },
    )
    return after


def _refresh_open_ended_requirements(db: Session, work_order_public_id: str, current_user_public_id: str | None) -> None:
    """Registered with the Work Orders module (8A core, independent review round 1, 8A-R1-001): its contract's end or a
    line's own end moved, so a requirement with no end of its own now runs to another day and its status is worked
    out again, in the Work Order's own transaction. That transaction holds the Work Order's row lock; the requirement
    rows are locked in id order and the allocations read through the port - the order every path keeps, as
    no requirement or allocation write takes the Work Order's lock."""
    for public_id in lock_open_ended_live_rows_of_work_order(db, work_order_public_id=work_order_public_id):
        _refresh_fulfilment(db, public_id, current_user_public_id=current_user_public_id)


register_end_dates_listener(_refresh_open_ended_requirements)
