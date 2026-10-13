from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.authorization.contract import (
    LEAD_ACTIVITY_CREATE,
    LEAD_CONVERT,
    LEAD_CREATE as LEAD_CREATE_PERMISSION,
    LEAD_QUALIFICATION_DECIDE,
    LEAD_READ as LEAD_READ_PERMISSION,
    LEAD_UPDATE as LEAD_UPDATE_PERMISSION,
)
from app.modules.authorization.dependencies import require_permission
from app.modules.identity.schemas import AuthUser
from app.modules.leads.schemas import (
    LeadActivityCreate,
    LeadActivityCreatedResponse,
    LeadActivityResponse,
    LeadConversionCreate,
    LeadConversionResponse,
    LeadCreate,
    LeadCreatedResponse,
    LeadQualificationDecision,
    LeadQualificationDecisionResponse,
    LeadResponse,
    LeadUpdate,
    LeadUpdatedResponse,
)
from app.modules.leads.service import (
    LeadNotFoundError,
    LeadValidationError,
    create_lead,
    convert_lead,
    create_lead_activity,
    decide_lead_qualification,
    get_lead,
    get_lead_activities,
    list_leads,
    update_lead,
)

router = APIRouter(prefix="/api/leads", tags=["leads"])


def _user_public_id(user: AuthUser) -> str | None:
    value = getattr(user, "user_public_id", None) or getattr(user, "public_id", None)
    return str(value) if value else None


@router.post("", response_model=LeadCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_lead_endpoint(
    payload: LeadCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(LEAD_CREATE_PERMISSION)),
) -> LeadCreatedResponse:
    try:
        return create_lead(
            db,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except LeadValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get("", response_model=list[LeadResponse])
def list_leads_endpoint(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
    status_code: str | None = Query(default=None, max_length=50),
    lead_source: str | None = Query(default=None, max_length=50),
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(LEAD_READ_PERMISSION)),
) -> list[LeadResponse]:
    return list_leads(db, limit=limit, offset=offset, status_code=status_code, lead_source=lead_source)


@router.get("/{public_id}/activities", response_model=list[LeadActivityResponse])
def list_lead_activities_endpoint(
    public_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(LEAD_READ_PERMISSION)),
) -> list[LeadActivityResponse]:
    try:
        return get_lead_activities(db, public_id, limit=limit)
    except LeadNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post("/{public_id}/activities", response_model=LeadActivityCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_lead_activity_endpoint(
    public_id: UUID,
    payload: LeadActivityCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(LEAD_ACTIVITY_CREATE)),
) -> LeadActivityCreatedResponse:
    try:
        return create_lead_activity(
            db,
            public_id=public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except LeadNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except LeadValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.post("/{public_id}/qualification-decision", response_model=LeadQualificationDecisionResponse)
def decide_lead_qualification_endpoint(
    public_id: UUID,
    payload: LeadQualificationDecision,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(LEAD_QUALIFICATION_DECIDE)),
) -> LeadQualificationDecisionResponse:
    try:
        return decide_lead_qualification(
            db,
            public_id=public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except LeadNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except LeadValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.post("/{public_id}/convert", response_model=LeadConversionResponse, status_code=status.HTTP_201_CREATED)
def convert_lead_endpoint(
    public_id: UUID,
    payload: LeadConversionCreate | None = None,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(LEAD_CONVERT)),
) -> LeadConversionResponse:
    try:
        return convert_lead(
            db,
            public_id=public_id,
            payload=payload or LeadConversionCreate(),
            current_user_public_id=_user_public_id(current_user),
        )
    except LeadNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except LeadValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get("/{public_id}", response_model=LeadResponse)
def get_lead_endpoint(
    public_id: UUID,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(LEAD_READ_PERMISSION)),
) -> LeadResponse:
    try:
        return get_lead(db, public_id)
    except LeadNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.put("/{public_id}", response_model=LeadUpdatedResponse)
def update_lead_endpoint(
    public_id: UUID,
    payload: LeadUpdate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(LEAD_UPDATE_PERMISSION)),
) -> LeadUpdatedResponse:
    try:
        return update_lead(
            db,
            public_id=public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except LeadNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except LeadValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
