"""Resource Assignment: own machines allocated to the resource requirements (8A core, RPA-001).

Design: docs/agent/slices/8a-core-equipment-allocation.md (agreed by the owner, 28 September 2026); the API is
docs/agent/contracts/resource-assignment-api-contract.md. In short:

- An allocation is one machine on one unit of one requirement, for a period. Before the Work Order is released
  it holds the machine (Q1). A machine is never on two allocations, and a unit never filled twice, on a common
  day: checked here and refused by the database's exclusion constraints, so the first valid commitment wins.
- Eligibility's `record_decision` is called in the allocation's own transaction and its decision kept. A machine
  that cannot be allocated, or needs an approval that cannot be given yet, is refused; one with warnings is
  allocated only when the user confirms having seen them (Q2).
- Replacing ends the old allocation the day before the new one starts; freeing ends it with a reason. Nothing is
  deleted. Each write refreshes the requirement's status through its own service.
- Locks are always taken in one order: the requirement's row, this module's write lock, Eligibility's (6.12).
- The kit going to site is listed per trip from the kit held for the machine's model, each piece checked.

Reading is `views.py`. This module registers the port Resource Requirements reads coverage and frees machines
through (`resource_requirements.ports`), so that module never imports this one.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.authorization.contract import WORK_ORDER_LINE_BILLING_TERMS_WRITE
from app.modules.authorization.service import has_permission
from app.modules.eligibility.ports import AllocatedAsset, register_allocation_source
from app.modules.eligibility.service import EligibilityValidationError, record_decision
from app.modules.equipment_reference.contract import ASSET_KIND_MACHINE, ASSET_STATUS_ACTIVE
from app.modules.equipment_reference.ports import ListedKit, register_kit_listing_source
from app.modules.equipment_reference.service import AllocationAsset, allocation_asset, kit_for_machine
from app.modules.events.service import record_business_event
from app.modules.identity.schemas import AuthUser
from app.modules.resource_assignments import repository as repo
from app.modules.resource_assignments.contract import (
    BILLING_CYCLE_CODES,
    DECISION_FOR_ASSIGNMENT,
    DECISION_FOR_KIT_LINE,
    EVENT_BILLING_CYCLE_SET,
    EVENT_CHECKED,
    EVENT_DATES_CHANGED,
    EVENT_HELD,
    EVENT_KIT_LISTED,
    EVENT_KIT_REMOVED,
    EVENT_RELEASED,
    EVENT_REPLACED,
    EVENT_TRIP_ADDED,
    EVENT_TRIP_NOTE_CHANGED,
    KIT_LINE_LISTED,
    KIT_LINE_REMOVED,
    LEFT_OUT_BELOW_REQUIREMENT,
    LEFT_OUT_CLASS_DIFFERS,
    LEFT_OUT_RATING_UNKNOWN,
    LEFT_OUT_TYPE_DIFFERS,
    LEFT_OUT_TYPE_UNKNOWN,
    REASON_OTHER,
    RELEASE_REASON_CODES,
    RELEASE_RECORDED_BY_MISTAKE,
    RELEASE_REQUIREMENT_CANCELLED,
    REPLACEMENT_REASON_CODES,
    REQUEST_ALLOCATE,
    REQUEST_KIT,
    REQUEST_REPLACE,
    RESOURCE_ASSIGNMENT_MODULE_NAME,
    RESOURCE_ASSIGNMENT_RECORD_TYPE,
    STATUS_HELD,
    STATUS_RELEASED,
    STATUS_REPLACED,
)
from app.modules.resource_assignments.errors import (
    AssignmentConflictError,
    AssignmentForbiddenError,
    AssignmentNotFoundError,
    AssignmentValidationError,
)
from app.modules.resource_assignments.rules import (
    Days,
    busy_days,
    covered_units,
    effective_end,
    left_out_reason,
    most_in_use,
    requirement_coverage,
)
from app.modules.resource_assignments.schemas import (
    Answer,
    AssignmentActionResponse,
    AssignmentBillingCycle,
    AssignmentCreate,
    AssignmentDates,
    AssignmentRelease,
    AssignmentReplace,
    AssignmentResponse,
    AssignmentVersion,
    KitAdd,
    SiteFacts,
    TripCreate,
    TripNote,
)
from app.modules.resource_assignments.views import (
    BLOCKING_ANSWERS,
    answer_from_check,
    asked_of,
    build_assignments,
    check_period,
    conflict_of_assignment,
    describe_conflict,
    describe_problems,
    get_assignment,
    held_for_reminders,
    kit_window,
    load_requirement,
    piece_availability,
    require_site,
    site_facts,
)
from app.modules.resource_requirements.ports import Coverage, RequirementToCover, register_assignment_port
from app.modules.resource_requirements.schemas import ResourceRequirementResponse
from app.modules.resource_requirements.service import (
    ResourceRequirementNotFoundError,
    lock_resource_requirement,
    refresh_requirement_fulfilment,
)
from app.modules.work_orders.contract import WORK_ORDER_STATUS_CLOSED
from app.modules.work_orders.service import WorkOrderNotFoundError, hold_work_order_status
from app.modules.work_orders.contract_period_rules import format_contract_date
from app.shared import business_time
from app.shared.request_keys import request_fingerprint
from app.shared.transactions import rollback_on_error

STALE = "Someone else changed this allocation after you opened it. Reload to see their version."
CLOSED = "This Work Order is closed. Its machines can no longer be allocated or changed."
KEY_USED = "This form was already used for something else. Reload the page and try again."
ONE_DAY = timedelta(days=1)


def can_set_billing_cycle(db: Session, user: AuthUser) -> bool:
    """Whether the signed-in user may set a billing cycle when allocating or replacing: the permission that changes
    billing terms (design section 6.9). Resolved here, as Eligibility resolves its own, so routes never read roles."""
    return has_permission(db, user.role_codes, WORK_ORDER_LINE_BILLING_TERMS_WRITE)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _request_key(value: str) -> str:
    cleaned = _clean(value)
    if cleaned is None:
        raise AssignmentValidationError("The form sent a blank request key, so nothing was recorded. Reload the page and try again.")
    return cleaned


def _fingerprint(payload: BaseModel, *, acts_on: UUID | str | None = None) -> str:
    """The request as sent, with the allocation it acts on, hashed. Only the fields sent count, so leaving one out and
    sending it empty differ - they mean different things for a replacement's end and billing cycle. A request key
    replays only the request with this fingerprint; any other use of the key is refused (8A-R1-002). The rule is the
    platform's now, so other modules' keyed creates follow it (TB-1 TB1-102 part b): app/shared/request_keys.py."""
    return request_fingerprint(payload, acts_on=acts_on)


def _require_user(user_public_id: str | None) -> str:
    if not user_public_id:
        raise AssignmentValidationError("The signed-in user could not be identified, so nothing was recorded.")
    return user_public_id


def _billing_cycle(value: str | None) -> str | None:
    code = (_clean(value) or "").upper() or None
    if code is not None and code not in BILLING_CYCLE_CODES:
        raise AssignmentValidationError("The billing cycle must be Weekly or Monthly, or left not stated yet.")
    return code


def _reason(code: str, note: str | None, *, allowed: tuple[str, ...], what: str) -> tuple[str, str | None]:
    reason = code.strip().upper()
    if reason not in allowed:
        raise AssignmentValidationError(f"Choose why the machine is being {what}.")
    cleaned = _clean(note)
    if reason == REASON_OTHER and cleaned is None:
        raise AssignmentValidationError("Say what the other reason is.")
    return reason, cleaned


def _date(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


def _label(asset: AllocationAsset) -> str:
    return f"{asset.asset_reference} ({asset.machine_number})" if asset.machine_number else asset.asset_reference


def _event(
    db: Session,
    *,
    event_name: str,
    assignment_public_id: str,
    user_public_id: str,
    status_before: str | None,
    status_after: str | None,
    reason: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Payloads carry public ids, references, codes, versions, counts and dates only: never a registration, a note
    or a reason's text (design section 10)."""
    event = record_business_event(
        db,
        event_name=event_name,
        source_module=RESOURCE_ASSIGNMENT_MODULE_NAME,
        record_type=RESOURCE_ASSIGNMENT_RECORD_TYPE,
        record_public_id=assignment_public_id,
        user_public_id=user_public_id,
        status_before=status_before,
        status_after=status_after,
        reason=reason,
        event_payload=payload,
    )
    return event.model_dump(mode="json")


def _identity(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "assignment_public_id": str(row["assignment_public_id"]),
        "assignment_reference": row["assignment_reference"],
        "requirement_public_id": str(row["resource_requirement_public_id"]),
        "work_order_public_id": str(row["work_order_public_id"]),
        "work_order_line_public_id": str(row["work_order_line_public_id"]),
        "source_offer_line_public_id": str(row["source_offer_line_public_id"]) if row["source_offer_line_public_id"] else None,
        "unit_number": int(row["unit_number"]),
        "machine_public_id": str(row["equipment_asset_public_id"]),
    }


# --- Checks shared by the writes --------------------------------------------------------------------------


def _lock_requirement(db: Session, public_id: UUID | str) -> None:
    try:
        lock_resource_requirement(db, public_id)
    except ResourceRequirementNotFoundError as exc:
        raise AssignmentNotFoundError("Resource requirement not found.") from exc


def _usable_requirement(requirement: ResourceRequirementResponse) -> None:
    if requirement.requirement_status_code == "CANCELLED":
        raise AssignmentValidationError(
            f"{requirement.requirement_reference} is cancelled, so no machine can be allocated to it."
        )
    if requirement.line.work_order_status_code == WORK_ORDER_STATUS_CLOSED:
        raise AssignmentValidationError(CLOSED)


def _hold_work_order_open(db: Session, work_order_public_id: UUID | str) -> None:
    """The first lock every write takes (design section 6.12, as corrected in review round 2, 8A-R2-001): the Work
    Order's row, shared, so a change to it - its closure included - waits for this write or is seen by it. Then the
    requirement's row, this module's lock and Eligibility's. A closed Work Order refuses the write: one that would
    change nothing, and a request replayed, included."""
    try:
        status_code = hold_work_order_status(db, work_order_public_id)
    except WorkOrderNotFoundError as exc:
        raise AssignmentNotFoundError("Work Order not found.") from exc
    if status_code == WORK_ORDER_STATUS_CLOSED:
        raise AssignmentValidationError(CLOSED)


def _locked_held(db: Session, public_id: UUID | str, expected_version: int, *, action: str) -> dict[str, Any]:
    row = repo.lock_assignment_row(db, public_id=str(public_id))
    if row is None:
        raise AssignmentNotFoundError("Allocation not found.")
    if int(row["assignment_version"]) != expected_version:
        raise AssignmentConflictError(STALE)
    if row["assignment_status_code"] != STATUS_HELD:
        ended = "replaced" if row["assignment_status_code"] == STATUS_REPLACED else "freed"
        raise AssignmentValidationError(f"{row['assignment_reference']} was {ended}, so it can no longer be {action}.")
    return row


def _held_on_open_work_order(
    db: Session, public_id: UUID | str, expected_version: int, *, action: str
) -> tuple[dict[str, Any], ResourceRequirementResponse]:
    """The held allocation, locked, and its requirement. Every write on an allocation is refused once its Work Order
    is closed - one that would change nothing included (independent review, round 1, 8A-R1-003)."""
    row = _locked_held(db, public_id, expected_version, action=action)
    requirement = load_requirement(db, str(row["resource_requirement_public_id"]))
    _usable_requirement(requirement)
    return row, requirement


def _owner_of(db: Session, public_id: UUID | str) -> dict[str, Any]:
    """An allocation read without a lock, for the Work Order and requirement it belongs to - which never change - so
    a write can take their locks first."""
    row = repo.get_assignment_row(db, public_id=str(public_id))
    if row is None:
        raise AssignmentNotFoundError("Allocation not found.")
    return row


def _claim(db: Session, key: str, *, kind: str, requirement_public_id: str, fingerprint: str, user: str) -> bool:
    """True when the key already made this very request - the caller returns what it made; False when the key is
    new, now claimed in the caller's transaction. A key used for any other request, of any kind, is 409 (8A-R2-002).
    Called under this module's lock, so two uses of one key are never both new."""
    earlier = repo.get_request(db, create_request_key=key)
    if earlier is None:
        repo.insert_request(
            db,
            create_request_key=key,
            kind_code=kind,
            requirement_public_id=requirement_public_id,
            fingerprint=fingerprint,
            user_public_id=user,
        )
        return False
    if earlier["request_kind_code"] != kind or earlier["request_fingerprint"] != fingerprint:
        raise AssignmentConflictError(KEY_USED)
    return True


def _replayed(db: Session, key: str, *, kind: str, acts_on: UUID | str | None = None) -> AssignmentActionResponse:
    """What a request key made, returned again with no event (ADR-023)."""
    if kind == REQUEST_KIT:
        return AssignmentActionResponse(assignment=get_assignment(db, str(acts_on)), replayed=True)
    made = repo.find_assignment_by_request_key(db, create_request_key=key)
    if made is None:
        raise AssignmentConflictError(KEY_USED)
    return AssignmentActionResponse(
        assignment=get_assignment(db, str(made["assignment_public_id"])),
        replaced=get_assignment(db, str(acts_on)) if kind == REQUEST_REPLACE else None,
        replayed=True,
    )


def _after_key_race(
    db: Session, exc: IntegrityError, key: str, *, kind: str, fingerprint: str, acts_on: UUID | str | None = None
) -> AssignmentActionResponse:
    """A save refused by the database: a machine, unit or piece taken meanwhile, or - should two uses of one key
    ever meet - the key's own uniqueness, read again as a replay or a 409."""
    db.rollback()
    conflict = _integrity_conflict(exc)
    if conflict is not None:
        raise conflict from exc
    earlier = repo.get_request(db, create_request_key=key)
    if earlier is None:
        raise exc
    if earlier["request_kind_code"] != kind or earlier["request_fingerprint"] != fingerprint:
        raise AssignmentConflictError(KEY_USED) from exc
    return _replayed(db, key, kind=kind, acts_on=acts_on)


LEFT_OUT_WORDS = {
    LEFT_OUT_CLASS_DIFFERS: "it is not of the class asked for",
    LEFT_OUT_TYPE_UNKNOWN: "its type is not known (its model is not mapped)",
    LEFT_OUT_TYPE_DIFFERS: "it is not of the type asked for",
    LEFT_OUT_RATING_UNKNOWN: "a capability asked for is not known for it",
    LEFT_OUT_BELOW_REQUIREMENT: "it does not meet a capability asked for",
}


def _fitting_machine(db: Session, requirement: ResourceRequirementResponse, machine_public_id: UUID | str) -> AllocationAsset:
    machine = allocation_asset(db, str(machine_public_id))
    if machine is None:
        raise AssignmentNotFoundError("Machine not found.")
    if machine.asset_kind_code != ASSET_KIND_MACHINE:
        raise AssignmentValidationError(
            f"{machine.asset_reference} is not a machine: kit goes to site on a Trip (Own Load), and a part with its machine."
        )
    if machine.asset_status_code != ASSET_STATUS_ACTIVE:
        raise AssignmentValidationError(f"{_label(machine)} is retired, so it cannot be allocated.")
    class_code, type_code, asked = asked_of(requirement)
    reason = left_out_reason(machine, class_code=class_code, type_code=type_code, asked=asked)
    if reason is not None:
        raise AssignmentValidationError(
            f"{_label(machine)} does not meet what {requirement.requirement_reference} asks for: {LEFT_OUT_WORDS[reason]}."
        )
    return machine


def _refuse_overlaps(
    db: Session,
    *,
    machine: AllocationAsset,
    requirement: ResourceRequirementResponse,
    unit_number: int,
    start: date,
    end: date | None,
    excluding: list[int],
) -> None:
    taken = repo.list_machine_overlaps(db, machine_public_id=machine.asset_public_id, start=start, end=end, excluding=excluding)
    if taken:
        raise AssignmentConflictError(
            f"{describe_conflict(_label(machine), conflict_of_assignment(taken[0]))} Choose another machine or other dates."
        )
    filled = repo.list_unit_overlaps(
        db,
        requirement_public_id=str(requirement.requirement_public_id),
        unit_number=unit_number,
        start=start,
        end=end,
        excluding=excluding,
    )
    if filled:
        other = conflict_of_assignment(filled[0])
        until = f" to {format_contract_date(other.busy_to)}" if other.busy_to else " with no end date"
        raise AssignmentConflictError(
            f"Unit {unit_number} of {requirement.requirement_reference} already has a machine ({other.assignment_reference}) "
            f"from {format_contract_date(other.busy_from)}{until}. Choose other dates, or replace that machine."
        )


def _decide(
    db: Session,
    *,
    asset_public_id: str,
    site: SiteFacts,
    start: date,
    end: date | None,
    user_public_id: str,
    requested_for_type: str,
    requested_for_public_id: str,
) -> Answer:
    """Eligibility's decision, stored in this transaction (ELA-001); the caller keeps its public id."""
    state_code, central = require_site(site)
    try:
        decision_public_id, check = record_decision(
            db,
            asset_public_id=asset_public_id,
            state_code=state_code,
            central_government_site=central,
            period_from=start,
            period_to=end,
            requested_by=user_public_id,
            requested_for_type=requested_for_type,
            requested_for_public_id=requested_for_public_id,
        )
    except EligibilityValidationError as exc:
        raise AssignmentValidationError(str(exc)) from exc
    return answer_from_check(check, decision_public_id=decision_public_id)


def _judge(answers: list[tuple[str, str, Answer]], *, accept_warnings: bool) -> None:
    """Never turn "cannot be allocated" into an allocation, nor "needs approval" while no approval can be given
    (ELA-001, Q2); a warning needs the user's confirmation. Each is refused naming every reason, and the caller's
    transaction rolls back, so a refused decision is not stored."""
    blocked = [(label, asset, answer) for label, asset, answer in answers if answer.overall_code in BLOCKING_ANSWERS]
    if blocked:
        raise AssignmentValidationError(
            " ".join(
                f"{label} cannot be allocated: {describe_problems(answer, asset_public_id=asset)}." for label, asset, answer in blocked
            )
        )
    warned = [(label, asset, answer) for label, asset, answer in answers if answer.overall_code == "WARNING"]
    if warned and not accept_warnings:
        raise AssignmentConflictError(
            " ".join(
                f"{label} can be allocated only with a warning: {describe_problems(answer, asset_public_id=asset)}."
                for label, asset, answer in warned
            )
            + " Tick \"I have seen these warnings\" and try again."
        )


def _integrity_conflict(exc: IntegrityError) -> AssignmentConflictError | None:
    """The database's backstop for two writes at once: the first valid commitment wins, the other is told to look
    again (RPA-001)."""
    constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
    messages = {
        "ex_resource_assignment_machine_overlap": "Someone has just allocated this machine for some of these days. Look again and choose another.",
        "ex_resource_assignment_unit_overlap": "Someone has just filled this unit for some of these days. Reload and look again.",
        "ex_resource_assignment_kit_piece_overlap": "Someone has just listed one of these pieces for some of these days. Look again.",
    }
    return AssignmentConflictError(messages[constraint]) if constraint in messages else None


def _one(db: Session, public_id: str) -> AssignmentResponse:
    row = repo.get_assignment_row(db, public_id=public_id)
    assert row is not None
    return build_assignments(db, [row], detail=True)[0]


# --- Allocating (design section 6.3) ------------------------------------------------------------------------


def create_assignment(
    db: Session, *, payload: AssignmentCreate, user_public_id: str | None, may_set_billing_cycle: bool
) -> AssignmentActionResponse:
    user = _require_user(user_public_id)
    key = _request_key(payload.create_request_key)
    cycle = _billing_cycle(payload.billing_cycle_code)
    if cycle is not None and not may_set_billing_cycle:
        raise AssignmentForbiddenError("Setting the billing cycle needs the permission to change billing terms.")
    notes = _clean(payload.notes)
    fingerprint = _fingerprint(payload)
    work_order_public_id = load_requirement(db, payload.requirement_public_id).work_order_public_id
    try:
        with rollback_on_error(db):
            _hold_work_order_open(db, work_order_public_id)
            _lock_requirement(db, payload.requirement_public_id)
            repo.take_write_lock(db)
            if _claim(db, key, kind=REQUEST_ALLOCATE, requirement_public_id=str(payload.requirement_public_id), fingerprint=fingerprint, user=user):
                db.rollback()
                return _replayed(db, key, kind=REQUEST_ALLOCATE)
            requirement = load_requirement(db, payload.requirement_public_id)
            _usable_requirement(requirement)
            if not 1 <= payload.unit_number <= requirement.units_required:
                raise AssignmentValidationError(
                    f"{requirement.requirement_reference} asks for {requirement.units_required} machine(s); unit "
                    f"{payload.unit_number} is not one of them."
                )
            end = check_period(requirement, payload.planned_from, payload.planned_to)
            site = site_facts(db, requirement)
            require_site(site)
            machine = _fitting_machine(db, requirement, payload.machine_public_id)
            _refuse_overlaps(
                db, machine=machine, requirement=requirement, unit_number=payload.unit_number,
                start=payload.planned_from, end=end, excluding=[],
            )
            public_id = str(uuid4())
            answer = _decide(
                db, asset_public_id=machine.asset_public_id, site=site, start=payload.planned_from, end=end,
                user_public_id=user, requested_for_type=DECISION_FOR_ASSIGNMENT, requested_for_public_id=public_id,
            )
            _judge([(_label(machine), machine.asset_public_id, answer)], accept_warnings=payload.accept_warnings)
            now = _now()
            assignment_id = repo.insert_assignment(
                db,
                values={
                    "assignment_public_id": public_id,
                    "resource_requirement_public_id": str(requirement.requirement_public_id),
                    "unit_number": payload.unit_number,
                    "work_order_public_id": str(requirement.work_order_public_id),
                    "work_order_code": requirement.work_order_code,
                    "work_order_line_public_id": str(requirement.work_order_line_public_id),
                    "work_order_line_number": requirement.work_order_line_number,
                    "source_offer_line_public_id": (
                        str(requirement.source_offer_line_public_id) if requirement.source_offer_line_public_id else None
                    ),
                    **_machine_snapshot(machine),
                    "planned_from": payload.planned_from,
                    "planned_to": end,
                    "assignment_status_code": STATUS_HELD,
                    "billing_cycle_code": cycle,
                    "billing_cycle_set_by": user if cycle else None,
                    "billing_cycle_set_at": now if cycle else None,
                    "decision_public_id": answer.decision_public_id,
                    "notes": notes,
                    "create_request_key": key,
                    "created_by": user,
                    "created_at": now,
                    "updated_by": user,
                    "updated_at": now,
                },
            )
            _insert_trip_one(db, assignment_id=assignment_id, user=user, at=now)
            refresh_requirement_fulfilment(db, requirement.requirement_public_id, current_user_public_id=user)
            response = _one(db, public_id)
            event = _held_event(db, response=response, answer=answer, user=user, replaces=None)
            db.commit()
    except IntegrityError as exc:
        return _after_key_race(db, exc, key, kind=REQUEST_ALLOCATE, fingerprint=fingerprint)
    return AssignmentActionResponse(assignment=response, events=[event])


def _machine_snapshot(machine: AllocationAsset) -> dict[str, Any]:
    """The machine as allocated (RMR-001): what the history shows even if it is later renumbered or re-rated."""
    return {
        "equipment_asset_public_id": machine.asset_public_id,
        "allocated_machine_number": machine.machine_number,
        "allocated_class_code": machine.class_code,
        "allocated_type_code": machine.type_code,
        "allocated_model_public_id": machine.model_public_id,
        "allocated_asset_version": machine.asset_version,
    }


def _insert_trip_one(db: Session, *, assignment_id: int, user: str, at: datetime) -> None:
    repo.insert_trip(
        db,
        values={
            "trip_public_id": str(uuid4()),
            "resource_assignment_id": assignment_id,
            "trip_number": 1,
            "goes_on": None,
            "note": None,
            "created_by": user,
            "created_at": at,
        },
    )


def _held_event(
    db: Session, *, response: AssignmentResponse, answer: Answer, user: str, replaces: dict[str, Any] | None
) -> dict[str, Any]:
    return _event(
        db,
        event_name=EVENT_HELD,
        assignment_public_id=response.assignment_public_id,
        user_public_id=user,
        status_before=None,
        status_after=STATUS_HELD,
        reason="Machine held for a Work Order's requirement.",
        payload={
            "assignment_public_id": response.assignment_public_id,
            "assignment_reference": response.assignment_reference,
            "requirement_public_id": str(response.requirement.requirement_public_id),
            "work_order_public_id": str(response.work_order_public_id),
            "work_order_line_public_id": str(response.work_order_line_public_id),
            "source_offer_line_public_id": (
                str(response.source_offer_line_public_id) if response.source_offer_line_public_id else None
            ),
            "unit_number": response.unit_number,
            "machine_public_id": response.machine.asset_public_id if response.machine else None,
            "machine_reference": response.machine.asset_reference if response.machine else None,
            "machine_version": response.allocated_asset_version,
            "planned_from": _date(response.planned_from),
            "planned_to": _date(response.planned_to),
            "billing_cycle_code": response.billing_cycle_code,
            "decision_public_id": answer.decision_public_id,
            "decision_overall_code": answer.overall_code,
            "replaces_assignment_public_id": str(replaces["assignment_public_id"]) if replaces else None,
        },
    )


# --- Replacing (6.6), freeing (6.7) and changing dates (6.8) ----------------------------------------------


def replace_assignment(
    db: Session, *, public_id: UUID, payload: AssignmentReplace, user_public_id: str | None, may_set_billing_cycle: bool
) -> AssignmentActionResponse:
    user = _require_user(user_public_id)
    key = _request_key(payload.create_request_key)
    reason, note = _reason(payload.reason_code, payload.note, allowed=REPLACEMENT_REASON_CODES, what="replaced")
    cycle_given = "billing_cycle_code" in payload.model_fields_set
    cycle = _billing_cycle(payload.billing_cycle_code) if cycle_given else None
    if cycle_given and not may_set_billing_cycle:
        raise AssignmentForbiddenError("Setting the billing cycle needs the permission to change billing terms.")
    fingerprint = _fingerprint(payload, acts_on=public_id)
    owner = _owner_of(db, public_id)
    requirement_public_id = str(owner["resource_requirement_public_id"])
    try:
        with rollback_on_error(db):
            _hold_work_order_open(db, owner["work_order_public_id"])
            _lock_requirement(db, requirement_public_id)
            repo.take_write_lock(db)
            if _claim(db, key, kind=REQUEST_REPLACE, requirement_public_id=requirement_public_id, fingerprint=fingerprint, user=user):
                db.rollback()
                return _replayed(db, key, kind=REQUEST_REPLACE, acts_on=public_id)
            old = _locked_held(db, public_id, payload.expected_assignment_version, action="replaced")
            if str(old["equipment_asset_public_id"]) == str(payload.machine_public_id):
                raise AssignmentValidationError("Choose a different machine: the replacement cannot be the same machine.")
            old_end = effective_end(old["planned_to"], old["ended_on"])
            if payload.replace_from == old["planned_from"] and _has_started(old):
                raise AssignmentValidationError(
                    f"{old['assignment_reference']} started on {format_contract_date(old['planned_from'])}, so its days stay on "
                    "the record: the replacement must start after its first day. If it was recorded by mistake, free it as "
                    "Recorded by mistake and allocate again."
                )
            if payload.replace_from < old["planned_from"] or (old_end is not None and payload.replace_from > old_end):
                until = format_contract_date(old_end) if old_end else "with no end date"
                raise AssignmentValidationError(
                    f"The replacement must start on a day of {old['assignment_reference']}: from "
                    f"{format_contract_date(old['planned_from'])} to {until}."
                )
            requirement = load_requirement(db, requirement_public_id)
            _usable_requirement(requirement)
            new_to = payload.planned_to if "planned_to" in payload.model_fields_set else old["planned_to"]
            end = check_period(requirement, payload.replace_from, new_to)
            site = site_facts(db, requirement)
            require_site(site)
            machine = _fitting_machine(db, requirement, payload.machine_public_id)
            now = _now()
            ended_on = payload.replace_from - ONE_DAY
            repo.update_assignment(
                db,
                assignment_id=int(old["id"]),
                values={
                    "assignment_status_code": STATUS_REPLACED,
                    "ended_on": ended_on,
                    "end_reason_code": reason,
                    "end_note": note,
                    "ended_by": user,
                    "ended_at": now,
                },
                user_public_id=user,
                at=now,
            )
            _refuse_overlaps(
                db, machine=machine, requirement=requirement, unit_number=int(old["unit_number"]),
                start=payload.replace_from, end=end, excluding=[],
            )
            new_public_id = str(uuid4())
            answer = _decide(
                db, asset_public_id=machine.asset_public_id, site=site, start=payload.replace_from, end=end,
                user_public_id=user, requested_for_type=DECISION_FOR_ASSIGNMENT, requested_for_public_id=new_public_id,
            )
            _judge([(_label(machine), machine.asset_public_id, answer)], accept_warnings=payload.accept_warnings)
            new_id = repo.insert_assignment(
                db,
                values={
                    "assignment_public_id": new_public_id,
                    "resource_requirement_public_id": str(old["resource_requirement_public_id"]),
                    "unit_number": int(old["unit_number"]),
                    "work_order_public_id": str(old["work_order_public_id"]),
                    "work_order_code": old["work_order_code"],
                    "work_order_line_public_id": str(old["work_order_line_public_id"]),
                    "work_order_line_number": int(old["work_order_line_number"]),
                    "source_offer_line_public_id": old["source_offer_line_public_id"],
                    **_machine_snapshot(machine),
                    "planned_from": payload.replace_from,
                    "planned_to": end,
                    "assignment_status_code": STATUS_HELD,
                    "replaces_assignment_id": int(old["id"]),
                    # The customer's invoice cycle for the position does not change with the machine.
                    "billing_cycle_code": cycle if cycle_given else old["billing_cycle_code"],
                    "billing_cycle_set_by": user if cycle_given else old["billing_cycle_set_by"],
                    "billing_cycle_set_at": now if cycle_given else old["billing_cycle_set_at"],
                    "decision_public_id": answer.decision_public_id,
                    "notes": None,
                    "create_request_key": key,
                    "created_by": user,
                    "created_at": now,
                    "updated_by": user,
                    "updated_at": now,
                },
            )
            _insert_trip_one(db, assignment_id=new_id, user=user, at=now)
            refresh_requirement_fulfilment(db, requirement_public_id, current_user_public_id=user)
            response = _one(db, new_public_id)
            replaced = _one(db, str(old["assignment_public_id"]))
            events = [
                _event(
                    db,
                    event_name=EVENT_REPLACED,
                    assignment_public_id=str(old["assignment_public_id"]),
                    user_public_id=user,
                    status_before=STATUS_HELD,
                    status_after=STATUS_REPLACED,
                    reason="Machine replaced on a Work Order.",
                    payload={
                        **_identity(old),
                        "replaced_by_assignment_public_id": new_public_id,
                        "replace_from": _date(payload.replace_from),
                        "ended_on": _date(ended_on),
                        "reason_code": reason,
                    },
                ),
                _held_event(db, response=response, answer=answer, user=user, replaces=old),
            ]
            db.commit()
    except IntegrityError as exc:
        return _after_key_race(db, exc, key, kind=REQUEST_REPLACE, fingerprint=fingerprint, acts_on=public_id)
    return AssignmentActionResponse(assignment=response, replaced=replaced, events=events)


def release_assignment(
    db: Session, *, public_id: UUID, payload: AssignmentRelease, user_public_id: str | None
) -> AssignmentActionResponse:
    """Free a held machine, with the reason: from the day after its last day on the job, or entirely when it never
    goes (design section 6.7)."""
    user = _require_user(user_public_id)
    reason, note = _reason(payload.reason_code, payload.note, allowed=RELEASE_REASON_CODES, what="freed")
    owner = _owner_of(db, public_id)
    requirement_public_id = str(owner["resource_requirement_public_id"])
    with rollback_on_error(db):
        _hold_work_order_open(db, owner["work_order_public_id"])
        _lock_requirement(db, requirement_public_id)
        repo.take_write_lock(db)
        row = _locked_held(db, public_id, payload.expected_assignment_version, action="freed")
        requirement = load_requirement(db, requirement_public_id)
        _usable_requirement(requirement)
        end = effective_end(row["planned_to"], row["ended_on"])
        if payload.last_day is None:
            if reason != RELEASE_RECORDED_BY_MISTAKE and _has_started(row):
                raise AssignmentValidationError(
                    f"{row['assignment_reference']} started on {format_contract_date(row['planned_from'])}, so its days stay "
                    "on the record: give its last day on the job. Leave the last day empty only when it was recorded by "
                    "mistake."
                )
            ended_on = row["planned_from"] - ONE_DAY
        else:
            if payload.last_day < row["planned_from"] or (end is not None and payload.last_day > end):
                until = format_contract_date(end) if end else "with no end date"
                raise AssignmentValidationError(
                    f"The last day must be a day of {row['assignment_reference']}: from "
                    f"{format_contract_date(row['planned_from'])} to {until}. Leave it empty if the machine never goes."
                )
            ended_on = payload.last_day
        event = _end(db, row, ended_on=ended_on, reason=reason, note=note, user=user)
        refresh_requirement_fulfilment(db, requirement_public_id, current_user_public_id=user)
        response = _one(db, str(row["assignment_public_id"]))
        db.commit()
    return AssignmentActionResponse(assignment=response, events=[event])


def _has_started(row: dict[str, Any]) -> bool:
    """Whether an allocation's first day has come (India date). From then its days stay on the record: only an
    allocation recorded by mistake may be erased (owner, 1 October 2026)."""
    return row["planned_from"] <= business_time.india_today()


def _end(db: Session, row: dict[str, Any], *, ended_on: date, reason: str, note: str | None, user: str) -> dict[str, Any]:
    """Free an allocation from the day after `ended_on`, cutting its kit with it."""
    now = _now()
    repo.update_assignment(
        db,
        assignment_id=int(row["id"]),
        values={
            "assignment_status_code": STATUS_RELEASED,
            "ended_on": ended_on,
            "end_reason_code": reason,
            "end_note": note,
            "ended_by": user,
            "ended_at": now,
        },
        user_public_id=user,
        at=now,
    )
    days = busy_days(row["planned_from"], row["planned_to"], ended_on)
    event = _event(
        db,
        event_name=EVENT_RELEASED,
        assignment_public_id=str(row["assignment_public_id"]),
        user_public_id=user,
        status_before=STATUS_HELD,
        status_after=STATUS_RELEASED,
        reason="Machine freed from a Work Order.",
        payload={
            **_identity(row),
            "last_day": _date(days.end) if days else None,
            "never_on_the_job": days is None,
            "reason_code": reason,
        },
    )
    return event


def change_assignment_dates(
    db: Session, *, public_id: UUID, payload: AssignmentDates, user_public_id: str | None
) -> AssignmentActionResponse:
    """New dates for a held allocation, checked as a new one is, with a fresh decision for the machine and every
    listed piece; its kit moves with it (design section 6.8). Once its first day has come, that day stays: only its
    last day can change, as freeing and replacing keep the days it held (owner, 1 October 2026)."""
    user = _require_user(user_public_id)
    owner = _owner_of(db, public_id)
    requirement_public_id = str(owner["resource_requirement_public_id"])
    try:
        with rollback_on_error(db):
            _hold_work_order_open(db, owner["work_order_public_id"])
            _lock_requirement(db, requirement_public_id)
            repo.take_write_lock(db)
            row = _locked_held(db, public_id, payload.expected_assignment_version, action="changed")
            requirement = load_requirement(db, requirement_public_id)
            _usable_requirement(requirement)
            if payload.planned_from != row["planned_from"] and _has_started(row):
                raise AssignmentValidationError(
                    f"{row['assignment_reference']} started on {format_contract_date(row['planned_from'])}, so its days stay "
                    "on the record: its first day cannot change, only its last day. If it was recorded by mistake, free it "
                    "as Recorded by mistake and allocate again."
                )
            end = check_period(requirement, payload.planned_from, payload.planned_to)
            if payload.planned_from == row["planned_from"] and end == row["planned_to"]:
                db.rollback()
                return AssignmentActionResponse(assignment=get_assignment(db, str(public_id)))
            window = Days(payload.planned_from, end)
            trips = repo.list_trip_rows(db, assignment_ids=[int(row["id"])])
            listed = [
                item for item in repo.list_kit_rows(db, assignment_ids=[int(row["id"])]) if item["line_status_code"] == KIT_LINE_LISTED
            ]
            # Every later trip, with kit or without, stays within the allocation's days (8A-R1-004). A later trip can
            # be neither moved nor removed yet, so the dates keep it.
            for trip in trips:
                if trip["goes_on"] is not None and not window.contains(Days(trip["goes_on"], trip["goes_on"])):
                    raise AssignmentValidationError(
                        f"Trip (Own Load) {trip['trip_number']} goes on {format_contract_date(trip['goes_on'])}, outside the new "
                        "dates. A Trip (Own Load) cannot be moved or removed yet: keep that day within the allocation's dates."
                    )
            site = site_facts(db, requirement)
            require_site(site)
            machine = _fitting_machine(db, requirement, str(row["equipment_asset_public_id"]))
            _refuse_overlaps(
                db, machine=machine, requirement=requirement, unit_number=int(row["unit_number"]),
                start=payload.planned_from, end=end, excluding=[int(row["id"])],
            )
            kit_days = {
                int(item["id"]): Days(
                    payload.planned_from if int(item["trip_number"]) == 1 else item["busy_from"], end
                )
                for item in listed
            }
            _refuse_kit_overlaps(db, listed, kit_days, owner=row)
            answers = [
                (
                    _label(machine),
                    machine.asset_public_id,
                    _decide(
                        db, asset_public_id=machine.asset_public_id, site=site, start=payload.planned_from, end=end,
                        user_public_id=user, requested_for_type=DECISION_FOR_ASSIGNMENT,
                        requested_for_public_id=str(row["assignment_public_id"]),
                    ),
                )
            ]
            kit_answers = _decide_kit(db, listed, kit_days, site=site, user=user)
            _judge(answers + [(label, asset, answer) for _line, label, asset, answer in kit_answers], accept_warnings=payload.accept_warnings)
            now = _now()
            repo.update_assignment(
                db,
                assignment_id=int(row["id"]),
                values={"planned_from": payload.planned_from, "planned_to": end, "decision_public_id": answers[0][2].decision_public_id},
                user_public_id=user,
                at=now,
            )
            for line_id, _label_text, _asset, answer in kit_answers:
                repo.set_kit_decision(db, kit_line_id=line_id, decision_public_id=str(answer.decision_public_id))
            refresh_requirement_fulfilment(db, requirement_public_id, current_user_public_id=user)
            response = _one(db, str(row["assignment_public_id"]))
            event = _event(
                db,
                event_name=EVENT_DATES_CHANGED,
                assignment_public_id=str(row["assignment_public_id"]),
                user_public_id=user,
                status_before=STATUS_HELD,
                status_after=STATUS_HELD,
                reason="Allocation dates changed.",
                payload={
                    **_identity(row),
                    "planned_from_before": _date(row["planned_from"]),
                    "planned_to_before": _date(row["planned_to"]),
                    "planned_from": _date(payload.planned_from),
                    "planned_to": _date(end),
                    "decision_public_id": answers[0][2].decision_public_id,
                    "decision_overall_code": answers[0][2].overall_code,
                    "kit_lines_checked": len(kit_answers),
                },
            )
            db.commit()
    except IntegrityError as exc:
        db.rollback()
        conflict = _integrity_conflict(exc)
        if conflict is not None:
            raise conflict from exc
        raise
    return AssignmentActionResponse(assignment=response, events=[event])


def _refuse_kit_overlaps(
    db: Session, listed: list[dict[str, Any]], kit_days: dict[int, Days], *, owner: dict[str, Any]
) -> None:
    """With the allocation's new dates, every listed piece must still be free: its own lines on their new days and
    every other listed line of it, never more at once than it holds (1 for a piece tracked one by one)."""
    if not listed:
        return
    window = Days(min(days.start for days in kit_days.values()), None)
    own_ids = [int(item["id"]) for item in listed]
    others = repo.list_listed_kit_overlaps(
        db, piece_public_ids=sorted({str(item["equipment_asset_public_id"]) for item in listed}), start=window.start, end=None,
        excluding=own_ids,
    )
    for piece_public_id in sorted({str(item["equipment_asset_public_id"]) for item in listed}):
        piece = allocation_asset(db, piece_public_id)
        held = piece.quantity if piece else 1
        lines = [(Days(row["busy_from"], row["busy_to"]), int(row["quantity"])) for row in others if str(row["equipment_asset_public_id"]) == piece_public_id]
        lines += [(kit_days[int(item["id"])], int(item["quantity"])) for item in listed if str(item["equipment_asset_public_id"]) == piece_public_id]
        if most_in_use(lines, window) > held:
            reference = piece.asset_reference if piece else piece_public_id
            raise AssignmentConflictError(
                f"{reference} is listed on another allocation for some of the new days. Remove it from one list first."
            )


def _decide_kit(
    db: Session, listed: list[dict[str, Any]], kit_days: dict[int, Days], *, site: SiteFacts, user: str
) -> list[tuple[int, str, str, Answer]]:
    decided: list[tuple[int, str, str, Answer]] = []
    for item in listed:
        days = kit_days[int(item["id"])]
        if days.end is not None and days.end < days.start:
            continue
        piece_public_id = str(item["equipment_asset_public_id"])
        piece = allocation_asset(db, piece_public_id)
        label = piece.asset_reference if piece else piece_public_id
        decided.append(
            (
                int(item["id"]),
                label,
                piece_public_id,
                _decide(
                    db, asset_public_id=piece_public_id, site=site, start=days.start, end=days.end, user_public_id=user,
                    requested_for_type=DECISION_FOR_KIT_LINE, requested_for_public_id=str(item["kit_line_public_id"]),
                ),
            )
        )
    return decided


# --- Checking again (6.4) and the billing cycle (6.9) ----------------------------------------------------


def check_assignment_again(
    db: Session, *, public_id: UUID, payload: AssignmentVersion, user_public_id: str | None
) -> AssignmentActionResponse:
    """Store a fresh decision for the machine and every listed piece, for the site as it now is. A "cannot be
    allocated" answer is stored too: the allocation stays held, shows it, and waits for renewal, replacement or
    freeing - never freed automatically."""
    user = _require_user(user_public_id)
    owner = _owner_of(db, public_id)
    with rollback_on_error(db):
        _hold_work_order_open(db, owner["work_order_public_id"])
        _lock_requirement(db, owner["resource_requirement_public_id"])
        repo.take_write_lock(db)
        row, requirement = _held_on_open_work_order(db, public_id, payload.expected_assignment_version, action="checked again")
        site = site_facts(db, requirement)
        require_site(site)
        end = effective_end(row["planned_to"], row["ended_on"])
        answer = _decide(
            db, asset_public_id=str(row["equipment_asset_public_id"]), site=site, start=row["planned_from"], end=end,
            user_public_id=user, requested_for_type=DECISION_FOR_ASSIGNMENT, requested_for_public_id=str(row["assignment_public_id"]),
        )
        listed = [item for item in repo.list_kit_rows(db, assignment_ids=[int(row["id"])]) if item["line_status_code"] == KIT_LINE_LISTED]
        kit_answers = _decide_kit(
            db, listed, {int(item["id"]): Days(item["busy_from"], item["busy_to"]) for item in listed}, site=site, user=user
        )
        repo.update_assignment(
            db, assignment_id=int(row["id"]), values={"decision_public_id": answer.decision_public_id}, user_public_id=user, at=_now()
        )
        for line_id, _label_text, _asset, kit_answer in kit_answers:
            repo.set_kit_decision(db, kit_line_id=line_id, decision_public_id=str(kit_answer.decision_public_id))
        response = _one(db, str(row["assignment_public_id"]))
        event = _event(
            db,
            event_name=EVENT_CHECKED,
            assignment_public_id=str(row["assignment_public_id"]),
            user_public_id=user,
            status_before=STATUS_HELD,
            status_after=STATUS_HELD,
            reason="Allocation checked again.",
            payload={
                **_identity(row),
                "decision_public_id_before": str(row["decision_public_id"]),
                "decision_public_id": answer.decision_public_id,
                "decision_overall_code": answer.overall_code,
                "kit_lines_checked": len(kit_answers),
                "kit_answers": dict(Counter(kit_answer.overall_code for _l, _t, _a, kit_answer in kit_answers)),
            },
        )
        db.commit()
    return AssignmentActionResponse(assignment=response, events=[event])


def set_billing_cycle(
    db: Session, *, public_id: UUID, payload: AssignmentBillingCycle, user_public_id: str | None
) -> AssignmentActionResponse:
    """Weekly, monthly, or not stated yet (FRS 2.8.1; the owner's answer 21). The same cycle again records
    nothing. The route asks for WORK_ORDER_LINE_BILLING_TERMS_WRITE."""
    user = _require_user(user_public_id)
    cycle = _billing_cycle(payload.billing_cycle_code)
    owner = _owner_of(db, public_id)
    with rollback_on_error(db):
        _hold_work_order_open(db, owner["work_order_public_id"])
        _lock_requirement(db, owner["resource_requirement_public_id"])
        repo.take_write_lock(db)
        row, _requirement = _held_on_open_work_order(db, public_id, payload.expected_assignment_version, action="changed")
        if row["billing_cycle_code"] == cycle:
            db.rollback()
            return AssignmentActionResponse(assignment=get_assignment(db, str(public_id)))
        now = _now()
        repo.update_assignment(
            db,
            assignment_id=int(row["id"]),
            values={"billing_cycle_code": cycle, "billing_cycle_set_by": user, "billing_cycle_set_at": now},
            user_public_id=user,
            at=now,
        )
        response = _one(db, str(row["assignment_public_id"]))
        event = _event(
            db,
            event_name=EVENT_BILLING_CYCLE_SET,
            assignment_public_id=str(row["assignment_public_id"]),
            user_public_id=user,
            status_before=STATUS_HELD,
            status_after=STATUS_HELD,
            reason="Billing cycle recorded for an allocated machine.",
            payload={**_identity(row), "billing_cycle_before": row["billing_cycle_code"], "billing_cycle_code": cycle},
        )
        db.commit()
    return AssignmentActionResponse(assignment=response, events=[event])


# --- Trips and kit (6.10) -----------------------------------------------------------------------------------


def add_trip(db: Session, *, public_id: UUID, payload: TripCreate, user_public_id: str | None) -> AssignmentActionResponse:
    user = _require_user(user_public_id)
    note = _clean(payload.note)
    owner = _owner_of(db, public_id)
    with rollback_on_error(db):
        _hold_work_order_open(db, owner["work_order_public_id"])
        _lock_requirement(db, owner["resource_requirement_public_id"])
        repo.take_write_lock(db)
        row, _requirement = _held_on_open_work_order(db, public_id, payload.expected_assignment_version, action="changed")
        end = effective_end(row["planned_to"], row["ended_on"])
        if not Days(row["planned_from"], end).contains(Days(payload.goes_on, payload.goes_on)):
            until = format_contract_date(end) if end else "with no end date"
            raise AssignmentValidationError(
                f"A Trip (Own Load) goes on a day of {row['assignment_reference']}: "
                f"from {format_contract_date(row['planned_from'])} to {until}."
            )
        trips = repo.list_trip_rows(db, assignment_ids=[int(row["id"])])
        number = max((int(trip["trip_number"]) for trip in trips), default=0) + 1
        now = _now()
        repo.insert_trip(
            db,
            values={
                "trip_public_id": str(uuid4()),
                "resource_assignment_id": int(row["id"]),
                "trip_number": number,
                "goes_on": payload.goes_on,
                "note": note,
                "created_by": user,
                "created_at": now,
            },
        )
        repo.update_assignment(db, assignment_id=int(row["id"]), values={}, user_public_id=user, at=now)
        response = _one(db, str(row["assignment_public_id"]))
        event = _event(
            db,
            event_name=EVENT_TRIP_ADDED,
            assignment_public_id=str(row["assignment_public_id"]),
            user_public_id=user,
            status_before=STATUS_HELD,
            status_after=STATUS_HELD,
            reason="Trip (Own Load) added to an allocation.",
            payload={**_identity(row), "trip_number": number, "goes_on": _date(payload.goes_on)},
        )
        db.commit()
    return AssignmentActionResponse(assignment=response, events=[event])


def set_trip_note(
    db: Session, *, public_id: UUID, trip_number: int, payload: TripNote, user_public_id: str | None
) -> AssignmentActionResponse:
    """Say what a Trip (Own Load) carries - which part of the machine (owner, 29 September 2026: a crane may go in
    several loads). Trip 1 is written with the allocation, so this is how it is said for trip 1 too. Only the note
    changes: the trip's day, and so its kit's days, stay. The same note again records nothing; the note is not put
    in the event, as an allocation's notes are not."""
    user = _require_user(user_public_id)
    note = _clean(payload.note)
    owner = _owner_of(db, public_id)
    with rollback_on_error(db):
        _hold_work_order_open(db, owner["work_order_public_id"])
        _lock_requirement(db, owner["resource_requirement_public_id"])
        repo.take_write_lock(db)
        row, _requirement = _held_on_open_work_order(db, public_id, payload.expected_assignment_version, action="changed")
        trip = next(
            (item for item in repo.list_trip_rows(db, assignment_ids=[int(row["id"])]) if int(item["trip_number"]) == trip_number),
            None,
        )
        if trip is None:
            raise AssignmentNotFoundError(f"Trip (Own Load) {trip_number} not found on {row['assignment_reference']}.")
        if trip["note"] == note:
            db.rollback()
            return AssignmentActionResponse(assignment=get_assignment(db, str(public_id)))
        now = _now()
        repo.update_trip_note(db, trip_id=int(trip["id"]), note=note)
        repo.update_assignment(db, assignment_id=int(row["id"]), values={}, user_public_id=user, at=now)
        response = _one(db, str(row["assignment_public_id"]))
        event = _event(
            db,
            event_name=EVENT_TRIP_NOTE_CHANGED,
            assignment_public_id=str(row["assignment_public_id"]),
            user_public_id=user,
            status_before=STATUS_HELD,
            status_after=STATUS_HELD,
            reason="What a Trip (Own Load) carries was changed.",
            payload={**_identity(row), "trip_number": trip_number, "note_given": note is not None},
        )
        db.commit()
    return AssignmentActionResponse(assignment=response, events=[event])


def add_kit(db: Session, *, public_id: UUID, payload: KitAdd, user_public_id: str | None) -> AssignmentActionResponse:
    """List pieces on a trip: each must be kit held for the machine's model, active, and free over the trip's days
    to the allocation's end, and each is checked for eligibility on its own (ELG-1, section 6)."""
    user = _require_user(user_public_id)
    key = _request_key(payload.create_request_key)
    fingerprint = _fingerprint(payload, acts_on=public_id)
    asked_ids = [str(piece.piece_public_id) for piece in payload.pieces]
    if len(set(asked_ids)) != len(asked_ids):
        raise AssignmentValidationError("A piece is listed twice. List each piece once, with how many of a counted set go.")
    owner = _owner_of(db, public_id)
    try:
        with rollback_on_error(db):
            _hold_work_order_open(db, owner["work_order_public_id"])
            _lock_requirement(db, owner["resource_requirement_public_id"])
            repo.take_write_lock(db)
            if _claim(
                db, key, kind=REQUEST_KIT, requirement_public_id=str(owner["resource_requirement_public_id"]),
                fingerprint=fingerprint, user=user,
            ):
                db.rollback()
                return _replayed(db, key, kind=REQUEST_KIT, acts_on=public_id)
            row, requirement = _held_on_open_work_order(db, public_id, payload.expected_assignment_version, action="changed")
            trip = next(
                (item for item in repo.list_trip_rows(db, assignment_ids=[int(row["id"])]) if int(item["trip_number"]) == payload.trip_number),
                None,
            )
            if trip is None:
                raise AssignmentNotFoundError(f"Trip (Own Load) {payload.trip_number} not found on {row['assignment_reference']}.")
            window = kit_window(row, trip)
            site = site_facts(db, requirement)
            require_site(site)
            held = {piece.asset_public_id: piece for piece in kit_for_machine(db, str(row["equipment_asset_public_id"]))}
            pieces: list[tuple[AllocationAsset, int]] = []
            for asked in payload.pieces:
                piece = held.get(str(asked.piece_public_id))
                if piece is None:
                    known = allocation_asset(db, str(asked.piece_public_id))
                    if known is None:
                        raise AssignmentNotFoundError("Piece of kit not found.")
                    raise AssignmentValidationError(
                        f"{known.asset_reference} cannot go with this machine: it is not active kit held for the machine's model."
                    )
                if piece.tracking_code == "SINGLE" and asked.quantity != 1:
                    raise AssignmentValidationError(f"{piece.asset_reference} is one piece: list it with a quantity of 1.")
                pieces.append((piece, asked.quantity))
            availability = piece_availability(db, [piece for piece, _quantity in pieces], window)
            for piece, quantity in pieces:
                free, conflicts = availability[piece.asset_public_id]
                if quantity > free:
                    if piece.tracking_code == "SINGLE" and conflicts:
                        raise AssignmentConflictError(f"{describe_conflict(piece.asset_reference, conflicts[0])} Choose another piece.")
                    raise AssignmentConflictError(
                        f"Only {free} of {piece.asset_reference} are free over these days; {quantity} were asked for."
                    )
            now = _now()
            line_ids = [str(uuid4()) for _piece in pieces]
            answers = [
                (
                    piece.asset_reference,
                    piece.asset_public_id,
                    _decide(
                        db, asset_public_id=piece.asset_public_id, site=site, start=window.start, end=window.end,
                        user_public_id=user, requested_for_type=DECISION_FOR_KIT_LINE, requested_for_public_id=line_id,
                    ),
                )
                for (piece, _quantity), line_id in zip(pieces, line_ids)
            ]
            _judge(answers, accept_warnings=payload.accept_warnings)
            for position, ((piece, quantity), line_id, (_label_text, _asset, answer)) in enumerate(zip(pieces, line_ids, answers), 1):
                repo.insert_kit_line(
                    db,
                    values={
                        "kit_line_public_id": line_id,
                        "resource_assignment_id": int(row["id"]),
                        "resource_assignment_trip_id": int(trip["id"]),
                        "equipment_asset_public_id": piece.asset_public_id,
                        "listed_kit_model_public_id": piece.model_public_id,
                        "tracking_code": piece.tracking_code,
                        "quantity": quantity,
                        "line_status_code": KIT_LINE_LISTED,
                        "decision_public_id": answer.decision_public_id,
                        "busy_from": window.start,
                        "busy_to": window.end,
                        "create_request_key": key,
                        "create_request_position": position,
                        "created_by": user,
                        "created_at": now,
                    },
                )
            repo.update_assignment(db, assignment_id=int(row["id"]), values={}, user_public_id=user, at=now)
            response = _one(db, str(row["assignment_public_id"]))
            event = _event(
                db,
                event_name=EVENT_KIT_LISTED,
                assignment_public_id=str(row["assignment_public_id"]),
                user_public_id=user,
                status_before=STATUS_HELD,
                status_after=STATUS_HELD,
                reason="Kit listed to go to site with an allocated machine.",
                payload={
                    **_identity(row),
                    "trip_number": payload.trip_number,
                    "pieces": [
                        {
                            "kit_line_public_id": line_id,
                            "piece_public_id": piece.asset_public_id,
                            "piece_reference": piece.asset_reference,
                            "quantity": quantity,
                            "decision_public_id": answer.decision_public_id,
                            "decision_overall_code": answer.overall_code,
                        }
                        for (piece, quantity), line_id, (_l, _a, answer) in zip(pieces, line_ids, answers)
                    ],
                },
            )
            db.commit()
    except IntegrityError as exc:
        return _after_key_race(db, exc, key, kind=REQUEST_KIT, fingerprint=fingerprint, acts_on=public_id)
    return AssignmentActionResponse(assignment=response, events=[event])


def remove_kit_line(
    db: Session, *, public_id: UUID, kit_line_public_id: UUID, payload: AssignmentVersion, user_public_id: str | None
) -> AssignmentActionResponse:
    """Take a piece off the list before it goes: the line is kept, removed, with who and when."""
    user = _require_user(user_public_id)
    owner = _owner_of(db, public_id)
    with rollback_on_error(db):
        _hold_work_order_open(db, owner["work_order_public_id"])
        _lock_requirement(db, owner["resource_requirement_public_id"])
        repo.take_write_lock(db)
        row, _requirement = _held_on_open_work_order(db, public_id, payload.expected_assignment_version, action="changed")
        line = repo.get_kit_row(db, public_id=str(kit_line_public_id))
        if line is None or int(line["resource_assignment_id"]) != int(row["id"]):
            raise AssignmentNotFoundError("Kit line not found on this allocation.")
        if line["line_status_code"] == KIT_LINE_REMOVED:
            db.rollback()
            return AssignmentActionResponse(assignment=get_assignment(db, str(public_id)))
        now = _now()
        repo.remove_kit_line(db, kit_line_id=int(line["id"]), user_public_id=user, at=now)
        repo.update_assignment(db, assignment_id=int(row["id"]), values={}, user_public_id=user, at=now)
        response = _one(db, str(row["assignment_public_id"]))
        event = _event(
            db,
            event_name=EVENT_KIT_REMOVED,
            assignment_public_id=str(row["assignment_public_id"]),
            user_public_id=user,
            status_before=STATUS_HELD,
            status_after=STATUS_HELD,
            reason="Kit taken off an allocation's list.",
            payload={
                **_identity(row),
                "kit_line_public_id": str(line["kit_line_public_id"]),
                "piece_public_id": str(line["equipment_asset_public_id"]),
                "trip_number": int(line["trip_number"]),
                "quantity": int(line["quantity"]),
            },
        )
        db.commit()
    return AssignmentActionResponse(assignment=response, events=[event])


# --- What Resource Requirements asks of this module (its port) ------------------------------------------


class _AssignmentPort:
    """Registered with Resource Requirements when this module is loaded (resource_requirements/ports.py)."""

    def hold(self, db: Session) -> None:
        # The lock alone: the caller reads coverage to store a status and writes no allocation (8A-F3-003).
        repo.take_lock(db)

    def coverage(self, db: Session, requirements: list[RequirementToCover]) -> dict[str, Coverage]:
        # The days every allocation kept - held, replaced or freed - are the days its unit had a machine: a replaced
        # machine's days before the hand-over still covered the unit. One freed before it started kept none.
        rows = repo.list_rows_for_requirements(
            db, requirement_public_ids=[item.requirement_public_id for item in requirements]
        )
        held: dict[str, dict[int, list[Days]]] = {}
        for row in rows:
            days = busy_days(row["planned_from"], row["planned_to"], row["ended_on"])
            if days is not None:
                held.setdefault(str(row["resource_requirement_public_id"]), {}).setdefault(int(row["unit_number"]), []).append(days)
        result: dict[str, Coverage] = {}
        for item in requirements:
            by_unit = held.get(item.requirement_public_id, {})
            covered, with_machines = requirement_coverage(item.units_required, by_unit, item.required_from, item.planned_end)
            result[item.requirement_public_id] = Coverage(
                units_covered=covered,
                units_with_machines=with_machines,
                covered_unit_numbers=covered_units(item.units_required, by_unit, item.required_from, item.planned_end),
            )
        return result

    def release_for_cancelled_requirement(self, db: Session, *, requirement_public_id: str, user_public_id: str) -> int:
        """Free every machine held for a requirement being cancelled: from the day before it starts, or from today if
        it has started, keeping its history (WRR-001). The caller holds the requirement's row lock."""
        repo.take_write_lock(db)
        rows = repo.lock_held_rows_for_requirement(db, requirement_public_id=requirement_public_id)
        today = business_time.india_today()
        for row in rows:
            end = effective_end(row["planned_to"], row["ended_on"])
            if row["planned_from"] > today:
                ended_on = row["planned_from"] - ONE_DAY
            else:
                ended_on = today if end is None or end >= today else end
            _end(db, row, ended_on=ended_on, reason=RELEASE_REQUIREMENT_CANCELLED, note=None, user=user_public_id)
        return len(rows)


register_assignment_port(_AssignmentPort())


class _AllocationSource:
    """What Eligibility's reminders read of the allocations (ELG-2), registered as the port above is."""

    def hold(self, db: Session) -> None:
        # The lock alone: the transaction writes no allocation, so it is not marked as the service's (8A-F3-003).
        repo.take_lock(db)

    def held_for_reminders(self, db: Session, *, today: date) -> list[AllocatedAsset]:
        return held_for_reminders(db, today=today)


register_allocation_source(_AllocationSource())


class _KitListings:
    """What the Equipment Reference asks before a counted set of kit shrinks (TB-1 finding TB1-307), registered as the
    ports above are."""

    def hold(self, db: Session) -> None:
        # The lock alone: retiring kit writes no allocation (8A-F3-003). The Equipment Reference takes it before its own
        # lock, as Eligibility's "seen" marks do, so allocations always come first.
        repo.take_lock(db)

    def listed_from(self, db: Session, *, piece_public_id: str, from_day: date) -> ListedKit:
        rows = repo.list_listed_kit_overlaps(db, piece_public_ids=[piece_public_id], start=from_day, end=None, excluding=[])
        lines = [(Days(row["busy_from"], row["busy_to"]), int(row["quantity"])) for row in rows]
        return ListedKit(
            most_at_once=most_in_use(lines, Days(from_day, None)),
            allocation_references=tuple(sorted({str(row["assignment_reference"]) for row in rows})),
        )


register_kit_listing_source(_KitListings())
