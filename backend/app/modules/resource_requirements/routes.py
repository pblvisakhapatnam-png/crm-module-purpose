"""Resource Requirement API (WRR-001). docs/agent/contracts/resource-requirement-api-contract.md.

`/defaults` is registered before `/{public_id}`, so it is never read as a requirement's public id.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.authorization.contract import RESOURCE_REQUIREMENT_READ, RESOURCE_REQUIREMENT_WRITE
from app.modules.authorization.dependencies import require_permission
from app.modules.identity.schemas import AuthUser
from app.modules.resource_requirements.schemas import (
    ResourceRequirementActionResponse,
    ResourceRequirementCancel,
    ResourceRequirementCreate,
    ResourceRequirementDefaultsResponse,
    ResourceRequirementResponse,
    ResourceRequirementUpdate,
)
from app.modules.resource_requirements.service import (
    ResourceRequirementConflictError,
    ResourceRequirementLineNotFoundError,
    ResourceRequirementNotFoundError,
    ResourceRequirementValidationError,
    cancel_resource_requirement,
    create_resource_requirement,
    get_resource_requirement,
    get_resource_requirement_defaults,
    list_resource_requirements,
    update_resource_requirement,
)

router = APIRouter(prefix="/api/resource-requirements", tags=["resource-requirements"])

_ERRORS = (
    ResourceRequirementNotFoundError,
    ResourceRequirementLineNotFoundError,
    ResourceRequirementConflictError,
    ResourceRequirementValidationError,
)


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, (ResourceRequirementNotFoundError, ResourceRequirementLineNotFoundError)):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, ResourceRequirementConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


def _user_public_id(user: AuthUser) -> str | None:
    value = getattr(user, "user_public_id", None) or getattr(user, "public_id", None)
    return str(value) if value else None


@router.get("", response_model=list[ResourceRequirementResponse])
def list_resource_requirements_endpoint(
    work_order_public_id: UUID | None = Query(default=None),
    work_order_line_public_id: UUID | None = Query(default=None),
    status_code: str | None = Query(default=None, max_length=20),
    equipment_class_code: str | None = Query(default=None, max_length=50),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(RESOURCE_REQUIREMENT_READ)),
) -> list[ResourceRequirementResponse]:
    try:
        return list_resource_requirements(
            db,
            work_order_public_id=work_order_public_id,
            work_order_line_public_id=work_order_line_public_id,
            status_code=status_code,
            equipment_class_code=equipment_class_code,
            limit=limit,
            offset=offset,
        )
    except _ERRORS as exc:
        raise _http_error(exc) from exc


@router.get("/defaults", response_model=ResourceRequirementDefaultsResponse)
def get_resource_requirement_defaults_endpoint(
    work_order_line_public_id: UUID = Query(...),
    required_from: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(RESOURCE_REQUIREMENT_READ)),
) -> ResourceRequirementDefaultsResponse:
    try:
        return get_resource_requirement_defaults(
            db, work_order_line_public_id=work_order_line_public_id, required_from=required_from
        )
    except _ERRORS as exc:
        raise _http_error(exc) from exc


@router.get("/{public_id}", response_model=ResourceRequirementResponse)
def get_resource_requirement_endpoint(
    public_id: UUID,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(RESOURCE_REQUIREMENT_READ)),
) -> ResourceRequirementResponse:
    try:
        return get_resource_requirement(db, public_id)
    except _ERRORS as exc:
        raise _http_error(exc) from exc


@router.post("", response_model=ResourceRequirementActionResponse, status_code=status.HTTP_201_CREATED)
def create_resource_requirement_endpoint(
    payload: ResourceRequirementCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(RESOURCE_REQUIREMENT_WRITE)),
) -> ResourceRequirementActionResponse:
    try:
        return create_resource_requirement(db, payload=payload, current_user_public_id=_user_public_id(current_user))
    except _ERRORS as exc:
        raise _http_error(exc) from exc


@router.put("/{public_id}", response_model=ResourceRequirementActionResponse)
def update_resource_requirement_endpoint(
    public_id: UUID,
    payload: ResourceRequirementUpdate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(RESOURCE_REQUIREMENT_WRITE)),
) -> ResourceRequirementActionResponse:
    try:
        return update_resource_requirement(
            db, public_id=public_id, payload=payload, current_user_public_id=_user_public_id(current_user)
        )
    except _ERRORS as exc:
        raise _http_error(exc) from exc


@router.post("/{public_id}/cancel", response_model=ResourceRequirementActionResponse)
def cancel_resource_requirement_endpoint(
    public_id: UUID,
    payload: ResourceRequirementCancel,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(RESOURCE_REQUIREMENT_WRITE)),
) -> ResourceRequirementActionResponse:
    try:
        return cancel_resource_requirement(
            db, public_id=public_id, payload=payload, current_user_public_id=_user_public_id(current_user)
        )
    except _ERRORS as exc:
        raise _http_error(exc) from exc
