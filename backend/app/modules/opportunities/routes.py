from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.authorization.contract import (
    OPPORTUNITY_ACCOUNT_REPAIR,
    OPPORTUNITY_CREATE as OPPORTUNITY_CREATE_PERMISSION,
    OPPORTUNITY_READ as OPPORTUNITY_READ_PERMISSION,
    OPPORTUNITY_UPDATE as OPPORTUNITY_UPDATE_PERMISSION,
)
from app.modules.authorization.dependencies import require_permission
from app.modules.identity.schemas import AuthUser
from app.modules.opportunities.schemas import (
    OpportunityAccountRepairRequest,
    OpportunityAccountRepairResponse,
    OpportunityCreate,
    OpportunityCreatedResponse,
    OpportunityResponse,
    OpportunityUpdate,
    OpportunityUpdatedResponse,
)
from app.modules.opportunities.service import (
    OpportunityNotFoundError,
    OpportunityValidationError,
    create_opportunity,
    get_opportunity,
    list_opportunities,
    repair_opportunity_account,
    update_opportunity,
)

router = APIRouter(prefix="/api/opportunities", tags=["opportunities"])


def _user_public_id(user: AuthUser) -> str | None:
    value = getattr(user, "user_public_id", None) or getattr(user, "public_id", None)
    return str(value) if value else None


@router.post("", response_model=OpportunityCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_opportunity_endpoint(
    payload: OpportunityCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(OPPORTUNITY_CREATE_PERMISSION)),
) -> OpportunityCreatedResponse:
    try:
        return create_opportunity(
            db,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except OpportunityValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get("", response_model=list[OpportunityResponse])
def list_opportunities_endpoint(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
    status_code: str | None = Query(default=None, max_length=50),
    opportunity_source: str | None = Query(default=None, max_length=50),
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(OPPORTUNITY_READ_PERMISSION)),
) -> list[OpportunityResponse]:
    return list_opportunities(
        db,
        limit=limit,
        offset=offset,
        status_code=status_code,
        opportunity_source=opportunity_source,
    )


@router.get("/{public_id}", response_model=OpportunityResponse)
def get_opportunity_endpoint(
    public_id: UUID,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(OPPORTUNITY_READ_PERMISSION)),
) -> OpportunityResponse:
    try:
        return get_opportunity(db, public_id)
    except OpportunityNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.put("/{public_id}", response_model=OpportunityUpdatedResponse)
def update_opportunity_endpoint(
    public_id: UUID,
    payload: OpportunityUpdate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(OPPORTUNITY_UPDATE_PERMISSION)),
) -> OpportunityUpdatedResponse:
    try:
        return update_opportunity(
            db,
            public_id=public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except OpportunityNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except OpportunityValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.post("/{public_id}/account-repair", response_model=OpportunityAccountRepairResponse)
def repair_opportunity_account_endpoint(
    public_id: UUID,
    payload: OpportunityAccountRepairRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(OPPORTUNITY_ACCOUNT_REPAIR)),
) -> OpportunityAccountRepairResponse:
    try:
        return repair_opportunity_account(
            db,
            public_id=public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except OpportunityNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except OpportunityValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
