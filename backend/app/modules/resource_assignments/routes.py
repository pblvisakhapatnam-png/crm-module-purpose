"""Resource Assignment API (8A core). docs/agent/contracts/resource-assignment-api-contract.md.

`/candidates` is registered before `/{public_id}`, so it is never read as an allocation's public id. Setting a
billing cycle asks for WORK_ORDER_LINE_BILLING_TERMS_WRITE: on its own route as that route's permission, and when
allocating or replacing, resolved by the service (`can_set_billing_cycle`) because the cycle is optional there:
route modules never read roles.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.authorization.contract import (
    RESOURCE_ASSIGNMENT_READ,
    RESOURCE_ASSIGNMENT_WRITE,
    WORK_ORDER_LINE_BILLING_TERMS_WRITE,
)
from app.modules.authorization.dependencies import require_permission
from app.modules.identity.schemas import AuthUser
from app.modules.resource_assignments.errors import (
    AssignmentConflictError,
    AssignmentForbiddenError,
    AssignmentNotFoundError,
    AssignmentValidationError,
)
from app.modules.resource_assignments.schemas import (
    AssignmentActionResponse,
    AssignmentBillingCycle,
    AssignmentCreate,
    AssignmentDates,
    AssignmentRelease,
    AssignmentReplace,
    AssignmentResponse,
    AssignmentVersion,
    CandidatesResponse,
    KitAdd,
    KitOptionsResponse,
    TripCreate,
    TripNote,
)
from app.modules.resource_assignments.service import (
    add_kit,
    can_set_billing_cycle,
    add_trip,
    change_assignment_dates,
    check_assignment_again,
    create_assignment,
    release_assignment,
    remove_kit_line,
    replace_assignment,
    set_billing_cycle,
    set_trip_note,
)
from app.modules.resource_assignments.views import find_candidates, get_assignment, kit_options, list_assignments

router = APIRouter(prefix="/api/resource-assignments", tags=["resource-assignments"])

_ERRORS = (AssignmentNotFoundError, AssignmentConflictError, AssignmentValidationError, AssignmentForbiddenError)


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, AssignmentNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, AssignmentConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, AssignmentForbiddenError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


def _user_public_id(user: AuthUser) -> str | None:
    value = getattr(user, "user_public_id", None) or getattr(user, "public_id", None)
    return str(value) if value else None


@router.get("", response_model=list[AssignmentResponse])
def list_assignments_endpoint(
    work_order_public_id: UUID | None = Query(default=None),
    requirement_public_id: UUID | None = Query(default=None),
    machine_public_id: UUID | None = Query(default=None),
    status_code: str | None = Query(default=None, max_length=20),
    starts_from: date | None = Query(default=None),
    starts_to: date | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    after: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(RESOURCE_ASSIGNMENT_READ)),
) -> list[AssignmentResponse]:
    try:
        return list_assignments(
            db,
            work_order_public_id=work_order_public_id,
            requirement_public_id=requirement_public_id,
            machine_public_id=machine_public_id,
            status_code=status_code,
            starts_from=starts_from,
            starts_to=starts_to,
            limit=limit,
            offset=offset,
            after=after,
        )
    except _ERRORS as exc:
        raise _http_error(exc) from exc


@router.get("/candidates", response_model=CandidatesResponse)
def find_candidates_endpoint(
    requirement_public_id: UUID = Query(...),
    unit_number: int = Query(..., ge=1, le=2_147_483_647),
    period_from: date | None = Query(default=None),
    period_to: date | None = Query(default=None),
    replacing_assignment_public_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(RESOURCE_ASSIGNMENT_READ)),
) -> CandidatesResponse:
    try:
        return find_candidates(
            db,
            requirement_public_id=requirement_public_id,
            unit_number=unit_number,
            period_from=period_from,
            period_to=period_to,
            replacing_assignment_public_id=replacing_assignment_public_id,
        )
    except _ERRORS as exc:
        raise _http_error(exc) from exc


@router.get("/{public_id}", response_model=AssignmentResponse)
def get_assignment_endpoint(
    public_id: UUID,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(RESOURCE_ASSIGNMENT_READ)),
) -> AssignmentResponse:
    try:
        return get_assignment(db, public_id)
    except _ERRORS as exc:
        raise _http_error(exc) from exc


@router.post("", response_model=AssignmentActionResponse, status_code=status.HTTP_201_CREATED)
def create_assignment_endpoint(
    payload: AssignmentCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(RESOURCE_ASSIGNMENT_WRITE)),
) -> AssignmentActionResponse:
    try:
        return create_assignment(
            db,
            payload=payload,
            user_public_id=_user_public_id(current_user),
            may_set_billing_cycle=can_set_billing_cycle(db, current_user),
        )
    except _ERRORS as exc:
        raise _http_error(exc) from exc


@router.post("/{public_id}/replace", response_model=AssignmentActionResponse, status_code=status.HTTP_201_CREATED)
def replace_assignment_endpoint(
    public_id: UUID,
    payload: AssignmentReplace,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(RESOURCE_ASSIGNMENT_WRITE)),
) -> AssignmentActionResponse:
    try:
        return replace_assignment(
            db,
            public_id=public_id,
            payload=payload,
            user_public_id=_user_public_id(current_user),
            may_set_billing_cycle=can_set_billing_cycle(db, current_user),
        )
    except _ERRORS as exc:
        raise _http_error(exc) from exc


@router.post("/{public_id}/release", response_model=AssignmentActionResponse)
def release_assignment_endpoint(
    public_id: UUID,
    payload: AssignmentRelease,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(RESOURCE_ASSIGNMENT_WRITE)),
) -> AssignmentActionResponse:
    try:
        return release_assignment(db, public_id=public_id, payload=payload, user_public_id=_user_public_id(current_user))
    except _ERRORS as exc:
        raise _http_error(exc) from exc


@router.put("/{public_id}/dates", response_model=AssignmentActionResponse)
def change_assignment_dates_endpoint(
    public_id: UUID,
    payload: AssignmentDates,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(RESOURCE_ASSIGNMENT_WRITE)),
) -> AssignmentActionResponse:
    try:
        return change_assignment_dates(db, public_id=public_id, payload=payload, user_public_id=_user_public_id(current_user))
    except _ERRORS as exc:
        raise _http_error(exc) from exc


@router.post("/{public_id}/check", response_model=AssignmentActionResponse)
def check_assignment_again_endpoint(
    public_id: UUID,
    payload: AssignmentVersion,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(RESOURCE_ASSIGNMENT_WRITE)),
) -> AssignmentActionResponse:
    try:
        return check_assignment_again(db, public_id=public_id, payload=payload, user_public_id=_user_public_id(current_user))
    except _ERRORS as exc:
        raise _http_error(exc) from exc


@router.put("/{public_id}/billing-cycle", response_model=AssignmentActionResponse)
def set_billing_cycle_endpoint(
    public_id: UUID,
    payload: AssignmentBillingCycle,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(WORK_ORDER_LINE_BILLING_TERMS_WRITE)),
) -> AssignmentActionResponse:
    try:
        return set_billing_cycle(db, public_id=public_id, payload=payload, user_public_id=_user_public_id(current_user))
    except _ERRORS as exc:
        raise _http_error(exc) from exc


@router.get("/{public_id}/kit-options", response_model=KitOptionsResponse)
def kit_options_endpoint(
    public_id: UUID,
    trip_number: int = Query(default=1, ge=1, le=2_147_483_647),
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(RESOURCE_ASSIGNMENT_READ)),
) -> KitOptionsResponse:
    try:
        return kit_options(db, assignment_public_id=public_id, trip_number=trip_number)
    except _ERRORS as exc:
        raise _http_error(exc) from exc


@router.post("/{public_id}/trips", response_model=AssignmentActionResponse, status_code=status.HTTP_201_CREATED)
def add_trip_endpoint(
    public_id: UUID,
    payload: TripCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(RESOURCE_ASSIGNMENT_WRITE)),
) -> AssignmentActionResponse:
    try:
        return add_trip(db, public_id=public_id, payload=payload, user_public_id=_user_public_id(current_user))
    except _ERRORS as exc:
        raise _http_error(exc) from exc


@router.put("/{public_id}/trips/{trip_number}/note", response_model=AssignmentActionResponse)
def set_trip_note_endpoint(
    public_id: UUID,
    trip_number: int,
    payload: TripNote,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(RESOURCE_ASSIGNMENT_WRITE)),
) -> AssignmentActionResponse:
    try:
        return set_trip_note(
            db, public_id=public_id, trip_number=trip_number, payload=payload, user_public_id=_user_public_id(current_user)
        )
    except _ERRORS as exc:
        raise _http_error(exc) from exc


@router.post("/{public_id}/kit", response_model=AssignmentActionResponse, status_code=status.HTTP_201_CREATED)
def add_kit_endpoint(
    public_id: UUID,
    payload: KitAdd,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(RESOURCE_ASSIGNMENT_WRITE)),
) -> AssignmentActionResponse:
    try:
        return add_kit(db, public_id=public_id, payload=payload, user_public_id=_user_public_id(current_user))
    except _ERRORS as exc:
        raise _http_error(exc) from exc


@router.post("/{public_id}/kit/{kit_line_public_id}/remove", response_model=AssignmentActionResponse)
def remove_kit_line_endpoint(
    public_id: UUID,
    kit_line_public_id: UUID,
    payload: AssignmentVersion,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(RESOURCE_ASSIGNMENT_WRITE)),
) -> AssignmentActionResponse:
    try:
        return remove_kit_line(
            db,
            public_id=public_id,
            kit_line_public_id=kit_line_public_id,
            payload=payload,
            user_public_id=_user_public_id(current_user),
        )
    except _ERRORS as exc:
        raise _http_error(exc) from exc
