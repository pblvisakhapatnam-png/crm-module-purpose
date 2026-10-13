from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.authorization.contract import TC_CLAUSE_READ as TC_CLAUSE_READ_PERMISSION
from app.modules.authorization.dependencies import require_permission
from app.modules.identity.schemas import AuthUser
from app.modules.terms_and_conditions.schemas import TermsAndConditionsClauseResponse
from app.modules.terms_and_conditions.service import (
    TermsAndConditionsClauseNotFoundError,
    TermsAndConditionsClauseValidationError,
    get_terms_and_conditions_clause,
    list_terms_and_conditions_clauses,
)

router = APIRouter(prefix="/api/tc-clauses", tags=["terms-and-conditions"])


@router.get("", response_model=list[TermsAndConditionsClauseResponse])
def list_tc_clauses_endpoint(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
    business_line: str | None = Query(default=None, max_length=50),
    clause_category: str | None = Query(default=None, max_length=100),
    active: bool | None = Query(default=None),
    applies_to_header: bool | None = Query(default=None),
    applies_to_line: bool | None = Query(default=None),
    search: str | None = Query(default=None, max_length=200),
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(TC_CLAUSE_READ_PERMISSION)),
) -> list[TermsAndConditionsClauseResponse]:
    try:
        return list_terms_and_conditions_clauses(
            db,
            limit=limit,
            offset=offset,
            business_line=business_line,
            clause_category=clause_category,
            active=active,
            applies_to_header=applies_to_header,
            applies_to_line=applies_to_line,
            search=search,
        )
    except TermsAndConditionsClauseValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/{public_id}", response_model=TermsAndConditionsClauseResponse)
def get_tc_clause_endpoint(
    public_id: UUID,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(TC_CLAUSE_READ_PERMISSION)),
) -> TermsAndConditionsClauseResponse:
    try:
        return get_terms_and_conditions_clause(db, public_id)
    except TermsAndConditionsClauseNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

