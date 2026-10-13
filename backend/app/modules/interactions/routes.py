"""Interaction API routes (Slice 9D)."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.authorization.contract import (
    INTERACTION_CREATE,
    INTERACTION_DELETE,
    INTERACTION_READ,
    INTERACTION_UPDATE,
)
from app.modules.authorization.dependencies import require_permission
from app.modules.identity.schemas import AuthUser
from app.modules.interactions.contract import INTERACTION_CORRELATION_HEADER
from app.modules.interactions.schemas import (
    InteractionCreate,
    InteractionCreatedResponse,
    InteractionDeletedResponse,
    InteractionResponse,
    InteractionUpdate,
    InteractionUpdatedResponse,
)
from app.modules.interactions.service import (
    InteractionDuplicateError,
    InteractionNotFoundError,
    InteractionValidationError,
    create_interaction,
    delete_interaction,
    get_interaction,
    list_interactions_for_record,
    update_interaction,
)
from app.shared.zoned_datetime import ZonedDateTime

router = APIRouter(prefix="/api/interactions", tags=["interactions"])


def _correlation_id(supplied: str | None) -> str:
    """MCF-001 correlation: honour a caller-supplied chain, or start one.

    A correlation reference always exists on the resulting business event, so an action can be
    traced even when the caller did not think to supply one.
    """
    value = (supplied or "").strip()
    return value[:100] if value else str(uuid4())


def _user_public_id(user: AuthUser) -> str | None:
    value = getattr(user, "user_public_id", None) or getattr(user, "public_id", None)
    return str(value) if value else None


@router.post("", response_model=InteractionCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_interaction_endpoint(
    payload: InteractionCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(INTERACTION_CREATE)),
    x_correlation_id: str | None = Header(default=None, alias=INTERACTION_CORRELATION_HEADER),
) -> InteractionCreatedResponse:
    correlation_id = _correlation_id(x_correlation_id)
    try:
        response = create_interaction(
            db,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
            current_user=current_user,
            correlation_id=correlation_id,
        )
        response.correlation_id = correlation_id
        return response
    except InteractionValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except InteractionDuplicateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("", response_model=list[InteractionResponse])
def list_interactions_endpoint(
    linked_record_type: str = Query(...),
    linked_record_public_id: UUID = Query(...),
    include_inherited: bool = Query(default=False),
    channel_code: str | None = Query(default=None),
    direction_code: str | None = Query(default=None),
    occurred_from: ZonedDateTime | None = Query(default=None),
    occurred_to: ZonedDateTime | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(INTERACTION_READ)),
) -> list[InteractionResponse]:
    return list_interactions_for_record(
        db,
        linked_record_type=linked_record_type,
        linked_record_public_id=str(linked_record_public_id),
        include_inherited=include_inherited,
        channel_code=channel_code,
        direction_code=direction_code,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
        limit=limit,
        offset=offset,
        current_user=current_user,
    )


@router.get("/{public_id}", response_model=InteractionResponse)
def get_interaction_endpoint(
    public_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(INTERACTION_READ)),
) -> InteractionResponse:
    try:
        return get_interaction(db, public_id, current_user=current_user)
    except InteractionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.put("/{public_id}", response_model=InteractionUpdatedResponse)
def update_interaction_endpoint(
    public_id: UUID,
    payload: InteractionUpdate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(INTERACTION_UPDATE)),
    x_correlation_id: str | None = Header(default=None, alias=INTERACTION_CORRELATION_HEADER),
) -> InteractionUpdatedResponse:
    correlation_id = _correlation_id(x_correlation_id)
    try:
        response = update_interaction(
            db,
            public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
            current_user=current_user,
            correlation_id=correlation_id,
        )
        response.correlation_id = correlation_id
        return response
    except InteractionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/{public_id}", response_model=InteractionDeletedResponse)
def delete_interaction_endpoint(
    public_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(INTERACTION_DELETE)),
    x_correlation_id: str | None = Header(default=None, alias=INTERACTION_CORRELATION_HEADER),
) -> InteractionDeletedResponse:
    correlation_id = _correlation_id(x_correlation_id)
    try:
        response = delete_interaction(
            db,
            public_id,
            current_user_public_id=_user_public_id(current_user),
            correlation_id=correlation_id,
        )
        response.correlation_id = correlation_id
        return response
    except InteractionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
